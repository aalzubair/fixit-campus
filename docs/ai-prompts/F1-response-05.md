- Date: 20 Nov 2026
- Tool: Claude Code
- Purpose: Stage 4 summary

Stage 4 is done: all 92 tests pass and every CLAUDE.md check is clean, apart from one long line in `settings.py`. This stage added only the new folder `src/campus/tests/`; I didn't change any app code or commit anything.

## Check results

| Check                                | Result                                                         |
| ------------------------------------ | -------------------------------------------------------------- |
| `flake8 src`                         | Clean                                                          |
| `black --check src`                  | Clean (26 files)                                               |
| `pylint src/campus src/fixit_campus` | 9.99/10, one finding: `settings.py:89` "Line too long (91/88)" |
| `python manage.py check`             | No issues                                                      |
| `python manage.py test`              | 92 tests, all pass, about 0.2 s                                |
| `coverage`                           | 99% overall, 100% for every file in `campus/`                  |

- **pylint:** the long line is in the password-validator list Django generated in Stage 1. I haven't changed it or silenced it.
- **Coverage:** the only uncovered files are Django's generated `asgi.py` and `wsgi.py`, which tests never load.

While writing the tests, three tool complaints came up and I fixed them rather than hiding them:
- black reformatted two of my new test files.
- pylint flagged how a temporary folder was opened; I switched to `mkdtemp` plus a cleanup.
- One coverage gap remained, so I added a test that gives the architecture check a file full of forbidden imports. This proves the check fails when it should.

## What the tests cover
- **Every acceptance criterion, 1 to 12:** tested in the service tests. The page tests also check that each SRS message appears on screen.
- **Boundaries:**
  - password of 7 and 8 characters;
  - OTP at 4:59 and 5:01;
  - 2nd and 3rd wrong attempt;
  - 5th and 6th OTP request, and requests older than 15 minutes no longer counting.
- **The test you asked for:** `test_wrong_attempt_is_still_counted_after_error` checks that `wrong_attempts` is 1 in the database after the error is raised.
- **Invalid input:** empty ID, empty password, an ID that is too long, a non-digit OTP, an OTP one digit too short or too long, an empty OTP.
- **Exceptions:**
  - when the OTP cannot be sent, nothing is saved;
  - a missing or broken records file;
  - a wrong class name in settings;
  - verifying, or asking for an OTP, without registering first.
- **Security:** only hashes are stored, and a pending account is refused by Django's own login check.
- **Architecture:** each module imports only what CLAUDE.md allows, every module has a rule, every constant is immutable, and every constant is used.
- **Test setup:** services use `FakeOtpSender` and `FakeRecordsClient`, the clock is fixed by patching `django.utils.timezone.now`, and the fast MD5 hasher is set through `override_settings`. Nothing sleeps.

## (1) Files created or changed for the whole feature
- **Stage 1:**
  - deleted `campus/admin.py` and `campus/tests.py`;
  - changed `settings.py` (12 lines added);
  - created `constants.py`, `models.py`, `records.py`, `delivery.py`, `migrations/0001_initial.py` and `data/iub_records.json`;
  - added docstrings to `apps.py`, `__init__.py` and `migrations/__init__.py`.
- **Stage 2:** `services.py`.
- **Stage 3:** `forms.py`, `views.py`, `urls.py`, `fixit_campus/urls.py`, the 5 templates, and new constants.
- **Stage 4:** `campus/tests/`, containing `__init__.py`, `fakes.py`, `base.py`, `test_services_register.py`, `test_views_register.py`, `test_forms.py`, `test_models.py`, `test_records.py`, `test_delivery.py` and `test_architecture.py`.

## (2) Assumptions
1. Every OTP sent counts toward the limit of 5 in 15 minutes, including the first one at registration and any sent by registering again.
2. A request made exactly 15 minutes ago no longer counts, and an OTP at exactly 5:00 is still accepted.
3. Typing an old, cancelled OTP counts as a wrong attempt on the current OTP.
4. A locked account counts as "already registered".
5. The role is copied from the records at registration; it isn't read again at verification.
6. Some messages are my own wording because the SRS doesn't give them:
   - "This OTP has expired. Please request a new OTP."
   - "Enter the 6-digit OTP."
   - "A new OTP has been sent. The earlier OTP no longer works."
   - The wrong-OTP and invalid-OTP messages come from the UI designs.
7. `urls.py` may import `views.py`, which the CLAUDE.md table doesn't list. Django needs it, and both files are in the same layer. There's a comment about this in `test_architecture.py`.

## (3) Things I was unsure about
- **The `settings.py:89` long line.** Either add `# pylint: disable=line-too-long` on that line, or set a matching rule in `pyproject.toml`. Which do you prefer?
- **New modules must be listed in the architecture test.** Any new module added later, for example in FR-02, has to go into `ALLOWED_IMPORTS` in `test_architecture.py`, or `test_every_module_has_a_rule` fails. That's on purpose, but the team should know.
- **Two users verifying at the same moment** aren't protected by database row locks. That's acceptable for SQLite and this project, but not for a real deployment.
- **Two UI-design items aren't built yet:** the "Verify" button isn't greyed out after the OTP becomes invalid, and there's no "Log in" link until FR-02 exists.

`docs/ai-prompts/F1-prompt-05.md` is your own new file; I didn't touch it.