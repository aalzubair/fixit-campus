Stage 2 is done, and the tests are where they should be. All 97 Feature 1 tests pass, and black, flake8, pylint (10.00/10) and `manage.py check` are clean. The new rules have no tests yet (they come in Stage 4), and I haven't tried them by hand.

The only failure is `test_every_constant_is_used`. It's down from 17 failing subtests to 15, and every one left is a URL, template or session constant that Stage 3 will use.

## What I changed in `services.py`

**`log_in_user(id_number, password)`** runs your checks in this order:
1. **Unknown or pending ID:** "Invalid ID or password". Nothing is saved.
2. **Locked:** "Your account is locked…". This comes before the password check, so a wrong password while locked is never counted.
3. **Lock has run out:** the count goes back to 0 and the lock is removed.
4. **Wrong password:** the count goes up by 1, and the 5th wrong password sets `locked_until = now + 15 min`. This is saved first, then the error is raised. There's no `transaction.atomic()` in this function, so nothing can roll it back. The docstring says why.
5. **Correct password:** only now are the IUB records checked. If the ID isn't there: "Your account is no longer active…".
6. **Success:** the role is copied from the records, the count and lock are cleared, and the user is returned. The view will start the session in Stage 3.

**`request_password_reset(id_number)`**
- An unknown, pending or former member, or one with no contact details, gets no OTP and no error. The page will show the same "If this ID is registered…" message for all of them.
- A locked account gets "Your account is locked…".
- Otherwise it sends a password-reset OTP using the Feature 1 OTP code. The "Request a new OTP" button will call this same function.

**`reset_password(id_number, code, new_password)`**
- The length is checked first, so a too-short password doesn't use up an OTP attempt.
- Then the OTP is checked with the Feature 1 function, so the wrong, expired and third-wrong messages are the same.
- Saving the new password and marking the OTP used happen in one `transaction.atomic()`.
- An unknown ID gets "Incorrect OTP…", so this page can't be used to find out whether an ID exists.

**Two new small helpers:**
- `_get_active_user` finds an activated user by ID.
- `_record_failed_login` adds 1 to the count, locks the account on the 5th, and saves.

## Feature 1 code I changed (all approved in D1 and D2)
- `_check_request_limit` now takes a `purpose` and counts only OTPs of that purpose. `_issue_otp` passes the purpose in. Registration behaviour is the same, because a pending user only ever has registration OTPs.
- In the `_raise_if_registered` docstring, "Active and locked accounts…" now reads "Active accounts, locked or not…".
- The module docstring now covers FR-02 and FR-04.

## Things to know
1. **Two wrong passwords at the same moment can be counted as one.** The count is read, increased and saved as three steps, so two simultaneous requests can both read the same number. An attacker sending requests in parallel could get a few more than 5 guesses before the lock. The fix is one line using Django's `F()` expression, but that's a less familiar idea to explain in the viva. Should I switch to it?
2. **Other logged-in sessions end after a reset.** If the same user is logged in elsewhere, Django ends those sessions automatically when the password changes. I didn't write code for this; Django does it already.
3. **A reset doesn't touch the lock.** Changing the password leaves the wrong-password count and the lock as they were. This is the assumption from the plan.
4. **Delivery failures behave as in Feature 1.** The sender's `ConnectionError` is passed on unchanged, and the new OTP is rolled back.

I haven't committed anything or touched `db.sqlite3` or `docs/`. Shall I start Stage 3 (forms, views, middleware, URLs, templates)?