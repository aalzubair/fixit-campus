- Date: 20 Nov 2026
- Tool: Claude Code
- Purpose: Stage 2 summary

Stage 2 is done, and flake8, black and pylint all pass apart from the old settings line. I'm stopping here for your review.

## What `services.py` does

**Three public functions, one per user action:**
- **`register_user(id_number, password)`** checks the password length and looks up the ID in the records. It rejects IDs that are already active or locked. For a new person it creates a user waiting for activation (`is_active=False`). For someone already waiting, it replaces the old password (AC 12). Then it sends an OTP to the email, or to the mobile number if there is no email.
- **`request_new_registration_otp(id_number)`** cancels the earlier OTP and sends a new one (AC 6), unless 5 OTPs were already sent in the last 15 minutes (AC 11).
- **`verify_registration_otp(id_number, code)`** handles the code the user types:

  | Situation | Result |
  |---|---|
  | Correct and within 5 minutes | OTP marked used, account becomes active and `is_active=True` (AC 2) |
  | Wrong | "Incorrect OTP…" (AC 3) |
  | 3rd wrong try on the same OTP | OTP marked invalid (AC 4) |
  | Expired | OTP marked expired (AC 5) |

**Errors:** any rejected step raises `RegistrationError`, which carries the exact SRS message. The view will just show `error.message`.

**Helpers:** small private functions that each do one job: look up the records, check the request limit, create and send the OTP, check the OTP, count a wrong attempt. The OTP helpers take a `purpose`, so password reset (FR-04) can reuse them later.

**Security:**
- The code comes from `secrets`.
- Only `make_password(code)` is stored.
- `check_password` compares in constant time.
- Nothing is printed or logged.

**Transactions:** registration and sending run inside `transaction.atomic()`, so a rejected or failed send rolls back the new password. A wrong or expired OTP is saved *before* the error is raised on purpose, so the attempt count isn't lost.

## Check results
- `flake8`: clean. `black --check`: clean. `manage.py check`: no issues.
- `pylint`: 9.96/10. The only finding is still the Django-generated long line in `settings.py:89` from Stage 1, which I haven't changed.
- **Quick run of the full flow:** I used a throwaway script on a temporary test database, kept in the scratchpad rather than the repo. Every rule gave the expected result: short password, unknown ID, no contact details, mobile-only delivery, re-registration replacing the password, wrong, wrong, then invalid on the 3rd try, a 6th request rejected with only 1 valid OTP left, expired at 5:01, success at 4:59 with the role `faculty`, and "already registered" after activation. The real tests come in Stage 4.

## Things you should know
1. **The password-length rule is in the service, not the form.** This is a change from my plan, because CLAUDE.md puts all business rules in `services.py`. In Stage 3 the form will only check that the fields are not empty.
2. **An old, cancelled OTP typed in counts as a wrong attempt** against the current OTP. It is simply a wrong code for the OTP that is now valid.
3. **The role is copied from the records at registration.** It isn't read again at verification. The two steps are at most minutes apart.
4. **Two users verifying at exactly the same moment** aren't protected by row locks. That's fine for SQLite and a student project, but say if you'd like it handled.
5. **`src/db.sqlite3` is an empty (0 bytes) file dated 19 Nov 19:00.** My smoke script didn't create it; it was most likely created by `manage.py check` in Stage 1. It's ignored by git and no migrations have been applied to it. Delete it or run `migrate` as you prefer.

Shall I continue with Stage 3 (forms, views, URLs and templates)?