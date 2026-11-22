Read CLAUDE.md first and follow it strictly (architecture, coding standards,
tests, checks, working style, and the rule that you never run git commands).

# Task: Feature 2, Login, Logout and Reset password (FR-02, FR-03, FR-04)

Feature 1 (register with OTP) is finished and its 97 tests pass. Build Feature 2
on top of it and REUSE the existing code instead of copying it. Before you plan,
read these files completely: `constants.py`, `models.py`, `records.py`,
`delivery.py`, `services.py`, `forms.py`, `views.py`, `urls.py`, the templates
and `tests/` (especially `fakes.py`, `base.py` and `test_architecture.py`).
Do not change the behaviour of Feature 1. All existing tests must keep passing.
If a small change to Feature 1 code is needed (for example to share an OTP
helper with a new `purpose`), say so in the plan and keep it minimal.

Work in stages. Start with a PLAN only: list every file you will create, change
or delete, and what each one does. Wait for my approval. Then implement one
stage at a time and STOP after each stage with a short plain-language summary:

- Stage 1: constants.py, models.py (new fields + migration), settings
- Stage 2: services.py (login rules, lock, IUB records check, password reset)
- Stage 3: forms, views, role_required decorator, idle-timeout, urls, templates
- Stage 4: tests, then run all checks

## What the feature does

Registered members log in with their IUB ID number and password, see a home page
for their role, and log out. A member who forgot the password resets it with an
OTP sent to the registered email (or mobile number if there is no email). The
account locks after repeated wrong passwords. At every login the system checks
the IUB records again, so people who left the university lose access.

## Business rules (exact)

Login order of checks, in `services.py` (the service has no request, no session):
1. Find the user by ID. Not found: reject with "Invalid ID or password" and store
   nothing.
2. Account not activated (pending): reject with the same "Invalid ID or password".
3. Account locked (`locked_until` is later than now): reject with "Your account is
   locked. Please try again later." even if the password is correct. Do NOT count
   attempts while locked.
4. Lock already expired (`locked_until` is not later than now): treat the account
   as unlocked and start the wrong-password count again from 0.
5. Wrong password: add 1 to `failed_login_attempts`. On the 5th wrong password in
   a row set `locked_until = now + 15 minutes`. Reject with "Invalid ID or password"
   (never say which of the two is wrong).
6. Correct password: ask the IUB records for this ID. Not found: reject with "Your
   account is no longer active. Please contact the university administration."
7. If the role in the records differs from the stored role, update the stored role.
8. Set `failed_login_attempts = 0` and `locked_until = None`, return the user.

Lock state is DERIVED from `locked_until`. Do not keep a second stored "locked"
status that can get out of sync. If the existing account status value `locked` is
then unused, propose in the plan whether to remove it (with a migration) or keep
it, and why.

Log in and log out in the VIEW (the service never touches the session):
- Correct login: start the session and go to `/home/`.
- Log out: POST only. Ends the session and shows the login page.
- Protected pages: not logged in goes to the login page. Use `login_required`
  and `never_cache`, so the back button after logout does not show the page.
- Idle timeout: after 15 minutes of inactivity the session ends, the login page is
  shown with "Your session has expired. Please log in again." Propose the simplest
  way in the plan (for example a small middleware that stores a last-activity time
  in the session). The 15 minutes must come from constants.py.
- `role_required(*roles)` decorator: wrong role gives HTTP 403 with the page text
  "You are not authorized to view this page." Test it with a tiny view defined
  only inside the tests, so no extra routes are added.

Reset password (reuse the Feature 1 OTP rules: 6 digits, 5 minutes, hashed, 3rd wrong
attempt invalidates it, a new OTP cancels the earlier one, 5 requests per 15 minutes):
- Request step: ID registered and activated, found in records, not locked: send an
  OTP with purpose `password_reset` to the email or else the mobile number, and show
  "If this ID is registered, a one-time password has been sent."
- ID not registered, pending, or no longer in the records: show exactly the same
  message and send nothing.
- Account locked: reject with "Your account is locked. Please try again later."
- Too many requests: "Too many requests. Please try again in 15 minutes."
  Count OTP requests per user AND per purpose. If Feature 1 currently counts all
  purposes together, tell me in the plan and propose the smallest change.
- Verify step: correct OTP plus a new password of at least 8 characters changes the
  password; saving the password and marking the OTP used happen in ONE
  `transaction.atomic()`. Then the old password no longer works.
- New password shorter than 8: "Password must be at least 8 characters."
- Wrong, expired, third-wrong and new-OTP cases behave as in Feature 1 (reuse the
  same messages from constants.py).
- Changing the password does not unlock a locked account (not in the SRS; list it
  as an assumption).

## Acceptance criteria (Given-When-Then). Implement ALL of them.

FR-02 Log in
1. Registered account, correct ID and password: logged in, home page for my role.
2. Wrong password: rejected, "Invalid ID or password".
3. 5 wrong passwords in a row, then another try: account locked for 15 minutes.
4. Logged in, open a page my role may not use: denied, "You are not authorized to
   view this page."
5. Account locked, correct password: rejected, "Your account is locked. Please
   try again later."
6. Account locked 15 minutes ago, correct password: logged in.
7. ID no longer in the records: rejected, "Your account is no longer active.
   Please contact the university administration."
8. Role in the records changed since registration: I see the home page for my
   current role.

FR-03 Log out
1. Logged in, choose Log out: session ends, login page shown.
2. After logout, back button or the address of a protected page: not shown, login
   page asks me to log in.
3. Inactive for 15 minutes: session ends, login page, "Your session has expired.
   Please log in again."

FR-04 Reset password
1. Choose Forgot password and enter my ID: OTP sent to the email or else mobile.
2. Correct OTP within 5 minutes and a new password of at least 8 characters:
   password changed, I can log in with it.
3. Wrong OTP: rejected, I can try again.
4. 3rd wrong OTP for the same OTP: OTP invalid, I must request a new one.
5. Expired OTP: rejected, I can request a new one.
6. Valid OTP and I request a new one: the earlier OTP is cancelled at once.
7. Password changed: the old password is rejected at login.
8. ID not registered or no longer in the records: "If this ID is registered, a
   one-time password has been sent."
9. Correct OTP and a new password shorter than 8: "Password must be at least 8
   characters."
10. 5 OTP requests in 15 minutes, then another: "Too many requests. Please try
    again in 15 minutes."
11. Account locked, ask for a reset: "Your account is locked. Please try again later."

## Models and settings

- `User`: add `failed_login_attempts` (integer, default 0) and `locked_until`
  (date-time, may be empty), with a new migration. Do not edit existing migrations.
- Add `LOGIN_URL` and anything the idle timeout needs to settings. Change nothing
  else there.

## Pages

- `/login/`: ID + password, links "Forgot password?" and "Register".
- `/logout/`: POST only (the Log out button is a small form in the navbar).
- `/home/`: any logged-in role. One template with a heading and a short text for
  each of the 5 roles (placeholders, real home pages come with later features).
- `/password-reset/`: ID. `/password-reset/verify/`: OTP + new password, with a
  "Request new OTP" button (POST only, like Feature 1).
- `403.html` for access denied.
- `base.html`: navbar shows "Log in" and "Register" when logged out; the user ID,
  role and a "Log out" button when logged in. Add a "Log in" link on the register
  done page.
- Show each message exactly as written above, near the form. Keep the IDs between
  steps in the session in the VIEW only.
- Do not show whether an ID exists anywhere on the login or reset pages.

## Tests

One test per acceptance criterion at least, plus boundaries: 4th vs 5th wrong
password; lock still active at 14:59 and over at 15:00; idle 14:59 vs 15:01;
password of 7 and 8 characters; OTP at 4:59 and 5:01; 2nd vs 3rd wrong OTP; 5th vs
6th OTP request. Invalid input: empty ID, empty password, non-digit OTP. Exceptions:
OTP delivery failure (same behaviour as Feature 1). Cases that must not change
anything: wrong password while locked does not count; unknown ID stores nothing.
Use the fakes (extend `FakeRecordsClient` for removed members and changed roles) and
`unittest.mock.patch` on `django.utils.timezone.now`; never sleep. Extend
`test_architecture.py` for any new module and keep `test_every_constant_is_used`
green.

## When all stages are done

Run every check listed in CLAUDE.md and report the results honestly. Then give me:
(1) the list of files created or changed, (2) your assumptions, (3) anything you
were unsure about, (4) which Feature 1 tests or files you had to change and why.
Do not commit anything. Do not touch `src/db.sqlite3` or anything under `docs/`.