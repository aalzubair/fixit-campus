Stage 1 approved. Start Stage 2.

Reminder from my last message: use name.strip()[:MEMBER_NAME_MAX_LENGTH].rstrip() and the extra trailing-space test, and count the public methods of RecordsCheckAtLoginTests first (new class if it would go over 20; no silencing).

At the end, for interrogate run the documented command instead of "interrogate src":
interrogate -v --exclude src/campus/migrations src/campus