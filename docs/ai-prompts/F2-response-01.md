I've read everything the task lists, plus SRS FR-02 to FR-04, the account and OTP state diagrams and the login and reset UI designs. The baseline is **97 tests, all passing**. Nothing is written yet. Here is the plan for your approval.

# Plan: Feature 2 (FR-02, FR-03, FR-04)

## Decisions for you to approve first

**D1. Remove the `locked` account status (recommended).** Lock state will come only from `locked_until`. If the `locked` status stays, two fields describe the same thing and can disagree, and no code would ever set it.
- Remove `ACCOUNT_LOCKED` and its entry in `ACCOUNT_STATUS_CHOICES`.
- The new migration includes an `AlterField` for the smaller choices list.
- Feature 1 effects: the docstring of `_raise_if_registered` changes ("Active and locked accounts…"). The test `test_locked_id_is_rejected_as_already_registered` changes to lock the account with `locked_until`. The rule it checks stays the same.

**D2. Count OTP requests per purpose. Feature 1 currently counts all purposes together.** `_check_request_limit(user, now)` counts every OTP row of the user.
- Smallest change: add a `purpose` parameter and filter on it, and pass the purpose through from `_issue_otp`.
- Feature 1 behaviour does not change, because a pending user only ever has registration OTPs.
- I'll leave `_issue_otp`'s "cancel every valid OTP of this user" as it is. The SRS glossary says only one OTP is valid at a time.

**D3. Idle timeout uses a new module, `campus/middleware.py` (Presentation layer, imports only `constants`).**
- After each request by a logged-in user, it saves the current time in the session. It does this after the view runs, so the login request itself is stamped too.
- Before each request, if the user has been idle for 15 minutes or more: log out, add the message "Your session has expired. Please log in again.", and redirect to `/login/`.
- Why not Django's `SESSION_COOKIE_AGE` instead? With it, the session just disappears, so we couldn't tell "expired" from "never logged in" and couldn't show the message.
- `CLAUDE.md`'s layout and dependency table don't list `middleware.py`. I won't edit `CLAUDE.md` unless you ask. I'll add the rule to `test_architecture.py`.

**D4. `role_required(*roles)` goes in `views.py`, not a new module.** All future views live there anyway. It includes `login_required`, and a wrong role renders `403.html` with HTTP 403. The 403 uses `HTTPStatus.FORBIDDEN` from the standard library, so there's no magic number.

## Stage 1: constants, model, migration, settings

| File                | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `constants.py`      | **New rule numbers:** `LOGIN_MAX_FAILED_ATTEMPTS = 5`, `ACCOUNT_LOCK_MINUTES = 15`, `SESSION_IDLE_TIMEOUT_MINUTES = 15`.<br>**New session keys:** `SESSION_LAST_ACTIVITY`, `SESSION_RESET_ID_NUMBER`.<br>**New URL names:** login, logout, home, password_reset, password_reset_verify, password_reset_new_otp.<br>**New templates:** login, home, password_reset, password_reset_verify, 403.<br>**New SRS messages:** `MSG_INVALID_LOGIN`, `MSG_ACCOUNT_LOCKED`, `MSG_ACCOUNT_NO_LONGER_ACTIVE`, `MSG_NOT_AUTHORIZED`, `MSG_SESSION_EXPIRED`, `MSG_RESET_OTP_SENT`.<br>**Home page text:** one heading and text per role, as a tuple of tuples (immutable).<br>**Remove:** `ACCOUNT_LOCKED` (D1). |
| `models.py`         | `User` gets `failed_login_attempts` (integer, default 0) and `locked_until` (date-time, may be empty), plus two small helpers like `Otp.is_expired`:<br>• `is_locked(now)`: true when `locked_until > now`<br>• `clear_lock()`: count back to 0 and `locked_until = None`, does not save                                                                                                                                                                                                                                                                                                                                                                                                            |
| `migrations/0003_…` | New, made by `makemigrations`: the two fields and the D1 `AlterField`. Existing migrations are not touched.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `settings.py`       | Add `LOGIN_URL` (the login URL name, imported from `constants` so the name is written only once) and append the idle-timeout middleware to `MIDDLEWARE`. Nothing else changes.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Stage 2: `services.py`

**`log_in_user(id_number, password) -> User`** follows your eight steps in order:
1. Unknown or pending ID: "Invalid ID or password". Nothing is saved.
2. Locked (`is_locked(now)`): locked message. No attempt is counted.
3. `locked_until` set but in the past: `clear_lock()`, so counting restarts at 0.
4. Wrong password: count +1. On the 5th, set `locked_until = now + 15 min`. Save, then reject with "Invalid ID or password".
5. Correct password: look the ID up in the records. Not found: "no longer active".
6. If the role in the records differs, update the stored role.
7. `clear_lock()`, save, and return the user. The view calls Django's `login()`.

**`request_password_reset(id_number) -> None`**
- Unknown, pending, not in the records, or no contact details: return quietly, nothing sent.
- Locked: locked message.
- Otherwise: `_issue_otp(user, destination, OTP_PURPOSE_PASSWORD_RESET)` inside `transaction.atomic()`.
- It reuses `_find_member_and_destination`, catching its `ServiceError` to stay quiet.
- The same function serves the "Request new OTP" button.

**`reset_password(id_number, code, new_password) -> None`**
- Checks the password length first (`_check_password_length`), so a short password doesn't use up an OTP attempt.
- Then `_check_otp(user, PASSWORD_RESET, code)`. An unknown or inactive ID gets "Incorrect OTP", so it can't be used to find IDs.
- Then marks the OTP used and saves the new password in one `transaction.atomic()`.

**Feature 1 edits:** only D1 and D2.

## Stage 3: forms, views, middleware, urls, templates

| File                | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `forms.py`          | • `LoginForm(RegisterForm)`: the same fields, so nothing is copied.<br>• `PasswordResetRequestForm` (`id_number`)<br>• `PasswordResetVerifyForm(OtpForm)`: adds `new_password` (`strip=False`)                                                                                                                                                                                                                                                                                                                                                                                         |
| `views.py`          | • `role_required`<br>• `login_view`: on success, `login()` and redirect to `/home/`. If you're already logged in, redirect to home.<br>• `logout_view`: `@require_POST`, `logout()`, redirect to login<br>• `home_view`: `login_required` + `never_cache`<br>• `password_reset_view`: always stores the ID in the session in the view, shows `MSG_RESET_OTP_SENT`, and redirects to verify<br>• `password_reset_verify_view`: on success, clears the session key and redirects to login with a success message<br>• `password_reset_new_otp_view`: POST only, shows `MSG_NEW_OTP_SENT` |
| `middleware.py`     | `IdleTimeoutMiddleware` (D3)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `urls.py`           | `/login/`, `/logout/`, `/home/`, `/password-reset/`, `/password-reset/verify/`, `/password-reset/verify/new-otp/`. No test-only routes.                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `templates/campus/` | **New:** `login.html`, `home.html` (one template with a heading and text per role), `password_reset.html`, `password_reset_verify.html`, `403.html`, and `_messages.html` (a shared include for flash messages).<br>**Changed:** `base.html` gets a navbar (logged out: Log in and Register; logged in: ID, role and a Log out form). `register_done.html` gets a "Log in" link. `register_verify.html` uses `_messages.html` instead of its own inline loop (DRY; it looks the same).                                                                                                 |

## Stage 4: tests, then all checks

| File                                    | Change                                                                                                                                                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/fakes.py`                        | `FakeRecordsClient` gains `remove_member(id)` and `change_role(id, role)`.                                                                                                                        |
| `tests/base.py`                         | Keeps the fake records in `self.records` so tests can change them. Adds a `lock_account` helper.                                                                                                  |
| `test_services_login.py` (new)          | AC1–8, 4th vs 5th wrong password, lock at 14:59 vs 15:00, wrong password while locked doesn't count, unknown ID stores nothing, pending ID                                                        |
| `test_services_password_reset.py` (new) | AC1–11, OTP at 4:59 vs 5:01, 2nd vs 3rd wrong OTP, 5th vs 6th request, password of 7 vs 8 characters, delivery failure rolls back, per-purpose counting                                           |
| `test_views_auth.py` (new)              | Login and logout pages, POST-only logout, `never_cache` headers, protected pages redirect to login, idle at 14:59 vs 15:01, navbar, `role_required` 403 using a tiny view defined inside the test |
| `test_views_password_reset.py` (new)    | Reset pages, same message for unknown IDs, request-new-OTP button, empty and non-digit input                                                                                                      |
| `test_forms.py`, `test_models.py`       | New form and helper tests                                                                                                                                                                         |
| `test_services_register.py`             | Only the D1 test change                                                                                                                                                                           |
| `test_architecture.py`                  | Add a `"middleware": {"constants"}` rule                                                                                                                                                          |

Then I'll run `flake8`, `black --check`, `pylint`, `manage.py check` and `manage.py test` and report the results honestly.

## Assumptions
- A password reset doesn't unlock a locked account or reset the wrong-password count.
- The reset request checks things in this order: registered and active, then in the records, then locked. So a locked member who has left the university gets the general message.
- An active user whose records entry has no contact details gets the general message, and nothing is sent.
- After login, the user always goes to `/home/`. The `?next=` parameter is ignored, as the spec says.
- The idle timeout ends the session at exactly 15:00 of inactivity (`>=`), the same boundary style as the lock.

## Unsure, flagged now
- **The SRS itself reveals that an ID exists.** On the reset pages, the "locked" and "too many requests" messages can only appear for real accounts.
- **Response timing can reveal an ID.** A login with an unknown ID returns faster than one with a known ID, because no password hash is checked. I'm not adding a fake hash check unless you want it.

**Can I go ahead with Stage 1, and do you approve D1–D4?**