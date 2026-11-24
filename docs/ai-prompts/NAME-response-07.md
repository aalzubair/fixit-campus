Both review edge cases are now fixed on `feature/F1-records-name`. All 243 tests pass, coverage is 100% and every check is clean.

## Stage 2 is done: services.py and its tests

**The method count first:** `RecordsCheckAtLoginTests` had 6 public methods. Adding 4 makes 10, well under the limit of 20, so the tests went into that class. Nothing was silenced.

**`services.py` (`_copy_records_details`)**
- It now does `user.first_name = member.name.strip()[:MEMBER_NAME_MAX_LENGTH].rstrip()`, as you specified.
- It now also sets `user.last_name = ""`.
- The docstring explains why: an account made in the admin may already have a `last_name`. Stripping before the cut means outer spaces don't use up the 150 characters. Stripping after the cut means a cut that ends on a space leaves no trailing space.
- Following your choice, `ValueError` is not added to the service docstrings.

**`tests/test_services_login.py`** has 4 new tests:
- `test_login_clears_existing_last_name`: the stored user is given `last_name = "Admin Surname"` before login. After login, `get_full_name()` equals the records name and `last_name == ""`, on both the returned user and the user read again from the database.
- `test_name_is_stripped_before_storing`: a records name of `"  Test Student Renamed  "` is stored without the spaces.
- `test_padded_full_length_name_is_stripped_then_cut`: 2 spaces followed by exactly 150 letters is stored with all 150 letters. Cutting before stripping would lose 2.
- `test_cut_ending_on_a_space_leaves_no_trailing_space`: 149 letters, then a space as the 150th character, then more text. The stored name is the 149 letters with no trailing space.

New test constants: `OLD_LAST_NAME`, `NAME_LETTER` and `CUT_OFF_PART`. I added them so there are no magic values in the tests.

## Check results (real output)

| Check                                                       | Result                                      |
| ----------------------------------------------------------- | ------------------------------------------- |
| `flake8 src`                                                | Clean (exit 0)                              |
| `black --check src`                                         | 31 files unchanged                          |
| `pylint src/campus src/fixit_campus`                        | 10.00/10                                    |
| `interrogate -v --exclude src/campus/migrations src/campus` | PASSED, 100.0% (432 of 432)                 |
| `python manage.py check`                                    | No issues                                   |
| `python manage.py test`                                     | 243 tests, OK                               |
| Coverage (your command, from `src/`)                        | 100%: 479 statements, 76 branches, 0 missed |

## Assumptions
1. Pylint's `too-many-public-methods` counts only the methods a class defines itself, not the many it inherits from `TestCase`.
2. I didn't add a separate registration test, because registration calls the same `_copy_records_details` helper.
3. Saving the user directly with `.save()` in the `last_name` test is fine: it stands in for an admin edit, and it's test code, not code in `views.py`.

Nothing was run with git, and nothing in `docs/` or the database was changed.