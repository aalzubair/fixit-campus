Stage 3 is done, and all 97 Feature 1 tests pass again. `test_every_constant_is_used` is green now that every new constant is used. Black, flake8, pylint (10.00/10), `manage.py check` and `makemigrations --check` are all clean.

I also ran a throwaway end-to-end check through the real pages, using the test client against a test database. The script is only in the scratchpad, not the repo. Every step behaved as specified:
- **Login:** wrong password, then correct login going to the student home page.
- **Idle timeout:** a request at 14:59 still works; at 30:00 you're sent to login with the expired message.
- **Logout:** GET gives 405; POST logs you out, and `/home/` then sends you to login.
- **Reset:** an unknown ID gets the general message and nothing is sent. Then a short password, a new OTP, a successful change, and the old password rejected.
- **Wrong role:** 403 with the right text and no-cache headers.

## Files and what they do

- **`forms.py`**
  - `LoginForm` reuses `RegisterForm`, so the fields aren't copied.
  - `PasswordResetRequestForm` has only the ID.
  - `PasswordResetVerifyForm` is the OTP form plus `new_password`.
  - To avoid repeating code, I gave `RegisterForm` a small parent `IdNumberForm` and a `_password_field()` helper. Its fields and behaviour are unchanged.
- **`middleware.py`** (new, imports only `constants`): `IdleTimeoutMiddleware` saves the time of each request by a logged-in user in the session, after the view runs. If the gap reaches 15 minutes, it logs the user out, adds "Your session has expired. Please log in again." and redirects to `/login/`.
- **`views.py`**
  - **`role_required(*roles)`:** applies `never_cache` and `login_required`, and gives a 403 page for a wrong role.
  - **`login_view`:** calls `log_in_user`, then Django's `login()`, then goes to `/home/`.
  - **`logout_view`:** POST only.
  - **`home_view`:** uses `login_required` and `never_cache`, and picks the role's text from `HOME_PAGE_TEXT`.
  - **Three reset views:** the ID between the two steps is kept in the session, in the views only.
- **`urls.py`**: six new routes. No routes were added just for tests.
- **`settings.py`**: the middleware is placed after Session, Authentication and Messages, because it uses all three.
- **Templates**
  - New: `login.html`, `home.html`, `password_reset.html`, `password_reset_verify.html` and `403.html`.
  - `_messages.html` is a shared message box: red for errors, green for success, blue for information, as in the design.
  - `base.html` now has a navbar: "Log in" and "Register" when logged out; ID, role and a "Log out" button when logged in.
  - `register_done.html` gets a "Log in" button, and `register_verify.html` now uses `_messages.html`.
- **`tests/test_architecture.py`**: I added the `middleware` rule now rather than in Stage 4. Without it, `test_every_module_has_a_rule` would fail as soon as `middleware.py` exists.

## Things to know
1. **Feature 1 pages look slightly different.** The "FixIt Campus" title moved from above the card into the navbar on every page.
2. **The login page link says "Register"**, as your spec asked. The design says "Create an account".
3. **Two parts of the design are missing.** I left out the "Show" password button and the OTP countdown timer, because both need JavaScript.
4. **Two "request new OTP" views look alike.** `register_new_otp_view` and `password_reset_new_otp_view` have the same shape. I kept them separate because a shared helper would need 5 parameters and be harder to explain in the viva. Tell me if you'd rather merge them.
5. **A reset with an unknown ID still goes to the OTP page.** It shows the general message there, so the page behaves the same whether or not the ID exists.
6. **The reset-request message is blue.** "If this ID is registered…" is shown as information on the OTP page.

All of your Stage 4 test requests are noted:
- An old session stops working after a password reset.
- A 7-character password with a correct OTP leaves that OTP valid.
- OTP requests are counted per purpose, both ways.
- `locked_until` is still saved after the 5th wrong password raises its error.
- `test_every_constant_is_used` ignores names in docstrings and comments.

I haven't committed anything or touched `db.sqlite3` or `docs/`. Shall I start Stage 4 (tests and all checks)?