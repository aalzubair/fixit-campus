Understood. The safety flag will be saved and displayed, with a clearly marked hook for notifications, and the confirmation banner waits until FR-05 exists. We'll start with `constants.py`.

## Step 1: `constants.py`

### Why only some constants now
A test in `test_architecture.py` fails if any constant isn't used in code. So I'm adding only the constants that `models.py` (step 2) will use. Messages, URL names and the location list are added later, in the step that uses them. This keeps the "unused constant" failure short-lived.

### Where to put it
Open `src/campus/constants.py` and paste this block directly **after** the line `OTP_HASH_MAX_LENGTH = 128` and **before** `# --- Business rules (FR-01) ---`:

```python
# --- Complaint statuses (SRS FR-06 to FR-20, SDS complaint state diagram) ---
# Overdue is not a status: it is a mark on an Open complaint (SRS Glossary).
COMPLAINT_OPEN = "open"
COMPLAINT_IN_PROGRESS = "in_progress"
COMPLAINT_RESOLVED = "resolved"
COMPLAINT_REJECTED = "rejected"
COMPLAINT_STATUS_CHOICES = (
    (COMPLAINT_OPEN, "Open"),
    (COMPLAINT_IN_PROGRESS, "In Progress"),
    (COMPLAINT_RESOLVED, "Resolved"),
    (COMPLAINT_REJECTED, "Rejected"),
)
COMPLAINT_STATUS_MAX_LENGTH = 12

# --- Complaint categories (the value stored, the label shown) ---
# Taken from the UI design. The SRS (Assumption 4) says the university supplies
# the final list, so add or rename entries here when it does.
CATEGORY_CHOICES = (
    ("electrical", "Electrical"),
    ("plumbing", "Plumbing"),
    ("furniture", "Furniture"),
    ("air_conditioning", "Air conditioning"),
    ("lift", "Lift"),
    ("wifi", "Wi-Fi"),
)
CATEGORY_MAX_LENGTH = 20

# --- Complaint field sizes ---
# "CMP-2026-01482" is 14 characters; 20 leaves room if the number grows.
COMPLAINT_ID_MAX_LENGTH = 20
# One part of a location: a building, a floor, or a room or area.
LOCATION_PART_MAX_LENGTH = 50
DESCRIPTION_MAX_LENGTH = 1000
# Used for both the reopen reason (FR-10) and the reject reason (FR-20).
REASON_MAX_LENGTH = 500
# Folder inside MEDIA_ROOT where complaint photos are stored (FR-06).
COMPLAINT_PHOTO_DIR = "complaint_photos"
```

### What each part is for
- **Statuses:** the four states from the SDS diagram. Each is stored as a lowercase value with a readable label, the same pattern as `ROLE_CHOICES`. `COMPLAINT_IN_PROGRESS` is 11 characters, so a 12-character column fits it.
- **`CATEGORY_CHOICES`:** these are the six categories shown in the UI mockups. It's a tuple of pairs because `forms.py` may import only `constants.py`, so it can't read categories from the database. Never rename a stored value (like `"wifi"`) after real data exists; change only the label.
- **Lengths and the photo folder:** `models.py` will use them for column sizes and the upload path. This avoids magic numbers, as `CLAUDE.md` requires.

### How it connects
Step 2 (`models.py`) imports `COMPLAINT_STATUS_CHOICES`, `COMPLAINT_OPEN` and the others. Step 3 (`forms.py`) will reuse `CATEGORY_CHOICES` for the dropdown.

### Tests to run
From `src/`:
```
python manage.py test
```
**Expected right now:** every test passes except `ArchitectureTests.test_every_constant_is_used`. It will list the new constants as unused, which is correct because `models.py` doesn't exist yet. `test_constants_are_immutable` should pass because everything is a string, integer or tuple. If you'd rather not see a red test, wait and run once after step 2, where it should return to 224 passing.

Then, from the repository root:
```
flake8 src
black --check src
```
Both should stay clean.

Once the block is pasted, tell me and I'll give you step 2: the `Complaint` and `Follow` models and the `0004` migration.
