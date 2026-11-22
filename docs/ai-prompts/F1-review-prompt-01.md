Read CLAUDE.md first. You are a code REVIEWER, not the author. Do NOT edit, create or delete any file, and run only read-only git commands (git diff, git log, git show).

Review everything on branch feature/F1-register compared with main (use: git diff main...HEAD). Judge it against the CLAUDE.md rules (architecture dependency table, coding standards, tests) and the Feature 1 acceptance criteria below.

Use this checklist and give a short verdict for each point:
1. Design (dependency rule, responsibilities of each layer)
2. Functionality (does the code do what each acceptance criterion says?)
3. Complexity (anything too complicated for beginners to explain?)
4. Tests (missing cases, tests that only mirror the code)
5. Naming
6. Comments (explain WHY, not WHAT)
7. Documentation (docstrings, message text, SRS match)

Then list findings, most important first. For each finding give: file and line, severity (high / medium / low), and a QUESTION-style comment a teammate could post on a pull request (for example: "What happens if ...?"), plus a suggested fix. Do not repeat what the tools already check (flake8, black, pylint). Also say honestly what you could NOT verify.

Acceptance criteria summary: register with IUB ID and password; OTP of 6 digits valid 5 minutes, stored only as a hash; wrong OTP can be retried, the 3rd wrong attempt invalidates it; expired OTP rejected; a new OTP cancels the earlier one; at most 5 OTP requests per 15 minutes; password at least 8 characters; OTP goes to email, else mobile; exact SRS error messages; registering again while pending replaces the password and sends a new OTP.