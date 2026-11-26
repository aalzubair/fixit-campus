F3 and F4 are finished, built on your repo and tested. There are two files: `fixit_f3_f4.patch` and `fixit_f3_f4_files.zip` (the same 25 files, laid out by path).

All checks pass. I applied the patch to a fresh clone of your repo and the full suite ran there too.

| Check | Result |
|---|---|
| Tests | 352 pass (224 existing plus 128 new) |
| Coverage of the app modules | 100% |
| pylint | 10.00/10 |
| black, flake8, `makemigrations --check` | clean |

## How to apply it
From the repo root, on your feature branch:
```
git apply fixit_f3_f4.patch
cd src
python manage.py migrate
python manage.py test
```
I didn't touch git, as `CLAUDE.md` requires, so reviewing, committing and pushing are yours.

## What was built, by layer
- **`constants.py`:** statuses, categories, the location list, photo and 7-day limits, URL and template names, and messages. The SRS messages are word for word. Some wording comes from the UI design or is my own, and the file says which.
- **`models.py` plus migration `0004`:** `Complaint` (including fields teammates will need, such as assignment and rejection) and `Follow`.
- **`forms.py`:** the complaint, reopen and browse-filter forms. The photo check covers extension, size and file signature, so a text file renamed to `.jpg` is rejected.
- **`services.py`:** all the rules.
  - **ID:** `CMP-2026-00001` format, restarting each year.
  - **Duplicates:** the similar-complaint search and follow.
  - **Privacy:** other users' complaints come back as a `ComplaintSummary` that has no description, photo or reporter field, so no page can show them by mistake.
  - **Reopen:** goes back to Open, clears the assignment and stores the reason. Exactly 7 days is allowed.
- **`views.py`, `urls.py`, templates:** thin views, 10 routes, and a new wide layout with the nav from the UI design. `base.html` is untouched, so F1/F2 pages are unaffected.

## Things you should know
- **Safety Hazard:** the flag is saved and shown as text, and there's a clearly marked `HOOK (FR-08, needs FR-05)` comment in `submit_complaint`. As agreed, the confirmation page doesn't claim anyone was notified, and a test locks that in.
- **Not browser-tested:** the live "Already reported?" panel is a small script. The server side it calls is tested, but I couldn't click through it in a real browser, so please try it once.
- **Location dropdowns are not cascading.** The form checks that building, floor and room form a valid combination, but choosing a building doesn't yet narrow the other lists.
- **Placeholder lists:** `LOCATIONS` and `CATEGORY_CHOICES` come from the UI mockups. Replace them with the university's real lists (SRS Assumption 4).
- **Photos:** they're only served to the owner through a permission-checked view. Staff and supervisors will need that view extended in their features.
- **Complaint ID in addresses:** a followed complaint's ID is never shown as text, but it appears in the Follow and Stop following form addresses, because the button needs it.
- **Team coordination:** you're the first to define `Complaint`, so tell teammates the model and migration `0004` exist before they create their own migrations.
- **Notifications:** `Follow` stores who follows what, but sending the Resolved/Rejected notification belongs to FR-05, FR-13 and FR-20.

Want me to walk through any layer line by line, so you can explain it to your team?
