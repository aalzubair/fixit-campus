Stage 1 is done and every check passes. I'm stopping here as you asked, before Stage 2.

## What changed

- **`constants.py`**: added `RECORD_KEY_NAME = "name"`, the JSON key for the name. `records.py` and the tests use it.
- **`records.py`**: `UniversityMember` now has a required `name` field, right after `id_number`. `JsonRecordsClient` reads it with `person[RECORD_KEY_NAME]`, the same way it reads `role`. A record with no name raises a `KeyError`; the docstring says so.
- **`data/iub_records.json`**: each of the 6 people has a fake name: Ayesha Rahman, Farhan Hossain, **Rahim Uddin** (maintenance staff, as you asked), Nusrat Jahan, Tanvir Ahmed and Sadia Islam.
- **`tests/base.py`**: the 6 `TEST_MEMBERS` now include a name. There is a new `STUDENT_NAME` constant for Stage 2 to use. Nothing else changed.
- **`tests/fakes.py`**: only the `change_member` docstring changed; it now lists `name`.
- **`tests/test_records.py`**: the expected member includes the name. The temporary file has a third person with no name, for the error test. Three new tests:
  - `test_finds_member_name` (normal case)
  - `test_record_without_name_raises_key_error` (exception case)
  - `test_every_person_has_a_name` (checks the demo file)

No SRS message changed, and I didn't touch `services.py`, `docs/`, `db.sqlite3` or git.

## Check results (final run)

| Check                                | Result                                                                                        |
| ------------------------------------ | --------------------------------------------------------------------------------------------- |
| `flake8 src`                         | Clean. The first run found one line 2 characters too long in `test_records.py`; I wrapped it. |
| `black --check src`                  | Clean (31 files unchanged). It flagged that same line on the first run.                       |
| `pylint src/campus src/fixit_campus` | 10.00/10                                                                                      |
| `python manage.py check`             | No issues                                                                                     |
| `python manage.py test`              | 227 tests, all OK                                                                             |
| Coverage, statements and branches    | **100%** (1843 statements, 164 branches)                                                      |

**About the coverage command:** a plain `coverage run manage.py test` from `src/` reports 99%. The only missing lines are 13–14 in `manage.py`, which this change didn't touch.
- The coverage settings in `pyproject.toml` try to leave out `"src/manage.py"`, but that path only matches when coverage runs from the repository root.
- Running from the root doesn't fix it: it then counts `wsgi.py` and `asgi.py`, which the tests never load.
- The 100% figure comes from running in `src/` with `--branch --omit="*/migrations/*,manage.py"` added.

I didn't change the config. I can fix it if you want.

## Assumptions
1. The name sits right after `id_number` in `UniversityMember`, so all constructor calls pass it second.
2. The test names (for example "Test Student") are kept separate from the demo names, as the test emails are.

Say when you'd like me to start Stage 2.