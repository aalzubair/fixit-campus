Before I write any code, here's the plan. CLAUDE.md asks for this step and for your approval first.

## Plan

**`src/campus/services.py`**
- **Rename:** `RegistrationError` becomes `ServiceError` in the class, every `raise`, and every docstring (finding 8).
- **Finding 1:** add a small helper, `_missing_otp_message(user, purpose)`. It looks at the user's newest OTP for that purpose. If that OTP is `OTP_EXPIRED`, it returns `MSG_OTP_EXPIRED`; otherwise it returns `MSG_OTP_NO_LONGER_VALID`. `_check_otp` raises with this message when no valid OTP exists.
- **Finding 5:** `_check_otp` will only reject or return the valid OTP, without changing it. Expired and wrong attempts are still saved before the error is raised, as now. `verify_registration_otp` then sets `otp.status = OTP_USED` and saves the OTP and the user inside one `transaction.atomic()`.

**`src/campus/views.py`**
- Rename the imports and `except` clauses to `ServiceError` (finding 8).

**`src/campus/constants.py`**
- Module docstring only (finding 6). It will list the five messages copied from SRS FR-01 (`MSG_ID_NOT_FOUND`, `MSG_ALREADY_REGISTERED`, `MSG_PASSWORD_TOO_SHORT`, `MSG_NO_CONTACT_DETAILS`, `MSG_TOO_MANY_REQUESTS`).
- It will name the other five (`MSG_OTP_INCORRECT`, `MSG_OTP_EXPIRED`, `MSG_OTP_NO_LONGER_VALID`, `MSG_OTP_FORMAT`, `MSG_NEW_OTP_SENT`) as UI-design or our own wording, not checked against the SRS Wiki.

**`src/campus/models.py` and a new `migrations/0002_…py`**
- Change `Otp.Meta.ordering` to `("-created_at", "-id")`.
- Create the migration with `python manage.py makemigrations campus`. Django records ordering changes in migrations, so one is needed.

**`src/campus/tests/test_architecture.py`**
- New test `test_views_do_not_touch_the_database_directly` (finding 13). It reads `views.py` and checks that it contains neither `.objects` nor `.save(`.

**`src/campus/tests/test_services_register.py`**
- Rename to `ServiceError` throughout.
- `test_second_submit_after_expiry_still_says_expired`: submit twice after 5:01; both show `MSG_OTP_EXPIRED`.
- `test_old_code_is_rejected_after_new_otp`: patch `_generate_otp_code` so the new code is guaranteed to differ from the old one; a random code could match the old one by chance and make the test flaky. The old code then gets `MSG_OTP_INCORRECT` and the new code still works.
- `test_sixth_request_at_fourteen_fifty_nine_is_rejected`: new test.
- `test_sixth_request_at_fifteen_minutes_is_accepted`: the existing `test_requests_older_than_window_do_not_count`, renamed so the 14:59/15:00 pair reads clearly. The test body stays the same.
- `test_failed_new_otp_delivery_keeps_previous_otp_valid`: with `FailingOtpSender`, `ConnectionError` propagates, because finding 4 is left unchanged. Afterwards the earlier OTP is still `OTP_VALID` and the earlier code still activates the account.

**Not touched:** findings 2, 3, 4, 7, 9, 10 and 12, everything in `docs/`, and the templates.

**Checks afterwards:**
- From the repository root: `flake8 src`, `black --check src` and `pylint src/campus src/fixit_campus`.
- From `src/`: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`, and `coverage run manage.py test` followed by `coverage report -m`. Coverage 7.17.3 is already in `requirements.txt`, so nothing new gets installed.

## Assumptions
- Typing the old code after a new OTP has been requested gives `MSG_OTP_INCORRECT`, and it counts as a wrong attempt against the new OTP. That's how the code already behaves, and the brief didn't ask to change it.
- I can't tell which of the five non-SRS messages come from the UI design and which are our own wording. The docstring will group them together as "UI design or our own wording, not yet checked against the SRS Wiki". Tell me if you know the split.
- No git commands will be run; you'll do the git work.

Shall I go ahead?