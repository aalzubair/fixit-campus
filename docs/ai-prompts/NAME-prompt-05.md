# AI Prompt: Review fixes for the name change (empty name, existing last name)

- Date: 25 Nov 2026
- Tool: Claude Code
- Purpose: fix two edge cases that a reviewer found in the name pull request: an empty name in the records, and an existing last name on an account
- CLAUDE.md version: commit 010297c

Read CLAUDE.md first and follow it.

Context: the CR-03 change (member name from the IUB records) is in review. The reviewer found two edge cases. Fix both on this branch (feature/F1-records-name).

1. An empty or whitespace-only name in the records is accepted. It must be rejected the same way as a missing "name" key: the records data is wrong, so fail loudly. Put the check in UniversityMember (__post_init__), so every RecordsClient is covered, not only the JSON one. Update the Raises section of the docstrings that are affected.

2. _copy_records_details sets first_name but never clears last_name. An existing account that has a last_name (for example created in the admin) would show "first last" in get_full_name(). Make the helper set last_name to an empty string, and strip the name before cutting it to MEMBER_NAME_MAX_LENGTH.

Rules for this task:
- Plan first. Show me the plan and WAIT for my approval. Do not write code before that.
- After approval, work in two stages and stop after each: Stage 1 = records.py (+ its tests), Stage 2 = services.py (+ its tests). Show a summary after each stage.
- No git commands. Do not change anything in docs/ or the database. Do not touch the SRS or SDS.
- If you add a constant (for the error message), it must be used. No unused constants.
- Keep PEP 257 docstrings and type hints on everything new.
- Tests: empty name, whitespace-only name, and a login test where the user already has a last_name (after login, get_full_name() equals the name from the records and last_name is empty). Keep coverage at 100%.
- At the end run: python manage.py test (from src/), the documented coverage command, flake8, black --check, pylint, interrogate. Report the real numbers.