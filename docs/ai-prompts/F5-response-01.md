# F5 response 01: what the AI produced and what was checked

## Files

- `constants.py`: STAFF_ROLES, REJECTABLE_STATUSES, the F5 URL names,
  templates and SRS messages.
- `forms.py`: `StaffFilterForm` (all statuses + Safety Hazard box) and
  `RejectForm` (reuses the required reason of `ReopenForm`).
- `services.py`: `list_staff_complaints`, `get_staff_complaint_detail`
  (location history), `accept_complaint`, `resolve_complaint`,
  `reject_complaint`; the row is locked with `select_for_update` so two staff
  members cannot accept the same complaint at once.
- `views.py`, `urls.py`: five staff pages under `staff/complaints/`.
- Templates: `staff_base.html`, `staff_complaints.html`,
  `staff_complaint_detail.html`, `complaint_reject.html`; a `nav_links` block
  in `app_base.html`; a Complaints button on the staff home page.
- Tests: `staff_base.py`, `test_services_staff.py` (29 tests),
  `test_views_staff.py` (20 tests).

## Checks run

- `python manage.py test`: 401 tests OK (352 existing + 49 new)
- coverage of services, views and forms: 100%
- flake8 and black: clean (with the repository's `.flake8` and `pyproject.toml`)
- pylint: 10.00/10, one notice: `services.py` has 1175 lines (limit 1000)
- `python manage.py check`: no issues

## Assumptions and limits

- FR-13 Confirmation 3 gives no exact text; the message is
  "Please accept this complaint first."
- Location history shows complaints at the same place submitted before the
  opened one, newest first.
- Only maintenance staff can accept (UC-12); supervisors assign in F6.
- Notifications to the complainant, followers and assigned staff (FR-13 and
  FR-20) are HOOK comments until FR-05 exists.
- The photo is not shown on the staff page yet, because the photo address is
  limited to the complaint owner in F4.
