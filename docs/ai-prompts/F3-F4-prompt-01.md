# FixIt Project – F3 and F4 Implementation Guide

I am working on a university group project called **FixIt**, a Campus Complaint and Maintenance System developed for Independent University, Bangladesh (IUB).

Repository: [https://github.com/aalzubair/fixit-campus](https://github.com/aalzubair/fixit-campus)

My assigned development work covers **F3 – Submit Complaint** and **F4 – Track, Reopen, and Browse Complaints**.

I need help implementing my assigned features in the existing codebase. Do not build a separate application or change the project's existing architecture.

## 1. First, understand the existing project

Before writing any code:

- Inspect the repository structure and existing source code.
- Read `CLAUDE.md` and follow all project-specific development rules.
- Examine the completed registration and authentication features (F1 and F2).
- Study the existing `models.py`, `forms.py`, `services.py`, `views.py`, `urls.py`, `constants.py`, templates, and tests.
- Understand how the existing code connects these layers.
- Identify existing reusable functions, conventions, naming patterns, and test structures.

Do not assume something is missing without checking the codebase first.

## 2. My assigned features

### F3 – Submit Complaint

Implement the complaint submission workflow, including:

- Allow authenticated users to submit maintenance complaints.
- Collect the complaint category, location (building, floor, room or area), and description.
- Allow users to upload an optional photo.
- Validate required fields and uploaded files.
- Accept only JPG and PNG images up to 5 MB.
- Generate a unique complaint ID.
- Save new complaints with the status `Open`.
- Check for similar existing complaints before creating a new one.
- Allow users to follow an existing similar complaint instead of submitting a duplicate.
- Support the safety hazard flag according to the SRS.

### F4 – Track, Reopen, and Browse Complaints

Implement the following workflows:

**My Complaints**

- Display complaints submitted by the logged-in user.
- Show relevant complaint information and current status.
- Allow users to open and view their own complaint details.

**Following Complaints**

- Allow users to follow existing complaints.
- Display complaints they are following.
- Allow users to stop following a complaint.
- Restrict information about other users' complaints to the fields permitted by the SRS.

**Browse Existing Complaints**

- Allow users to browse existing complaints.
- Implement the required filters, such as category, location, and status, according to the SRS.
- Handle empty results and no-match states.

**Reopen Complaint**

- Allow users to reopen only complaints with `Resolved` status.
- Reject reopening if the complaint was resolved more than seven days ago.
- Require a reason for reopening.
- Display the appropriate validation message when the reason is missing.
- Follow the exact status and assignment rules specified in the SRS/SDS.

## 3. Architecture and coding rules

Follow the existing project architecture:

- `models.py`: database models and relationships.
- `forms.py`: form fields and input validation.
- `services.py`: business logic and application rules.
- `views.py`: handle requests and call services.
- `urls.py`: URL routing.
- `constants.py`: fixed values, statuses, and messages.
- Templates: presentation only.

Important rules:

- Do not put database queries or business logic directly in views.
- Do not put business logic in templates.
- Avoid duplicated code and unnecessary dependencies.
- Follow existing naming conventions and import rules.
- Use type hints and docstrings as required by `CLAUDE.md`.
- Keep code formatted according to the project's Black configuration and 88-character line limit.
- Write tests for new functionality.
- Do not break existing F1 and F2 functionality.

## 4. Testing requirements

Test the important scenarios, including:

- Successful complaint submission.
- Missing required fields.
- Invalid image format.
- Image larger than 5 MB.
- Unique complaint ID generation.
- Similar complaint detection.
- Following and unfollowing complaints.
- Complaint privacy and access restrictions.
- Filtering and empty results.
- Successful reopening.
- Reopening without a reason.
- Reopening after the seven-day limit.
- Reopening a complaint that is not resolved.

Also run the existing test suite to check for regressions.

## 5. How I want you to guide me

I am a CSE student and still learning backend development. I need to understand the code rather than blindly copy it.

Please follow these instructions:

1. Work with the actual repository code, not an imagined version.
2. Explain the existing implementation before suggesting changes.
3. Work one file at a time.
4. Explain why each change is needed.
5. Provide complete, working code when we reach an implementation step.
6. Tell me exactly where each code block belongs.
7. Explain how the files connect to each other.
8. Identify which tests to run and what results to expect.
9. Check for compatibility with the existing code before suggesting new imports, functions, or dependencies.
10. Do not rewrite completed features unless necessary.

If a requirement is unclear or conflicts with the existing implementation, check the SRS, SDS, and repository before deciding. Ask me for clarification when necessary.

## 6. Expected outcome

By the end, I should have:

- A working F3 and F4 implementation. 
- Database models and relationships that follow the existing design.
- Proper form validation and business logic.
- Connected views, URLs, and templates.
- Tests covering the required workflows.
- Code that follows the repository's conventions and does not interfere with other team members' work.

**Start by auditing the repository and identifying exactly what is already implemented, what is missing, and what needs to be changed for F3 and F4. Do not start writing code until this audit is complete.**
