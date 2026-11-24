## Stage 1 is done: records.py and its tests

**What changed**

- **`constants.py`**: added `RECORDS_ERROR_EMPTY_NAME = "University record {id_number} has an empty name."` It's used in `records.py` and in one test. The message names the ID, not the name.
- **`records.py`**:
  - `UniversityMember.__post_init__` raises `ValueError` when `name.strip()` is empty. Because the check lives in the dataclass, every `RecordsClient` is covered: the JSON one, the fake one, and a future real one.
  - It only checks the name and doesn't change it. A padded name like `"  Ali  "` stays as it is, and the services will strip it in Stage 2.
  - `Raises: ValueError` is now in the docstrings of the class, of `__post_init__`, of `RecordsClient.find_member` (the interface) and of `JsonRecordsClient.find_member`. `KeyError` for a missing key stays.
- **`tests/test_records.py`**:
  - A new `UniversityMemberTests` class checks four things:
    - an empty name raises `ValueError`
    - a name of only spaces, tabs and newlines raises `ValueError`
    - the error message is exact and shows the ID
    - a padded name is accepted unchanged (the boundary case)
  - `JsonRecordsClientTests` has a new test: a JSON record with `"name": ""` raises `ValueError`.
  - A small `make_student(name)` helper builds the test members. The existing `test_finds_member_by_id` uses it too, so the constructor call isn't repeated.

**Check results (real output)**

| Check                                | Result                                      |
| ------------------------------------ | ------------------------------------------- |
| `flake8 src`                         | Clean (exit 0)                              |
| `black --check src`                  | 31 files unchanged                          |
| `pylint src/campus src/fixit_campus` | 10.00/10                                    |
| `interrogate src`                    | PASSED, 98.4% (minimum 80%)                 |
| `python manage.py check`             | No issues                                   |
| `python manage.py test`              | 239 tests, OK                               |
| Coverage (your command, from `src/`) | 100%: 478 statements, 76 branches, 0 missed |

**About interrogate's 98.4%:** every item it reports as missing is in a file I didn't touch. They are the three generated migration files (the module and the `Migration` class in each) and `fixit_campus/__init__.py`. Everything in `campus/` that I wrote or changed has a docstring. I didn't change the interrogate config.

**Note for Stage 2:** I haven't counted the public methods in `RecordsCheckAtLoginTests` yet. I'll count them before adding the 4 login tests (the 3 planned plus your trailing-space test). If the class would go over 20, they'll go in a new class.

Say when to start Stage 2.