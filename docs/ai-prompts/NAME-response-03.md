Stage 2 is done and every check passes. The name from the records is now stored in the user at registration and refreshed at every login, the same way the role is. I'm stopping here, before Stage 3.

## What changed

- **`constants.py`**: added `MEMBER_NAME_MAX_LENGTH = 150`, with a comment that it matches the size of Django's `first_name` field.
- **`services.py`**: a new helper, `_copy_records_details(user, member)`, sets `first_name` and `role` from the records. Names longer than 150 characters are cut to 150.
  - `register_user` and `log_in_user` now call it where they used to copy only the role, so the copy logic lives in one place.
  - The helper's docstring explains why: the full name goes in `first_name` and `last_name` stays empty, so `get_full_name()` returns the name with no new field or migration. A long name is cut because it must not block registration or login.
  - The docstrings of `register_user` and `log_in_user` and the role comment now mention the name.
- **`tests/base.py`**: added `NEW_STUDENT_NAME`, next to `NEW_PASSWORD`, for the "name changed in the records" tests. The tests also use `STUDENT_NAME`, as you asked.
- **`tests/test_services_register.py`**: a new class, `RegisterNameTests`, with 4 tests:
  - the name is stored at registration, `last_name` stays empty and `get_full_name()` returns the name;
  - a pending account that registers again gets the new name;
  - boundary: a name of exactly 150 characters is stored whole;
  - boundary: a name of 151 characters is cut to 150, and registration still succeeds.
- **`tests/test_services_login.py`**: 2 tests. Login refreshes a name that changed in the records. A wrong password leaves the stored name unchanged.

No model field, migration, view, template or SRS message changed. I didn't touch `pyproject.toml`, `docs/` or `db.sqlite3`, and I didn't run any git commands.

## Check results (final run)

| Check                                | Result                                                                                                                                                                                                      |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `flake8 src`                         | Clean                                                                                                                                                                                                       |
| `black --check src`                  | Clean (31 files unchanged)                                                                                                                                                                                  |
| `pylint src/campus src/fixit_campus` | 10.00/10. The first run scored 9.99 because `RegisterUserTests` had 21 public methods and pylint allows 20. I didn't silence the warning; I moved the name tests into their own class, `RegisterNameTests`. |
| `python manage.py check`             | No issues                                                                                                                                                                                                   |
| `python manage.py test`              | 233 tests (6 new), all OK                                                                                                                                                                                   |
| Coverage, using your command         | **100%** of statements and branches (474 statements, 74 branches)                                                                                                                                           |

## Assumptions
1. Names are cut by character count, which is the same unit Django uses for `max_length`.
2. `request_new_registration_otp` still doesn't refresh the name, because it doesn't refresh the role either.
3. Users already saved in `db.sqlite3` keep an empty name until their next login.

Say if you want Stage 3, the navbar change.