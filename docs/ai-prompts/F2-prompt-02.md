Approved: D1, D2, D3, D4. Please go ahead with Stage 1 only, then stop.

Additions:
1. Add a row for middleware.py to the dependency table and the layout in CLAUDE.md (may import: constants only). Do not change any other line in CLAUDE.md.
2. role_required should also apply never_cache.
3. In log_in_user, the failed-attempt count and the lock must be saved BEFORE the error is raised and must not be inside a transaction.atomic() that would roll them back. In Stage 4, add a test that proves locked_until is still in the database after the 5th wrong password raised the error.
4. On your two unsure points: do not add a fake hash check and do not change the SRS messages. I will list both as known limitations in the SDS.