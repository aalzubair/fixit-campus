# F5 prompt 01: Staff actions (FR-11 to FR-14, FR-20)

Tool: Claude (Anthropic), used by Puja Sur on 24 Nov 2026.

## Prompt (summary)

Implement Feature 5 of FixIt Campus on a new branch `feature/F5-staff-actions`,
following `CLAUDE.md` (layered architecture, imports downwards only, all rules
in `services.py`, all texts in `constants.py`, docstrings and type hints,
black/flake8/pylint clean, tests for normal, boundary, invalid and exception
cases).

Requirements, taken from the Wiki "SRS Functional Requirements" and the SDS
(UC-11 to UC-14, UC-20):

- FR-11 Filter complaint list (status, category, location, Safety Hazard;
  Safety Hazard first; "No complaints match your filters.")
- FR-12 Accept complaint ("Complaint already assigned",
  "Only Open complaints can be accepted.")
- FR-13 Mark complaint as Resolved (accept first; "Only the assigned staff
  member or a supervisor can resolve this complaint."; "Only In Progress
  complaints can be marked as Resolved.")
- FR-14 View location history ("No complaint history available.")
- FR-20 Reject complaint with a reason (all seven confirmations)

The Complaint model comes from Jannatun Naim's F3/F4 branch, so build on
`feature/F3-F4`. Notifications (FR-05) are not built yet, so leave a HOOK
comment where they belong, like F3 does. Match the UI screens 20 to 24 in
`docs/ui-design/` and the Wiki page "UI Design F5 F6".
