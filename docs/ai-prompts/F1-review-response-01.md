# Code review: `feature/F1-register` vs `main`

I read all of `src/` on the branch, the tests, and the acceptance criteria in `docs/ai-prompts/F1-prompt-01.md`. I changed no files and ran no checks or tests; the only commands I ran were `git log`, `git diff` and `git show` (plus `cat` and `grep` to read files).

## Checklist verdicts

| #   | Area          | Verdict                                                                                                                                                                                                                                                              |
| --- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Design        | **Pass.** The import table is respected and `test_architecture.py` enforces it. Views call one service each, forms only check input shape, and all business rules live in `services.py`. The one deviation (`urls.py` imports `views`) is documented and reasonable. |
| 2   | Functionality | **Mostly pass, with two real gaps.** A second submit after expiry shows the wrong message. The "5 requests" limit may be counted differently from how AC 11 reads. See findings 1–2.                                                                                 |
| 3   | Complexity    | **Good overall.** One subtle spot: `_check_otp` sometimes saves the OTP and sometimes doesn't (finding 5).                                                                                                                                                           |
| 4   | Tests         | **Strong.** The required boundaries are covered (7/8-character password, 4:59/5:01 expiry, 2nd/3rd wrong attempt, 5th/6th request). A few behaviour tests are missing (finding 11).                                                                                  |
| 5   | Naming        | **Good.** One forward-looking issue: `RegistrationError` will be raised by password reset (FR-04) code too.                                                                                                                                                          |
| 6   | Comments      | **Pass.** Comments mostly explain why (`strip=False`, the transaction, cancelling the earlier OTP).                                                                                                                                                                  |
| 7   | Documentation | **Docstrings complete.** The seven SRS messages match the prompt exactly. Five messages and one button label are not in the AC, so I can't confirm them (finding 6).                                                                                                 |

## Findings (most important first)

**1. `src/campus/services.py:300-302`: High**
> "What does a user see if their OTP expired, they get 'This OTP has expired', and they press Verify again? Doesn't `_check_otp` find no valid OTP and say 'Too many wrong attempts…', which isn't what happened?"

The same wrong message appears whenever no valid OTP exists for any reason other than three wrong tries.

*Fix:* when there's no valid OTP, look at the newest OTP's status instead. If it's `OTP_EXPIRED`, raise `MSG_OTP_EXPIRED`; otherwise raise `MSG_OTP_NO_LONGER_VALID`. Add a test that submits twice after expiry.

**2. `src/campus/services.py:245-248` and AC 11: Medium (needs a team decision)**
> "AC 11 says 'Given I have requested a new OTP 5 times … When I request another'. Right now the registration counts as the 1st request, so the 5th click on 'Request new OTP' is rejected. Which reading does the SRS owner want?"

`test_fifth_request_in_window_is_accepted` encodes the current reading, which is registration plus 4 new requests. Your summary says "at most 5 OTP requests per 15 minutes", and that supports the code.

*Fix:* confirm the reading with the SRS. If the registration OTP shouldn't count, either exclude it from the count or raise the limit. Then update the template text "up to 5 OTPs".

**3. `src/campus/services.py:324-329` (also `246-247`): Medium**
> "What happens if an attacker sends 50 wrong OTPs at the same moment? Each request reads `wrong_attempts = 0`, adds 1 and saves, so don't we get far more than 3 guesses?"

The request-limit check has the same check-then-act race: it counts first and creates afterwards.

*Fix:* increment in the database with `Otp.objects.filter(pk=otp.pk).update(wrong_attempts=F("wrong_attempts") + 1)`, then `refresh_from_db()` before comparing with the maximum. It's still simple enough to explain in a viva.

**4. `src/campus/views.py:45-48` and `services.py:277`: Medium**
> "If the email/SMS service is down, `send_otp` raises (e.g. `ConnectionError`). The transaction rolls back, which is good, but doesn't the user then get a 500 error page with no explanation?"

*Fix:* in `delivery.py`, define one delivery exception and wrap the error in it. Catch that exception in services and turn it into a `RegistrationError` with a message from the SRS. If the SRS has no message for this, ask the SRS owner for one.

**5. `src/campus/services.py:280-311`: Medium (complexity)**
> "`_check_otp` saves the OTP on expiry and on a wrong code, but only marks it used, without saving, on success. Could a teammate reusing it for FR-04 forget to save and leave the OTP reusable?"

*Fix:* have `_check_otp` handle only rejections and return the valid OTP. Then `verify_registration_otp` sets `status = OTP_USED` and saves the OTP and the user inside one `atomic()`. That way the code that marks the OTP used is the code that saves it.

**6. `src/campus/constants.py:101-107` and `templates/campus/register_verify.html:33`: Low**
> "`MSG_OTP_INCORRECT`, `MSG_OTP_EXPIRED`, `MSG_OTP_NO_LONGER_VALID`, `MSG_OTP_FORMAT` and `MSG_NEW_OTP_SENT` aren't in the AC list. Are they in the SRS Wiki word for word? Also, the spec says the button is 'Request new OTP', but the template says 'Request a new OTP'."

The constants module docstring also claims that every message matches the SRS word for word.

*Fix:* check these against the Wiki and copy its exact wording. If they aren't in the SRS, change the docstring to say which messages come from the SRS and which come from the UI design.

**7. `constants.py:95,100`, `register.html:30`, `register_verify.html:38`: Low**
> "If `PASSWORD_MIN_LENGTH` or `OTP_REQUEST_LIMIT` changes, aren't the '8', '5' and '15' typed into the messages and templates silently wrong?"

*Fix:* add a test asserting that each message and template text contains `str(PASSWORD_MIN_LENGTH)`, `str(OTP_REQUEST_LIMIT)` and so on, or pass those values to the template.

**8. `src/campus/services.py:44`: Low (naming)**
> "The OTP helpers are 'written so FR-04 password reset can reuse them', but they raise `RegistrationError`. Will a password-reset failure really be a 'registration' error?"

*Fix:* rename it to `OtpError` or `ServiceError` now, while it's cheap.

**9. `src/fixit_campus/settings.py:87-100`: Low**
> "`AUTH_PASSWORD_VALIDATORS` is configured but never called. If someone later adds `validate_password()`, won't `12345678` be rejected even though the SRS allows it?"

*Fix:* remove the validators or empty the list, and add a comment saying the length rule lives in `services.py`.

**10. `src/fixit_campus/urls.py:10`: Low**
> "CLAUDE.md says not to use the admin for roles. Do we need `admin/` routed at all? A superuser could edit `role` and `account_status` there and bypass the services."

*Fix:* remove the route, or agree as a team to keep it for development only.

**11. Missing tests: Medium as a group**
- Two expired-OTP cases: submitting a second time after expiry (this would have caught finding 1), and a view-level test for the expired and 3rd-wrong messages.
- After requesting a new OTP, typing the old code is rejected. Today the test only checks the old row's status.
- Window boundary on the other side: at 14:59 the 6th request is still rejected. Only 15:00 is tested, which relies on `__gt`.
- Delivery fails during `request_new_registration_otp`: the previous OTP must stay valid.
- A delivery failure in the view (see finding 4).
- `test_registration_error_keeps_message` only repeats the code; it could be dropped.

**12. `src/campus/views.py:65-67` and `services.py:216`: Low**
> "If the session holds an ID whose user no longer exists (e.g. the database was reset), the verify page says 'IUB ID number not found. Please contact the university administration.' Is that right? And after 'This ID is already registered.' the session key is never cleared. Should it be?"

*Fix:* clear `SESSION_REGISTER_ID_NUMBER` and redirect to `/register/` when verification fails because the account is missing or already active.

**13. `src/campus/tests/test_architecture.py:93-99`: Low**
> "Could a view do `get_user_model().objects…` without importing `campus.models`? The import check wouldn't notice."

*Fix:* add a simple check that `views.py` contains no `.objects` and no `.save(`, since CLAUDE.md bans both.

**Nit: `src/campus/models.py:84`.** The clock is frozen in tests, so all OTPs get the same `created_at` and the newest-first order is arbitrary. Use `ordering = ("-created_at", "-id")` as a tie-breaker.

## What I could not verify
- **Tool results:** I didn't run `flake8`, `black`, `pylint`, `manage.py check` or `manage.py test`, because the brief allowed only read-only git commands. I don't know whether the suite passes on this machine.
- **SRS Wiki:** I couldn't open it. I checked messages only against the AC copied into `docs/ai-prompts/F1-prompt-01.md`.
- **Concurrency (finding 3):** this comes from reading the code. I didn't reproduce it with parallel requests.
- **Not reviewed in detail:** the migration (I assumed it matches the models), the `docs/ai-prompts/*` response files, and how the templates render in a browser.
- **Out of scope:** whether user enumeration (different messages for unknown versus registered IDs) is acceptable. The SRS requires these messages, so I didn't flag it.