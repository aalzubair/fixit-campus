- Date: 20 Nov 2026
- Tool: Claude Code
- Purpose: Stage 3 summary

I've finished Stage 3, and both registration pages work end to end in a quick test-client run. flake8 and black are clean; pylint still flags only the long line in `settings.py` from Stage 1. I'm stopping here for your review.

## What each file does

| File                                    | What it does                                                                                                                                                                                                  |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/campus/constants.py`               | **Changed.** New constants for this stage: the ID number's maximum length, the OTP pattern (built from `OTP_LENGTH`), the session key, the four URL names, the three template names, and one new message.     |
| `src/campus/forms.py`                   | **New.** `RegisterForm` checks only that the ID number and password are filled in. The password keeps any spaces it contains. `OtpForm` accepts exactly 6 digits and otherwise shows "Enter the 6-digit OTP." |
| `src/campus/views.py`                   | **Changed.** Four small views. Each one validates with a form, calls a single service, then shows a page or redirects. See below.                                                                             |
| `src/campus/urls.py`                    | **New.** `/register/`, `/register/verify/`, `/register/verify/new-otp/` and `/register/done/`.                                                                                                                |
| `src/fixit_campus/urls.py`              | **Changed.** Adds `path("", include("campus.urls"))` next to the existing admin line, and replaces the long generated comment with a short docstring.                                                         |
| `templates/campus/base.html`            | **New.** Loads Bootstrap 5.3.3 from a CDN. It has an integrity hash, which I checked against the real file. It shows "FixIt Campus" above a centred card, like the UI designs.                                |
| `templates/campus/_errors.html`         | **New.** A small piece that shows a list of errors in red. The two forms reuse it, so the markup isn't repeated.                                                                                              |
| `templates/campus/register.html`        | **New.** Step 1 of 2, following the UI design. Errors appear under the field they belong to, or above the "Send OTP" button.                                                                                  |
| `templates/campus/register_verify.html` | **New.** Step 2 of 2. It has the OTP field, a "Verify" button, and a separate "Request a new OTP" form, plus the note about 5 OTPs in 15 minutes and a "Back to registration" link.                           |
| `templates/campus/register_done.html`   | **New.** Says "Account activated… You can now log in."                                                                                                                                                        |

What the four views do:
- **`register_view`**: on success, puts the ID number in the session and goes to the verify page.
- **`register_verify_view`**: sends you back to `/register/` if you haven't registered in this session. On a correct OTP, it removes the ID from the session and goes to the done page.
- **`register_new_otp_view`**: accepts POST only, because it cancels the earlier OTP. It shows "A new OTP has been sent…" or the "Too many requests…" error, then goes back to the verify page.
- **`register_done_view`**: shows the success page.

## Check results
- **`flake8`:** clean.
- **`black --check`:** clean. On the first run, one line in `forms.py` was 89 characters and black wanted to re-wrap `urls.py`. I ran `black` on those two files only and then re-checked.
- **`pylint`:** 9.97/10. The only finding is still the long Django-generated line in `settings.py:89`.
- **`manage.py check`:** no issues.
- **Quick page run** (throwaway script in the scratchpad, temporary database, not part of the repo):

  | Request | What it showed |
  |---|---|
  | Empty fields | "This field is required." twice |
  | Short password | The exact SRS message |
  | Unknown ID | The exact SRS message |
  | Valid registration | Redirect to `/register/verify/` |
  | Non-digit OTP | "Enter the 6-digit OTP." |
  | Wrong OTP | "Incorrect OTP…" |
  | Request a new OTP | Success message |
  | GET on the new-OTP URL | 405 |
  | Correct OTP | `/register/done/` |
  | Registering again | "This ID is already registered." |

## Things you should know
1. **"Request a new OTP" has its own URL** (`/register/verify/new-otp/`) and its own small form. It doesn't share the Verify form. This way the view doesn't need to work out which button was pressed, and requesting a new OTP doesn't make you fill in the OTP field.
2. **Messages after a redirect use Django's messages framework.** A new OTP and too many requests are shown this way; it was already installed, so no settings change was needed.
3. **The "Verify" button stays enabled when the OTP is invalid.** The UI design greys it out, but that would need extra state in the view. Pressing it simply shows the "no longer valid" message again. I can add it if you want.
4. **There's no "Already registered? Log in" link yet,** because the login page (FR-02) doesn't exist.
5. **A logged-in user can still open `/register/`.** There's no login yet, so I added no login or role checks to these views.
6. **"A new OTP has been sent. The earlier OTP no longer works." is my own wording.** The SRS doesn't define this message, so please check it.

Shall I continue with Stage 4 (fakes, all the tests, `test_architecture.py`, then the full check run)?