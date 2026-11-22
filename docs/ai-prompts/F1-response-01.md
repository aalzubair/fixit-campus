I've read CLAUDE.md, the FR-01 section of the SRS, the OTP and account state diagrams, and the register/verify UI designs. Here is the plan. I haven't written or changed anything yet.

# Plan: Feature 1, Register with OTP (FR-01)

## Stage 1: setup, constants, models, records, delivery

| File                                                          | Action     | What it does                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/campus/admin.py`                                         | **delete** | Unused stub.                                                                                                                                                                                                                                                                                                                                                                |
| `src/campus/tests.py`                                         | **delete** | Replaced by the package `src/campus/tests/`.                                                                                                                                                                                                                                                                                                                                |
| `src/campus/apps.py`, `__init__.py`, `migrations/__init__.py` | change     | Add the docstrings that pylint requires. No change to behaviour.                                                                                                                                                                                                                                                                                                            |
| `src/fixit_campus/settings.py`                                | change     | Add `"campus"` to `INSTALLED_APPS`, plus `AUTH_USER_MODEL = "campus.User"`, `FIXIT_OTP_SENDER = "campus.delivery.ConsoleOtpSender"`, `FIXIT_RECORDS_CLIENT = "campus.records.JsonRecordsClient"` and `FIXIT_RECORDS_FILE = BASE_DIR / "campus" / "data" / "iub_records.json"`. Nothing else changes.                                                                        |
| `src/fixit_campus/urls.py`                                    | change     | Add `include("campus.urls")`. I'll keep the existing `admin/` line.                                                                                                                                                                                                                                                                                                         |
| `src/campus/constants.py`                                     | create     | All rule numbers: OTP length 6, OTP lifetime 5 min, max 3 wrong attempts, 5 requests per 15 min, password minimum 8, field lengths. Also roles, account statuses, OTP statuses and purposes (as tuples of choices), every SRS message, and session key and template names. Everything is immutable.                                                                         |
| `src/campus/models.py`                                        | create     | **`User(AbstractUser)`**: `username` holds the IUB ID, plus `role` and `account_status`. Passwords use Django hashing. **`Otp`**: user FK, `purpose`, `code_hash`, `status`, `wrong_attempts`, `created_at`, `expires_at`, and one small helper `is_expired(now)`. The `Otp` rows also act as the request log for the "5 per 15 minutes" rule, so no extra table is needed. |
| `src/campus/migrations/0001_initial.py`                       | generate   | Made with `makemigrations` (the first migration, with the custom user model).                                                                                                                                                                                                                                                                                               |
| `src/campus/data/iub_records.json`                            | create     | 5 fake people, one per role. One has only a mobile number and one has no contact details.                                                                                                                                                                                                                                                                                   |
| `src/campus/records.py`                                       | create     | `UniversityMember` (a frozen dataclass), the abstract `RecordsClient.find_member(id_number)`, `JsonRecordsClient` (reads the JSON file and does not import models), and `get_records_client()`, which loads the class named in settings.                                                                                                                                    |
| `src/campus/delivery.py`                                      | create     | The abstract `OtpSender.send_otp(destination, code)`, `ConsoleOtpSender` (prints the code, for development only), and `get_otp_sender()`.                                                                                                                                                                                                                                   |

## Stage 2: `src/campus/services.py`
- `RegistrationError(Exception)` carries the exact SRS message that the view shows.
- `register_user(id_number, password)`: looks up the records (AC 7, AC 10). It rejects an account that is already active or locked (AC 8). It creates the pending user, or replaces the password of a user who is still pending (AC 12). Then it issues an OTP (AC 1).
- `request_new_registration_otp(id_number)`: AC 6 and AC 11.
- `verify_registration_otp(id_number, code)`: handles correct (AC 2), wrong (AC 3), the 3rd wrong attempt making the OTP invalid (AC 4) and expired (AC 5).
- Private helpers:
  - `_issue_otp` checks the rate limit, cancels the earlier valid OTP (status becomes invalid), makes the code with `secrets`, saves only the hash, and sends it to the email or, if there is none, the mobile number.
  - `_check_otp` does the comparison.
- The OTP is hashed and checked with Django's `make_password` / `check_password`, which add a salt and compare in constant time. Time comes from `timezone.now()` so tests can patch it. The steps that change several rows run inside `transaction.atomic()`.

## Stage 3: presentation
- `forms.py`: `RegisterForm` (ID required; password required with a minimum of 8 characters and the exact AC 9 message). `OtpForm` (exactly 6 digits).
- `views.py`:
  - `register_view` validates the form, calls `register_user`, stores the ID in the session, and redirects to the verify page.
  - `verify_otp_view` has two buttons, Verify and Request new OTP, on one form. It redirects to `/register/` if the session has no ID.
  - `register_done_view` shows the success page.
- `urls.py`: `/register/`, `/register/verify/`, `/register/done/`.
- Templates in `templates/campus/`: `base.html` (Bootstrap 5 from a CDN), `register.html`, `verify_otp.html` and `register_done.html`. They follow the UI designs ("Step 1 of 2", "Send OTP", and so on), show errors under the form, and each starts with an HTML comment.

## Stage 4: tests and checks
In `src/campus/tests/`:

| File                        | What it covers                                                                                                                         |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `__init__.py`               | Makes the folder a test package.                                                                                                       |
| `fakes.py`                  | `FakeOtpSender` and `FakeRecordsClient`.                                                                                               |
| `test_records.py`           | The JSON client, using a temporary file.                                                                                               |
| `test_delivery.py`          | The sender interface and `get_otp_sender()`.                                                                                           |
| `test_models.py`            | `Otp.is_expired`.                                                                                                                      |
| `test_services_register.py` | Every AC, plus these boundaries: password of 7 and 8 characters, OTP at 4:59 and 5:01, 2nd and 3rd wrong attempt, 5th and 6th request. |
| `test_forms.py`             | Empty ID, empty password, non-digit OTP.                                                                                               |
| `test_views_register.py`    | Pages, session and messages shown.                                                                                                     |
| `test_architecture.py`      | Parses imports with `ast` and checks them against the CLAUDE.md dependency table.                                                      |

Then I'll run flake8, black, pylint, `check` and `test`, and report the results honestly.

## Open questions (my default is shown; reply "approved" to accept all of them)
1. **Messages that the SRS does not define.** The UI designs give "Incorrect OTP. Please check it and try again." (AC 3) and "Too many wrong attempts. This OTP is no longer valid. Please request a new OTP." (AC 4). For an **expired** OTP I'd use "This OTP has expired. Please request a new OTP." When there is no valid OTP at all (for example, it was already cancelled), I'd reuse the AC 4 "no longer valid" wording. I'd keep Django's "This field is required." for empty fields and use "Enter the 6-digit OTP." for a non-digit OTP.
2. **What counts toward the 5-per-15-minutes limit.** By default every OTP sent counts, including the first one at registration and those for both purposes. That means the 6th send within 15 minutes is rejected.
3. **The account after activation.** By default `account_status` becomes `active` and Django's `is_active` stays `True`. The login feature (FR-02) will check `account_status`. Because login doesn't exist yet, success shows a "Your account is activated" page.
4. **Password rules.** By default only the 8-character minimum applies. I won't call Django's other password validators that are in settings (common or all-numeric passwords), because the SRS doesn't list them and you asked me not to touch settings.

No new dependencies, no git commands, and nothing under `docs/` will change. Should I start Stage 1?