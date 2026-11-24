# AI Prompt: Name in the university records (small change to Features 1 and 2)

- Date: 24 Nov 2026
- Tool: Claude Code
- Purpose: add the member's name to the IUB records
- CLAUDE.md version: commit 010297c

## Prompt

Read CLAUDE.md first and follow it strictly (architecture, coding standards,
tests, checks, working style, and the rule that you never run git commands).

# Task: add the member's name to the university records

Why: the SRS needs the name of the staff member or supervisor who rejects a
complaint (FR-16, FR-20) and already speaks of "the reporter's name". Today the
records hold only ID number, role, email and mobile. The team decided to add
the name to the IUB records. The user never types a name: registration still
asks only for the ID number and a password (FR-01 does not change).

Start with a PLAN only: list every file you will create or change and what each
change does. Wait for my approval. Then implement one stage at a time and STOP
after each stage with a short plain-language summary.

- Stage 1: `constants.py` (a constant for the "name" key), `records.py`
  (`UniversityMember` gets a required `name` field and `JsonRecordsClient`
  reads it), `data/iub_records.json` (a fake name for each of the 6 people),
  every `UniversityMember(...)` call in the tests (`tests/base.py`,
  `tests/test_records.py`), and new tests in `test_records.py`.
- Stage 2: `services.py`. Copy the name from the records into the user in
  the same places where `role` is copied from the records (`register_user`
  and `log_in_user`), so the name is refreshed at every login like the role.
  Store it in the existing `first_name` field (full name in `first_name`,
  `last_name` stays empty, so `User.get_full_name()` returns it). Do NOT add a
  model field or a migration. Add a short comment saying why. Tests: the name is
  stored at registration; a pending account that registers again keeps the
  correct name; login refreshes a name that changed in the records. In the plan
  say how you handle a name longer than the `first_name` limit.
- Stage 3 (ONLY if I ask): in `templates/campus/base.html` the navbar shows the
  full name and the role instead of the ID number and the role, with a view
  test.

## Rules

- Do not change the behaviour of anything else. All existing tests must keep
  passing, with only the constructor calls updated.
- Do not change any SRS message. The names in the JSON file are fake.
- Keep 100% statement and branch coverage. Every constant must be used.
- Run every check in CLAUDE.md plus coverage and report the results honestly.
- Do not touch `docs/` or `db.sqlite3`. Do not run git commands.
- List your assumptions at the end.