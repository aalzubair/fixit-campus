Stage 1 approved. Answers and reminders for Stage 2:

1. Yes, tighten test_every_constant_is_used in Stage 4 so a name in a docstring
   or comment does not count as a use. If this exposes unused Feature 1
   constants, list them in the report. Do not delete them silently.
2. is_locked(now) must be strictly locked_until > now. Confirm this.
3. In Stage 2 keep these rules: the failed-attempt count and the lock are
   saved BEFORE the error is raised and never rolled back by transaction.atomic();
   a wrong password while locked is not counted; after a lock has expired the
   count restarts from 0; the IUB records check happens only after the correct
   password.
4. Do not commit. Do not touch db.sqlite3 or docs/. Stop after Stage 2 with a
   plain-language summary.

Start Stage 2 (services.py).