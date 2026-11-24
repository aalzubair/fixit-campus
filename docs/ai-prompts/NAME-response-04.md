Stage 3 is done and every check passes. When a user is logged in, the navbar now shows their full name and role. An account saved before this change has no name yet, so it shows the ID number and role instead.

## What changed

- **`templates/campus/base.html`**: the navbar span uses `{{ user.get_full_name|default:user.username }} · {{ user.get_role_display }}`.
  - `get_full_name()` returns an empty string when there is no name, so `default` falls back to the ID number.
  - A one-line template comment explains why the fallback is there: older accounts have no name until their next login.
  - Nothing else in the template changed.
- **`tests/test_views_auth.py`** (`NavbarTests`):
  - **Fixed:** `test_logged_in_navbar_shows_id_role_and_log_out` expected the ID number in the navbar. It is now `test_logged_in_navbar_shows_name_role_and_log_out`. It checks the exact text `"Test Student · Student"` and that the ID number no longer appears on the page. The "Log out" checks stay as they were.
  - **New:** `test_navbar_shows_id_when_user_has_no_name` empties the stored name and logs in with `force_login`, which skips the login service so the name isn't refreshed. It checks for `"1000001 · Student"` and that the name does not appear.
  - Added a small test constant, `STUDENT_ROLE_LABEL`, taken from `ROLE_CHOICES`, so the role label isn't a hard-coded string.

No other test needed changing. I didn't touch `docs/`, `pyproject.toml` or `db.sqlite3`, and I didn't run any git commands.

## Check results

| Check                                | Result                                                            |
| ------------------------------------ | ----------------------------------------------------------------- |
| `flake8 src`                         | Clean                                                             |
| `black --check src`                  | Clean (31 files unchanged)                                        |
| `pylint src/campus src/fixit_campus` | 10.00/10                                                          |
| `python manage.py check`             | No issues                                                         |
| `python manage.py test`              | 234 tests (1 new), all OK                                         |
| Coverage, using your command         | **100%** of statements and branches (474 statements, 74 branches) |

## Assumptions
1. "No name" means an empty `first_name`, which is what accounts saved before Stage 2 have.
2. The navbar keeps the same layout and styling. Only the text before the "·" changed.
3. On the home page, the ID number now appears nowhere. The role label still appears twice, once in the navbar and once above the heading, as before.