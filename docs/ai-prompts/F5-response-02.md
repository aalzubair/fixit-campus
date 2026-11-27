# F5 response 02: what the AI changed and what was checked

## Changes

- `services.py`: `accept_complaint` now refuses anyone who is not maintenance
  staff, and `resolve_complaint` anyone who is not staff or a supervisor, with
  `ServiceError(MSG_NOT_AUTHORIZED)`, before the complaint is read. The views
  already block these roles; the service check keeps the rule in the
  Application layer as well. The `accept_complaint` docstring now says that
  `select_for_update` locks the row only on databases with row locks and that
  SQLite serialises the writes instead.
- `staff_complaints.html`, `staff_complaint_detail.html`: Assigned to and
  Rejected by show `get_full_name|default:username` (CR-03), so names are
  shown instead of ID numbers.
- `tests/staff_base.py`: a real faculty member (not in the test records) and
  `self.complainants` (student, faculty member, administrator) for the access
  tests, because `self.faculty` is turned into a second staff member there.
- `tests/test_services_staff.py`: supervisors and complainant roles cannot
  accept; complainant roles cannot resolve; the complaint does not change.
- `tests/test_views_staff.py`: student, faculty member and administrator get
  403 on accept and resolve; an anonymous user is sent to the login page; the
  list and detail pages show staff and supervisor names, not ID numbers.

## Checks run

- `python manage.py test`: 425 tests OK
- coverage of the `campus` app (without tests and migrations): 100%
- flake8 and black: clean
- pylint: 10.00/10, with the existing notice that `services.py` is over
  1000 lines
