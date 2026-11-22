Stage 2 approved. Answers and reminders for Stage 3:

1. Do not use F(). Keep the current simple version. I will list "parallel
   requests can exceed 5 guesses" in the SDS limitations.
2. Add these tests in Stage 4:
   a. Log in with a test client, reset the password, then the old session no
      longer works. If it does not, tell me. Do not add code to force it.
   b. A 7-character password with a correct OTP leaves that OTP still valid.
   c. OTP requests are counted per purpose: reset requests do not count against
      registration and the other way round.
3. Stage 3 reminders: never_cache inside role_required; middleware.py imports
   constants only; IdleTimeoutMiddleware goes after SessionMiddleware and
   AuthenticationMiddleware in settings; logout is POST only; the IDs between
   steps are kept in the session in the views only.
4. Do not commit. Do not touch db.sqlite3 or docs/. Stop after Stage 3 with a
   plain-language summary.

Start Stage 3.