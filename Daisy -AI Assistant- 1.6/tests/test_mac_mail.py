"""Tests for mac_mail service (1.2) — mocked osascript."""
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import mac_mail


def _mock_run(returncode=0, stdout="", stderr=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_list_recent_messages_parses():
    chunk = "Meeting notes|boss@work.com|Mon May 26 2026|false||"
    with patch("services.mac_mail.subprocess.run",
               return_value=_mock_run(0, chunk)):
        msgs = mac_mail.list_recent_messages(count=1)
    assert len(msgs) == 1
    assert msgs[0]["subject"] == "Meeting notes"
    assert msgs[0]["from"] == "boss@work.com"


def test_list_recent_messages_empty_on_failure():
    with patch("services.mac_mail.subprocess.run",
               return_value=_mock_run(1)):
        assert mac_mail.list_recent_messages() == []


def test_search_messages_parses():
    chunk = "Invoice April|billing@co.com|Mon May 1 2026||"
    with patch("services.mac_mail.subprocess.run",
               return_value=_mock_run(0, chunk)):
        msgs = mac_mail.search_messages("Invoice")
    assert len(msgs) == 1
    assert msgs[0]["subject"] == "Invoice April"


def test_send_email_ok():
    with patch("services.mac_mail.subprocess.run",
               return_value=_mock_run(0)):
        res = mac_mail.send_email("a@b.com", "Hello", "Body text")
    assert res["ok"] is True
    assert res["error"] is None


def test_send_email_failure():
    with patch("services.mac_mail.subprocess.run",
               return_value=_mock_run(1, "", "Mail error")):
        res = mac_mail.send_email("a@b.com", "Hello", "Body text")
    assert res["ok"] is False
    assert res["error"] == "Mail error"


def test_create_draft_ok():
    with patch("services.mac_mail.subprocess.run",
               return_value=_mock_run(0)):
        res = mac_mail.create_draft("a@b.com", "Draft subject", "Draft body")
    assert res["ok"] is True


def test_create_draft_failure():
    with patch("services.mac_mail.subprocess.run",
               return_value=_mock_run(1, "", "Automation denied")):
        res = mac_mail.create_draft("a@b.com", "S", "B")
    assert res["ok"] is False
