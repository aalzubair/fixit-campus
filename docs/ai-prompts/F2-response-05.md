Feature 2 is finished: all 219 tests pass (97 from Feature 1, 122 new), and every check in CLAUDE.md is clean. Nothing is committed, and I didn't touch `db.sqlite3` or `docs/`. The new `docs/ai-prompts/F2-*` files showing in git status are yours.

## Check results

| Check                                | Result                                                         |
| ------------------------------------ | -------------------------------------------------------------- |
| `flake8 src`                         | no issues                                                      |
| `black --check src`                  | 31 files unchanged                                             |
| `pylint src/campus src/fixit_campus` | 10.00/10                                                       |
| `python manage.py check`             | no issues (and `makemigrations --check` finds nothing missing) |
| `python manage.py test`              | 219 tests, OK                                                  |

Problems I hit along the way, and how I fixed them:
- **Long lines** in three new test files: black reformatted them.
- **Too many methods:** pylint flagged `LoginTests` with 26 test methods (limit 20). I split it into three classes by acceptance criterion: login, lock, and records check.
- **Module-level name:** pylint read the test view's wrapped name as a variable, so I switched to normal `@role_required` decorator syntax.
- **`response.url`:** I replaced it with the `Location` header, because pylint can't see `.url` on a plain `HttpResponse`.

Nothing is silenced with a disable comment. I actually removed one: `FakeRecordsClient` now has enough methods that it no longer needs its `too-few-public-methods` disable.

## Your Stage 4 questions
- **Does `LoginForm` block short passwords?** No. The 8-character rule lives in the service, not the form, so I didn't need to change anything. A wrong 3-character password is counted, and tests at the form, service and page level prove it.
- **CSRF tokens:** every POST form has `{% csrf_token %}`, including the navbar Log out form. The tests now prove it four ways:
  - with real CSRF checking on, a logout POST without a token is refused (403) and the user stays logged in;
  - the rendered navbar form contains the token;
  - a logout using that token works;
  - every `<form method="post">` in every template has a token.
- **An old session after a password reset** stops working without any extra code. Django ends it by itself, and a test confirms it.
- **The tighter `test_every_constant_is_used`** no longer counts names in docstrings or comments. It found no unused constants, including all of Feature 1's. A small extra test checks that the new check ignores docstrings and comments.
- **Idle timeout at exactly 15:00:** the user is logged out, because the rule is "idle time is 15 minutes or more". The idle test class docstring says so, and there's a separate test for 15:00 next to the 14:59 and 15:01 ones.

## (1) Files created or changed

**Created**
- `campus/middleware.py`
- `campus/migrations/0003_user_login_lock.py`
- Templates: `login.html`, `home.html`, `password_reset.html`, `password_reset_verify.html`, `403.html`, `_messages.html`
- Tests: `test_services_login.py`, `test_services_password_reset.py`, `test_views_auth.py`, `test_views_password_reset.py`

**Changed**
- `campus/constants.py`, `models.py`, `services.py`, `forms.py`, `views.py`, `urls.py`
- `fixit_campus/settings.py`
- Templates: `base.html`, `register_verify.html`, `register_done.html`
- Tests: `tests/base.py`, `fakes.py`, `test_architecture.py`, `test_forms.py`, `test_models.py`, `test_services_register.py`
- `CLAUDE.md`: only the `middleware.py` layout entry and its table row.

## (2) Assumptions
1. A password reset doesn't unlock the account or reset the wrong-password count.
2. The reset request checks in this order: registered and active, then in the records, then locked. So a locked member who has left the university gets the general message.
3. An active member whose records entry has no contact details gets the general message, and nothing is sent.
4. The verify step answers an unknown ID with "Incorrect OTP…", so it doesn't reveal whether the ID exists.
5. A short new password is checked before the OTP, so it doesn't use up an OTP attempt. A test confirms the OTP stays valid.
6. After login the user always goes to `/home/`, and `?next=` is ignored.
7. A logged-in user who opens `/login/` is sent to `/home/`.
8. The idle timer restarts on every request, and the timeout ends the session at exactly 15:00.
9. `MSG_PASSWORD_CHANGED`, shown on the login page after a reset, is our own wording and isn't in the SRS.

## (3) Unsure points
1. **Two "too many attempts" messages could be mixed up.** "Too many wrong attempts. This OTP is no longer valid…" is the Feature 1 OTP message, and "Too many requests…" is the request limit. They're worded differently, so this is only worth a quick look in the viva.
2. **The verify step can still hint that an ID exists.** For an unknown ID, the reset verify step always says "Incorrect OTP". A real user sees "no longer valid" after 3 wrong tries. So repeated guessing could tell a real ID from an unknown one. Together with the locked and too-many-requests messages, this belongs with your SDS limitations on revealing IDs.
3. **A failed login page and an unknown-ID page are identical.** A test checks this after removing the typed ID and the CSRF token. Any future difference, such as a "welcome back" hint, would make it fail, which is what we want.
4. **The known limitations you already have:**
   - parallel wrong passwords can get more than 5 guesses;
   - a known ID makes login slightly slower, because the password hash is checked;
   - the "Show" password button and the OTP countdown are missing.

## (4) Feature 1 code and tests I changed, and why
- **`test_services_register.py`:** `test_locked_id_is_rejected_as_already_registered` now locks the account with `locked_until`, because `ACCOUNT_LOCKED` was removed (D1). It checks the same rule.
- **`tests/base.py`**
  - The fake records are kept in `self.records`, so tests can remove a member or change a role.
  - New `WRONG_PASSWORD` value and `type_wrong_passwords()` helper.
  - The docstring now covers FR-01 to FR-04.
  - Feature 1 tests use this file unchanged.
- **`fakes.py`:** `FakeRecordsClient` gained `remove_member()` and `change_member()`.
- **`test_architecture.py`:** added the `middleware` rule and the tighter constant-usage check.
- **`test_forms.py`, `test_models.py`:** new tests were added, and the existing ones are unchanged.
- **Feature 1 code**
  - `_check_request_limit` now counts per purpose (D2).
  - `_raise_if_registered` has an updated docstring.
  - `RegisterForm` now gets its fields from `IdNumberForm` and `_password_field()`; the fields are the same.
  - `register_verify.html` uses the shared `_messages.html`.
  - `register_done.html` has a Log in button.
  - `base.html` has the navbar, so the "FixIt Campus" title moved there.

All 97 Feature 1 tests pass, with only the one test change listed above.