Stage 1 is finished, but one test fails on purpose: `test_every_constant_is_used` reports 17 constants that no code uses yet. The other 91 tests pass, including every Feature 1 test. Black, flake8, pylint (10.00/10) and `manage.py check` are all clean, and `makemigrations --check` finds nothing missing.

## What changed

**`constants.py`**
- `ACCOUNT_LOCKED` is removed, with a comment explaining that "locked" now comes only from `locked_until`.
- **New rule numbers:** 5 wrong passwords, a 15-minute lock and a 15-minute idle timeout.
- **New session keys, URL names and template names** for login, logout, home, the reset pages and the 403 page.
- **New messages:** the six FR-02 to FR-04 messages, copied word for word from the SRS. `MSG_PASSWORD_CHANGED` is our own wording, shown on the login page after a reset, and the comment says so.
- **Home page text:** `HOME_PAGE_TEXT` holds a heading and one sentence for each of the five roles, as a tuple.
- I rewrote `MSG_ACCOUNT_NO_LONGER_ACTIVE` as one string so black accepts it. The text is the same.

**`models.py`**
- `User` gets `failed_login_attempts` (starts at 0) and `locked_until` (empty unless the account is locked).
- `is_locked(now)` says whether the lock time is still in the future.
- `clear_lock()` sets the count back to 0 and removes the lock, without saving.
- The rule "lock after the 5th wrong password" goes in `services.py` in Stage 2, not here.

**`migrations/0003_user_login_lock.py`** (new): adds the two fields and drops `locked` from the account status choices. The earlier migrations are untouched, and so is `db.sqlite3`.

**`settings.py`**: `LOGIN_URL` now uses `URL_NAME_LOGIN` from `constants.py`, so the name is written in one place.

**`CLAUDE.md`**: I added `middleware.py` to the layout and one row to the dependency table (may import `constants` only). No other line changed.

## Things to know
1. **Feature 1 test changed early.** `test_services_register.py` imported `ACCOUNT_LOCKED`, so removing it would have broken that whole file. I changed `test_locked_id_is_rejected_as_already_registered` now, not in Stage 4, so it locks the account with `locked_until` instead. It checks the same rule.
2. **The 17 failing subtests are expected.** Those constants get used in Stages 2 and 3, and the test should pass again by the end of Stage 3.
3. **The middleware line isn't in `settings.py` yet.** `middleware.py` doesn't exist until Stage 3, and listing it now would break every request.
4. **A gap in `test_every_constant_is_used`.** It also counts a name written in a docstring as a "use". The new `MSG_*` constants pass it only because the `constants.py` module docstring lists them, not because any code uses them yet. The Feature 1 messages pass the same way. Should I tighten the test in Stage 4 so it ignores docstrings?

Everything in your list of additions is recorded for later stages: `never_cache` on `role_required`, saving the lock outside any transaction plus its test, and no fake hash check or changes to the SRS messages.

I've stopped here. Shall I start Stage 2 (`services.py`)?