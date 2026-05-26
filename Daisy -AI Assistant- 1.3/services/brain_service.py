"""
Brain Service - Action planner that converts transcripts to structured actions
Outputs validated JSON schemas (AssistantIntent with AssistantActions)
"""
import json
import re
from typing import List, Optional
import requests

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

from schemas import TranscriptionResult, AssistantIntent, AssistantAction
from config import Config
from utils import get_logger

logger = get_logger("brain_service")


# JSON schema for structured action output
ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "action_type": {"const": "create_note"},
                            "create_note": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content": {"type": "string"},
                                    "path": {"type": "string"},
                                    "tags": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["title", "content"],
                            },
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["action_type", "create_note"],
                    },
                    {
                        "type": "object",
                        "properties": {
                            "action_type": {"const": "create_task"},
                            "create_task": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                                    "due_date": {"type": "string"},
                                    "tags": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["title"],
                            },
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["action_type", "create_task"],
                    },
                    {
                        "type": "object",
                        "properties": {
                            "action_type": {"const": "create_reminder"},
                            "create_reminder": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string"},
                                    "reminder_time": {"type": "string"},
                                    "recurring": {"type": "boolean"},
                                },
                                "required": ["message"],
                            },
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["action_type", "create_reminder"],
                    },
                    {
                        "type": "object",
                        "properties": {
                            "action_type": {"const": "run_command"},
                            "run_command": {
                                "type": "object",
                                "properties": {
                                    "command": {"type": "string"},
                                    "working_directory": {"type": "string"},
                                    "timeout": {"type": "integer"},
                                    "confirmation_required": {"type": "boolean"},
                                },
                                "required": ["command"],
                            },
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["action_type", "run_command"],
                    },
                    {
                        "type": "object",
                        "properties": {
                            "action_type": {"const": "conversation"},
                            "conversation": {"type": "string"},
                        },
                        "required": ["action_type", "conversation"],
                    },
                ],
            },
        },
        "requires_confirmation": {"type": "boolean"},
    },
    "required": ["actions"],
}


SYSTEM_PROMPT_BASE = """You are Daisy, a personal AI assistant that helps users manage notes, tasks, reminders, run commands, and drive desktop applications via MCP tools.

Your job is to parse user requests and convert them into structured actions.

ACTION TYPES:
1. create_note - User wants to save information as a note/document
   - Extract: title, content, optional path, optional tags

2. create_task - User wants to create a todo/task
   - Extract: title, description, priority (low/medium/high), optional due_date, optional tags

3. create_reminder - User wants to be reminded of something
   - Extract: message, reminder_time (ISO datetime; resolve relative times against the CURRENT_DATE the system gives you), optional recurring flag

4. run_command - User wants to execute a terminal/system command
   - Extract: command string, optional working_directory, optional timeout
   - Set confirmation_required=true for dangerous commands (delete, move, system changes)

5. mcp_tool_call - User wants to drive a desktop application (Xcode, Android Studio, browser, etc.)
   - Extract: server ("desktop_automation" for the native MCP tools, or "computer_use" as a last-resort GUI driver),
              tool (e.g. "take_screenshot", "click_mouse", "type_text", "key_press", "open_application",
                    "run_terminal_command", "build_with_retry"),
              args (object matching the tool's input schema).
   - PREFER specific desktop_automation tools over the generic computer_use fallback.
   - The computer_use tool always requires confirmation.

6. conversation - General conversation, question answering, or no specific action needed
   - Provide a helpful response as a string.

IMPORTANT RULES:
- Always output valid JSON matching the schema.
- For commands, set confirmation_required=true if they modify files, delete data, or change system state.
- Be conservative — if unsure, use conversation type with a clarifying response.
- Extract structured data when clear, but don't force actions if the user is just chatting.
- Keep conversation responses concise (2-3 sentences for voice).
- When the user says "tomorrow", "in N minutes", "at 3pm", resolve to absolute ISO datetimes using the CURRENT_DATE provided.

Output format (JSON):
{
  "actions": [
    {
      "action_type": "create_note|create_task|create_reminder|run_command|mcp_tool_call|conversation",
      ... (action-specific fields)
      "confidence": 0.0-1.0,
      "reasoning": "brief explanation"
    }
  ],
  "requires_confirmation": true/false
}"""


def _current_system_prompt() -> str:
    """0.8 fix: inject CURRENT_DATE so 'tomorrow' / 'in N minutes' resolve."""
    from datetime import datetime
    now = datetime.now()
    return (
        SYSTEM_PROMPT_BASE
        + f"\n\nCURRENT_DATE: {now.isoformat()} (local time)."
        + f"\nDay of week: {now.strftime('%A')}."
    )


# Back-compat alias used elsewhere in this file
SYSTEM_PROMPT = SYSTEM_PROMPT_BASE


class BrainService:
    """Service that converts transcripts to structured actions"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize LLM clients
        self.openai_client = None
        self.groq_client = None
        
        if OPENAI_AVAILABLE and config.llm.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=config.llm.openai_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")

        # 0.8: Anthropic Claude client (optional)
        self.anthropic_client = None
        if ANTHROPIC_AVAILABLE and getattr(config.llm, "anthropic_api_key", None):
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=config.llm.anthropic_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")

        # Fix #11: per-model cache of "JSON mode not supported" so we don't retry every call.
        self._openai_json_mode_unsupported: set[str] = set()
        
        if GROQ_AVAILABLE and config.llm.groq_api_key:
            try:
                self.groq_client = Groq(api_key=config.llm.groq_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")
    
    def plan_actions(self, transcript: TranscriptionResult, conversation_history: Optional[List] = None) -> AssistantIntent:
        """
        Convert transcript to structured intent with actions
        """
        conversation_context = ""
        if conversation_history:
            # Include last few messages for context
            recent = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
            conversation_context = "\n".join([f"{msg.role}: {msg.content}" for msg in recent])
        
        user_prompt = f"""User said: "{transcript.text}"

{conversation_context}

Analyze this request and determine what action(s) to take. Output valid JSON only."""

        # Call LLM with structured output (0.8: configurable fallback chain).
        provider_chain = self._build_provider_chain()
        response_text = None
        last_err: Optional[Exception] = None
        for provider in provider_chain:
            try:
                response_text = self._call_provider(provider, user_prompt)
                break
            except Exception as e:
                logger.warning(f"LLM provider '{provider}' failed: {e}; trying next.")
                last_err = e
                continue

        if response_text is None:
            logger.error(f"All LLM providers failed: {last_err}")
            # Fallback to conversation action
            return AssistantIntent(
                transcript=transcript.text,
                actions=[
                    AssistantAction(
                        action_type="conversation",
                        conversation="I'm having trouble processing that right now. Could you rephrase?",
                    )
                ],
            )
        
        # Parse and validate JSON response
        try:
            response_json = self._extract_json(response_text)
            actions = self._parse_actions(response_json)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}, response: {response_text}")
            # Fallback
            return AssistantIntent(
                transcript=transcript.text,
                actions=[
                    AssistantAction(
                        action_type="conversation",
                        conversation="I understood that, but let me confirm what you'd like me to do.",
                    )
                ],
            )
        
        return AssistantIntent(
            transcript=transcript.text,
            actions=actions,
            requires_confirmation=response_json.get("requires_confirmation", False),
        )
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API (fix #11: typed-exception fallback + per-model cache)."""
        model = self.config.llm.model
        messages = [
            {"role": "system", "content": _current_system_prompt() + "\n\nIMPORTANT: You MUST respond with valid JSON only. Output format: {\"actions\": [...], \"requires_confirmation\": false}"},
            {"role": "user", "content": prompt},
        ]

        use_json_mode = model not in self._openai_json_mode_unsupported

        try:
            kwargs = dict(
                model=model,
                messages=messages,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
            )
            if use_json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = self.openai_client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            # Identify "response_format / json_object not supported" without
            # relying on substring matching the message body.
            is_bad_request = False
            try:
                from openai import BadRequestError  # noqa
                is_bad_request = isinstance(e, BadRequestError)
            except Exception:
                # SDK shape may vary; fall back to attribute sniffing
                is_bad_request = getattr(e, "status_code", None) == 400

            param = getattr(e, "param", None) or getattr(getattr(e, "response", None), "param", None)
            looks_like_json_mode_issue = (
                use_json_mode
                and is_bad_request
                and (param == "response_format" or "response_format" in str(e) or "json_object" in str(e))
            )

            if looks_like_json_mode_issue:
                logger.warning(
                    f"JSON mode not supported for {model}; caching and retrying without it."
                )
                self._openai_json_mode_unsupported.add(model)
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                )
                return response.choices[0].message.content
            raise

    # ----------------- 0.8: provider chain helpers -----------------

    _DEFAULT_PROVIDER_ORDER = ("openai", "anthropic", "groq", "local_http")

    def _build_provider_chain(self) -> List[str]:
        """
        Returns the ordered list of provider names to try. Starts with the
        configured `llm.provider`, then walks `_DEFAULT_PROVIDER_ORDER`
        skipping providers without a client. fallback_enabled=False stops
        after the primary.
        """
        primary = (self.config.llm.provider or "openai").lower()
        chain = [primary]
        if getattr(self.config.llm, "fallback_enabled", True):
            for p in self._DEFAULT_PROVIDER_ORDER:
                if p != primary and self._provider_available(p):
                    chain.append(p)
        return chain

    def _provider_available(self, provider: str) -> bool:
        if provider == "openai":
            return self.openai_client is not None
        if provider == "groq":
            return self.groq_client is not None
        if provider == "anthropic":
            return self.anthropic_client is not None
        if provider == "local_http":
            return bool(getattr(self.config.llm, "local_http_url", None))
        return False

    def _call_provider(self, provider: str, prompt: str) -> str:
        if provider == "openai" and self.openai_client:
            return self._call_openai(prompt)
        if provider == "anthropic" and self.anthropic_client:
            return self._call_anthropic(prompt)
        if provider == "groq" and self.groq_client:
            return self._call_groq(prompt)
        if provider == "local_http" and self.config.llm.local_http_url:
            return self._call_local_http(prompt)
        raise RuntimeError(f"Provider '{provider}' unavailable")

    # ----------------- Anthropic -----------------

    _ANTHROPIC_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def _call_anthropic(self, prompt: str) -> str:
        """
        Call Anthropic Claude. Uses prompt caching on the system prompt so
        repeated turns within 5 minutes cost ~10% of the cached portion.
        """
        if not self.anthropic_client:
            raise RuntimeError("Anthropic client not initialized")

        model = self.config.llm.model
        if "claude" not in (model or ""):
            # User likely picked an OpenAI / Groq model name; substitute a Claude one.
            model = self._ANTHROPIC_DEFAULT_MODEL

        system_blocks = [
            {
                "type": "text",
                "text": _current_system_prompt(),
                "cache_control": {"type": "ephemeral"},
            }
        ]
        message = self.anthropic_client.messages.create(
            model=model,
            max_tokens=self.config.llm.max_tokens,
            temperature=self.config.llm.temperature,
            system=system_blocks,
            messages=[{"role": "user", "content": prompt + "\n\nRespond with valid JSON only."}],
        )

        # Concatenate text content blocks.
        out_parts = []
        for block in message.content:
            text = getattr(block, "text", None)
            if text:
                out_parts.append(text)
        return "".join(out_parts)

    # Models known to be served by Groq. If the user picked something else
    # (e.g. an OpenAI model name), we substitute a sensible Groq default.
    _GROQ_KNOWN_MODELS = {
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    }
    _GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def _call_groq(self, prompt: str) -> str:
        """Call Groq API (fix #9: model now comes from config, with fallback)."""
        configured = self.config.llm.model
        model = configured if configured in self._GROQ_KNOWN_MODELS else self._GROQ_DEFAULT_MODEL
        if model != configured:
            logger.info(
                f"Groq doesn't serve '{configured}'; falling back to '{model}'."
            )
        response = self.groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _current_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    
    def _call_local_http(self, prompt: str) -> str:
        """Call local HTTP LLM endpoint (e.g., Ollama)"""
        url = self.config.llm.local_http_url
        response = requests.post(
            url,
            json={
                "model": self.config.llm.model,
                "prompt": prompt,
                "system": _current_system_prompt(),
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    
    @staticmethod
    def _find_balanced_json(text: str) -> Optional[str]:
        """
        Fix #10: brace-counting scan that survives nested objects and arrays.
        Returns the first top-level JSON object found, or None.
        Ignores braces inside string literals.
        """
        depth = 0
        start = -1
        in_string = False
        escape = False
        for i, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start >= 0:
                        return text[start:i + 1]
        return None

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from text (may have markdown code blocks)."""
        # 1. Try fenced ```json blocks first (greedy enough now)
        fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if fence_match:
            candidate = fence_match.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                # Maybe the fenced block has trailing prose; try brace-balanced inside
                balanced = self._find_balanced_json(candidate)
                if balanced:
                    try:
                        return json.loads(balanced)
                    except Exception:
                        pass

        # 2. Brace-balanced scan over the whole text (handles nested objects/arrays)
        balanced = self._find_balanced_json(text)
        if balanced:
            try:
                return json.loads(balanced)
            except Exception:
                pass

        # 3. Try whole text
        try:
            return json.loads(text)
        except Exception:
            logger.warning(f"Could not extract JSON from: {text[:100]}...")
            return {
                "actions": [{
                    "action_type": "conversation",
                    "conversation": text.strip(),
                }]
            }
    
    def _parse_actions(self, response_json: dict) -> List[AssistantAction]:
        """Parse actions from JSON response"""
        from schemas import CreateNoteAction, CreateTaskAction, CreateReminderAction, RunCommandAction
        
        actions = []
        for action_data in response_json.get("actions", []):
            action_type = action_data.get("action_type")
            
            try:
                if action_type == "create_note":
                    note_data = action_data.get("create_note", {})
                    note_action = CreateNoteAction(**note_data)
                    actions.append(AssistantAction(
                        action_type="create_note",
                        create_note=note_action,
                        confidence=action_data.get("confidence"),
                        reasoning=action_data.get("reasoning"),
                    ))
                elif action_type == "create_task":
                    task_data = action_data.get("create_task", {})
                    task_action = CreateTaskAction(**task_data)
                    actions.append(AssistantAction(
                        action_type="create_task",
                        create_task=task_action,
                        confidence=action_data.get("confidence"),
                        reasoning=action_data.get("reasoning"),
                    ))
                elif action_type == "create_reminder":
                    reminder_data = action_data.get("create_reminder", {})
                    reminder_action = CreateReminderAction(**reminder_data)
                    actions.append(AssistantAction(
                        action_type="create_reminder",
                        create_reminder=reminder_action,
                        confidence=action_data.get("confidence"),
                        reasoning=action_data.get("reasoning"),
                    ))
                elif action_type == "run_command":
                    cmd_data = action_data.get("run_command", {})
                    cmd_action = RunCommandAction(**cmd_data)
                    actions.append(AssistantAction(
                        action_type="run_command",
                        run_command=cmd_action,
                        confidence=action_data.get("confidence"),
                        reasoning=action_data.get("reasoning"),
                    ))
                elif action_type == "conversation":
                    actions.append(AssistantAction(
                        action_type="conversation",
                        conversation=action_data.get("conversation", ""),
                        confidence=action_data.get("confidence"),
                        reasoning=action_data.get("reasoning"),
                    ))
            except Exception as e:
                logger.warning(f"Failed to parse action {action_type}: {e}")
                # Skip invalid actions
                continue
        
        return actions

