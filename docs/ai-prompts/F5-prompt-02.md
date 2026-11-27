# F5 prompt 02: review fixes for PR #17

Tool: Claude (Anthropic), used by Puja Sur on 27 Nov 2026.

## Prompt (from Abdullah Al Zubair's review of PR #17)

In FixIt Campus (branch of PR #17), make these small changes following
`CLAUDE.md`:

1. In `services.py`, add a role check to `accept_complaint` (only
   `ROLE_MAINTENANCE_STAFF`) and `resolve_complaint` (only `STAFF_ROLES`),
   raising `ServiceError` with `MSG_NOT_AUTHORIZED`, like `reject_complaint`
   does.
2. Add view tests: a student, a faculty member and an administrator posting
   to accept and resolve get 403; an anonymous user goes to login.
3. In `staff_complaints.html` and `staff_complaint_detail.html`, show
   `assigned_to` and `rejected_by` with `get_full_name|default:username`
   instead of `username`.
4. Reword the `accept_complaint` docstring: `select_for_update` locks rows
   only on databases that support it; SQLite serialises writes instead.

Keep 100% coverage, run flake8, black, pylint, and add an AI prompt file in
`docs/ai-prompts`.
