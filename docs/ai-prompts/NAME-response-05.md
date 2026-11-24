Here's the plan. I haven't written any code yet.

## What I found

- `records.py:28`: `UniversityMember` is a frozen dataclass with no checks. `JsonRecordsClient.find_member` only fails (`KeyError`) when the `"name"` key is missing. An empty or blank name gets through.
- `services.py:297`: `_copy_records_details` sets `user.first_name = member.name[:MEMBER_NAME_MAX_LENGTH]`. It never strips the name and never clears `last_name`.
- `FakeRecordsClient.change_member` uses `dataclasses.replace`, which runs `__post_init__` again. So the new check also covers members the tests change.

## Stage 1: `records.py`, `constants.py`, `tests/test_records.py`

1. **`constants.py`**: add one constant in the "University records" section:
   `RECORDS_ERROR_EMPTY_NAME = "University record {id_number} has an empty name."`
   It goes into the exception message. It is an internal error, not an SRS user message, and it doesn't include the name itself. `records.py` will use it, so it won't be an unused constant.
2. **`records.py`**:
   - Add `__post_init__(self) -> None` to `UniversityMember`. It raises `ValueError(RECORDS_ERROR_EMPTY_NAME.format(...))` when `not self.name.strip()`. It only checks; it doesn't change the value, because the dataclass is frozen and keeping it a pure check is simpler. It gets a full PEP 257 docstring with a `Raises:` section.
   - Add a `Raises: ValueError` section to the `UniversityMember` class docstring.
   - `RecordsClient.find_member` (the interface): add `Raises: ValueError`, so every implementation documents it.
   - `JsonRecordsClient.find_member`: keep `KeyError` for a missing key and add `ValueError` for an empty or blank name.
   - Why `ValueError`: a missing key already gives `KeyError`. A key that is there but has a bad value is the textbook case for `ValueError`. Both are "fail loudly" errors that the services don't catch.
3. **Tests** (`test_records.py`):
   - `test_empty_name_raises_value_error`: build `UniversityMember` directly.
   - `test_whitespace_only_name_raises_value_error`: use `"  \t\n "`.
   - `test_name_with_surrounding_spaces_is_accepted`: the boundary case, a valid name with padding.
   - `test_record_with_empty_name_raises_value_error`: through `JsonRecordsClient` with a temp file, so the JSON path is covered too.

## Stage 2: `services.py`, `tests/test_services_login.py`

1. `_copy_records_details` changes to:
   ```python
   user.first_name = member.name.strip()[:MEMBER_NAME_MAX_LENGTH]
   user.last_name = ""
   user.role = member.role
   ```
   I'll also update its docstring, which currently says `last_name` "stays empty". It will say the helper clears `last_name`, because an account made in the admin may have one.
2. **Tests** (in `RecordsCheckAtLoginTests`):
   - `test_login_clears_existing_last_name`: give the stored user `last_name="Old"`, log in, then check that `get_full_name()` equals the records name and `last_name == ""`. I'll check both the returned user and the reloaded one.
   - `test_name_is_stripped_before_storing`: records name `"  New Name  "` is stored as `"New Name"`.
   - `test_padded_long_name_is_stripped_then_cut`: leading spaces plus a name of exactly `MEMBER_NAME_MAX_LENGTH` characters. The stored name is the full name with nothing lost. This proves the strip happens before the cut.

## Checks at the end (after Stage 2, and the relevant ones after Stage 1)

From `src/`:
- `python manage.py check`
- `python manage.py test`
- The documented coverage command: `coverage run --branch --omit="*/migrations/*,manage.py" manage.py test && coverage report`

From the root:
- `flake8 src`
- `black --check src`
- `pylint src/campus src/fixit_campus`
- `interrogate src`

I'll report the real numbers. If `interrogate` isn't installed, I'll tell you rather than install it.

## One decision for you

**Service docstrings.** The service functions that call `find_member` (`register_user`, `log_in_user` and the others) don't list the existing `KeyError` today. Records-data errors are treated as "crash loudly" and left out of the service docs. I plan to follow that and update only the `records.py` docstrings plus `_copy_records_details`. If you want `ValueError` listed on every service function too, tell me and I'll add it in Stage 2.

## Assumptions

1. `ValueError` is the right exception type. A missing key stays `KeyError`.
2. The error message is developer-facing, so it isn't checked against the SRS. It includes the ID number but not the name.
3. I won't change `fakes.py` or the demo JSON file. The demo file already has a test that every name is non-empty.

Approve this (and answer the docstring question) and I'll start Stage 1.