Stage 3 approved. Answers: keep "Register" on the login page; keep the two
new-OTP views separate; the missing Show button and countdown go into the
SDS limitations.

Two questions before Stage 4:
1. Does LoginForm inherit any password-length rule from RegisterForm? A wrong
   3-character password must give "Invalid ID or password" and COUNT as a
   failed attempt. If the form blocks it, fix it with the smallest change.
2. Your end-to-end check used the Django test client, which skips CSRF checks.
   Confirm the Log out form in the navbar and all new forms contain
   {% csrf_token %}.

Add these tests in Stage 4, together with the ones already agreed:
a. A client created with enforce_csrf_checks=True: logout POST without a token
   is refused, and the rendered navbar form contains the token.
b. A wrong 3-character password at login counts as a failed attempt.
c. Idle timeout at 14:59 stays logged in and at 15:01 is logged out. Also
   state in a comment what happens at exactly 15:00.

Do not commit. Do not touch db.sqlite3 or docs/. Start Stage 4, run all
checks from CLAUDE.md and then give the final report (files changed,
assumptions, unsure points, Feature 1 tests changed and why).