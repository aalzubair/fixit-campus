# FixIt Campus: rules for AI coding assistants

These rules apply to every coding session in this repository.

## Project

FixIt Campus is a campus complaint and maintenance system for a university.
Stack: Python 3.14, Django 6.0, SQLite, Django templates with Bootstrap 5.
The team has four students who are new to Django. Keep code simple and easy
to explain in a viva. Prefer clear code over clever code.

## Repository layout

```
README.md, requirements.txt, .flake8, pyproject.toml   repository root
docs/                      documentation (do not edit unless asked)
tests/                     reserved (kept from the course template)
src/
  manage.py
  fixit_campus/            Django project: settings and root urls only
  campus/                  the ONE Django app: all feature code
    constants.py  urls.py  views.py  forms.py  services.py
    models.py  records.py  delivery.py
    templates/campus/  tests/
```

Run all Django commands from `src/`, for example `cd src && python manage.py test`.
Tests live in the package `src/campus/tests/` (not a single `tests.py`).

## Architecture (mandatory)

Layered Architecture (Presentation, Application, Storage) with MVC inside the
Presentation layer. Imports go DOWNWARDS ONLY. Never upwards, never skip a layer.

| File | May import | Must NOT import |
|---|---|---|
| views.py, urls.py | forms, services, constants | models, delivery, records |
| forms.py | constants | models, delivery, records, services, views |
| services.py | models, delivery, records, constants | views, forms |
| models.py | constants | services, views, forms, delivery, records |
| delivery.py, records.py | constants | every other project module, and each other |
| constants.py | nothing from the project | every other project module |

Responsibilities:
- templates: display only, no business rules.
- views.py: read the request, check login and role, validate with a form,
  call ONE service function, choose the template or redirect. No `.objects`,
  no `.save()`, no business rules.
- forms.py: check the SHAPE of input only (required, length, pattern).
- services.py: ALL business rules. No request, session or HTML.
  Outside systems are used only through `delivery.py` and `records.py`.
- models.py: tables and small one-row helpers only.
- delivery.py: `OtpSender` interface, `ConsoleOtpSender` (development only),
  `get_otp_sender()` reading `settings.FIXIT_OTP_SENDER`.
- records.py: `RecordsClient` interface, a JSON-file implementation (must not
  import models), `get_records_client()` reading `settings.FIXIT_RECORDS_CLIENT`.
- constants.py: all numbers, messages, roles and statuses. Immutable values
  only (use tuples or frozensets, never lists or dicts that code modifies).
  No module may reassign a constant. Every constant must be used.
- `tests/test_architecture.py` checks the dependency table automatically.
- Do not use Django shortcuts that skip the Application layer for business
  actions (no ModelForm saving, no generic edit views, no admin for roles).

## Coding standards (mandatory)

- PEP 8, line length 88, formatted with `black`.
- PEP 257 docstring on EVERY module, class, method and function
  (summary line, Args, Returns, Raises where relevant).
- snake_case for functions and variables, PascalCase for classes,
  UPPER_CASE for constants. Meaningful names (no x, tmp, data1).
- No magic numbers or magic strings: use named constants from constants.py.
- No unused imports, variables or function parameters.
- DRY: no duplicated logic. Short functions with one job.
- Type hints on all functions.
- Comments explain WHY, not WHAT.
- Never print or log passwords or plain OTPs (except the development-only
  console sender).
- User-facing messages must match the SRS exactly (Wiki "SRS Functional
  Requirements").

## Tests

- Use `django.test.TestCase` (`SimpleTestCase` when no database is needed).
- Cover normal, boundary, invalid and exception cases for every rule.
- Control time with `unittest.mock.patch` on `django.utils.timezone.now`.
  Never sleep.
- Test services with fakes (`tests/fakes.py`: `FakeOtpSender`,
  `FakeRecordsClient`), not with the console sender or real files.
- Test names describe behaviour, for example
  `test_third_wrong_otp_invalidates_otp`.

## Checks to run before finishing a task

From the repository root:
```
flake8 src
black --check src
pylint src/campus src/fixit_campus
```
From `src/`:
```
python manage.py check
python manage.py test
```
Report every failure honestly. Do not silence a warning without telling the
developer.

## Working style

- Ask for a plan first: list the files you will create or change and why.
  Wait for approval before writing code.
- Explain each file in simple words after writing it.
- List your assumptions at the end.
- Do not add dependencies without asking.
- Do NOT run git commit, git push, git checkout or create branches. The
  developer does all git work. Stay on the current branch.
- Do not edit anything under `docs/` unless asked.