# Daisy 1.2 — Calendar, Reminders, Mail

Daisy can now read and write to your Mac's Calendar, Reminders, and Mail apps. Ask her what's on your schedule today, have her book a dentist appointment, list your to-dos, add new reminders, check recent emails, search your inbox, or draft/send an email — all by voice.

## New in 1.2

- **`services/mac_calendar.py`** — list/create Calendar events + Reminders via AppleScript (`osascript`)
- **`services/mac_mail.py`** — read/search/send/draft email via Mail.app
- **New action types**: `CreateCalendarEventAction`, `CreateMacReminderAction`, `SendEmailAction`
- **API endpoints**:
  - `GET /api/calendar/events` (today's events), `POST /api/calendar/events` (create)
  - `GET /api/calendar/calendars` (list calendar names)
  - `GET/POST /api/mac-reminders` (list/create)
  - `GET /api/mail/messages` (recent), `GET /api/mail/search?q=`, `POST /api/mail/send` (send or draft)
- AppleScript output parser hardened against trailing-separator artifacts
- 27 new tests

## Tests

152/152 passing.

## Example voice commands

- "What's on my calendar today?"
- "Schedule a dentist appointment Tuesday at 3 PM"
- "Remind me to buy milk tomorrow"
- "Email Alice that I'll be late"
- "Search my inbox for invoice"
