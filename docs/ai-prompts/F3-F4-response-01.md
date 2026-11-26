I've finished the audit and haven't written any code. I read `CLAUDE.md`, all of F1/F2, the SRS, the SDS and the UI screens, and ran the baseline. I cloned the repo into my own sandbox, so you'll apply any code I give you in your copy. As `CLAUDE.md` requires, I won't touch git.

## Baseline
- 224 tests pass, and `manage.py check`, flake8 and black are all clean.
- I couldn't run pylint (not installed here), and I ran on Python 3.12 where the project says 3.14.
- The branch `feature/F3-Submit-Complaint,F4-Track/Reopen/Browse` exists but has zero commits. No other branch contains complaint code, so you define the Complaint model for everyone.

## How F1/F2 connect (the pattern to copy)
Every feature is one chain: **form** (shape only) → **view** (calls exactly one service) → **service** (all rules; raises `ServiceError(message)`) → **model**.

- **`constants.py`:** all messages, URL names, template names and statuses live here. A test fails if a constant is unused or mutable.
- **`views.py`:** `role_required(*roles)` handles login and role (403 uses `MSG_NOT_AUTHORIZED`). Views catch `ServiceError` and call `form.add_error` or `messages.error`. A test fails if `views.py` contains the text `.objects` or `.save(`, even in a docstring.
- **`forms.py`:** may import only `constants`. It can't query the database, which affects the category and location dropdowns.
- **Tests:** `tests/base.py` patches `timezone.now` to a fixed `START_TIME` and swaps in fakes. `test_architecture.py` fails if a new module has no rule.

## What's missing
Nothing complaint-related exists yet. Specifically:
- **Code:** models and a migration, forms, services, views, URLs, templates and tests.
- **Seed data:** the category and location lists.
- **Upload handling:** no `MEDIA_ROOT` setting and no photo-serving route.
- **Navigation:** the UI's top nav (Submit Complaint / Existing Complaints / My Complaints). `base.html` is a narrow 32rem card with no nav.

## Your F3/F4 mapped to the SRS
| Your item | SRS requirement |
|---|---|
| Submit, photo, unique ID | FR-06 |
| Similar complaints, follow | FR-07 |
| Safety hazard | FR-08 |
| My Complaints, Following, details | FR-09 |
| Reopen | FR-10 |
| Browse | FR-21 |

The SRS filters are **building, category, status** (your brief said "location"). FR-07 and FR-08 also depend on features that aren't yours: notifications (FR-05) and staff resolve/reject (FR-13/FR-20).

## Gaps and conflicts, with the default I'd use
1. **Complaint model is a shared contract.** It needs fields for teammates' features: status, `assigned_to`, `resolved_at`, reject reason, safety flag, reopen reason, and a status-changed timestamp. Default: I define it fully now, so nobody needs a conflicting migration later.
2. **Category and location lists.** Forms can't import models. Default: both are immutable tuples in `constants.py` (like `ROLE_CHOICES`), and the complaint stores building, floor and room/area. The UI shows "Block C, Lift 2" with no floor, so floor would be optional.
3. **Description.** The SRS user story mentions it, but the confirmations and the UI make only category and location required. Default: optional.
4. **Complaint ID format.** The SRS says only "unique", while the UI shows `CMP-2026-01482`. Default: `CMP-<year>-<5-digit number>`, generated inside a transaction (NFR-10/11: no partial or duplicate records on retry).
5. **Photo check.** Default: extension, 5 MB size (exactly 5 MB is allowed) and file signature, with no Pillow dependency, since `CLAUDE.md` forbids new dependencies without asking.
6. **Photo privacy.** NFR-05 covers direct URLs, so photos are served through a permission-checked view, not raw `/media/`.
7. **Live "Already reported?" panel.** FR-07 says it updates when category or location changes. Default: a small vanilla-JS fetch to an endpoint that returns the HTML for the panel. The service still does the query.
8. **Reopen rules.** The check order is reason → Resolved-only → 7 days, which follows the SDS. Exactly 7 days is allowed. Reopening sets the status to Open, clears the assignment, stores the reason, and resets the "open since" time (FR-15's 48-hour timer counts from reopening).
9. **Messages not in the SRS.** "Please select a category.", "Please select a location." and the 7-day expiry text come from the UI design. I'll document that in the `constants.py` docstring, as F1 did.
10. **Layout.** I'd add a new wide base template with the nav rather than edit `base.html`, so F1/F2 page tests aren't at risk. I'd also keep everything in the existing files, since a new module would break the architecture test.
11. **Roles.** Only student, faculty and administrator can submit, browse or follow. Staff and supervisors get the existing 403. Following your own complaint is blocked.

## Proposed plan (one file at a time, tests alongside)
1. `constants.py`: statuses, messages, lists, limits, URL and template names.
2. `models.py` plus migration `0004`: `Complaint` and `Follow` (unique per user and complaint).
3. `forms.py`: submit, reopen and browse-filter forms.
4. `services.py`, in three steps: submit with similar-check and follow; my/following/browse/detail; reopen.
5. `views.py`, `urls.py`, templates, then `settings.py` for `MEDIA_ROOT`.

Tests would cover your whole checklist. I'd run `test_architecture` early and the full suite after each step.

## One question
Is anyone on your team building Notifications (FR-05)? Until it exists, FR-08 confirmations 2 to 4 (staff notified, supervisors emailed) can't be built in F3. My default is to save and display the flag with a "Safety Hazard" text label (NFR-09) and leave a clear hook for the alerts. The UI's confirmation banner ("Maintenance staff and supervisors have been notified") would then be false, so I'd hide it for now.

Reply **"approved"** to accept all the defaults, or give me the numbers you want changed. I'll then start with `constants.py`.
