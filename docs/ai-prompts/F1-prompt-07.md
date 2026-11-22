An independent review found issues (docs/ai-prompts/F1-review-response-01.md). Fix ONLY these, by finding number:
1. After an expired OTP, a second submit must again show the "expired" message: when no valid OTP exists, look at the newest OTP; if it is expired raise MSG_OTP_EXPIRED, otherwise MSG_OTP_NO_LONGER_VALID.
5. Make _check_otp only reject or return the valid OTP; verify_registration_otp marks it used and saves the OTP and user inside one atomic block. A wrong attempt must still be saved before the error is raised.
8. Rename RegistrationError to ServiceError everywhere (code, tests, docstrings).
6. Fix only the constants.py module docstring so it says which messages come from the SRS and which from the UI design or are our own wording.
13. Add a test that views.py contains no ".objects" and no ".save(".
Nit: add ordering ("-created_at", "-id") to the Otp model (create the migration if needed).
Add tests for: finding 1 (submit twice after expiry); the old OTP code is rejected after a new OTP is requested; the 6th request is still rejected at 14:59 and accepted at 15:00; if delivery fails during request_new_registration_otp the previous OTP stays valid.
Do NOT change findings 2, 3, 4, 7, 9, 10, 12. Then run every check in CLAUDE.md plus coverage and report honestly.