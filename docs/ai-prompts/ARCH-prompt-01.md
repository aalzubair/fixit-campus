# AI Prompt: Architecture design

- Date: 15 Nov 2026
- Tool: Claude
- Purpose: Architecture design for FixIt Campus

## Prompt

You are a senior software architect. Propose the architecture for a Django web application and document it. Do not ask me questions; list assumptions at the end.

## Application
"FixIt Campus": a campus complaint and maintenance system for a university. Users (students, faculty, maintenance staff, supervisors, administrators) register using their university ID verified by a One-Time Password (OTP), log in, submit and track complaints, and receive notifications. Administrators get reports. The system reads a university records system (IUB Records) to verify IDs and roles, and uses an external message delivery service to send OTPs.

## Constraints
- Team of 4 students, new to Django. Stack: Python 3.12, Django 5, SQLite, Django templates + Bootstrap.
- Must be easy to test with Django TestCase and easy to replace the OTP sender and the records system later.
- The course teaches: Layered Architecture (Presentation, Application, Storage layers), MVC, cohesion and coupling (want strong cohesion, loose coupling), and UML package diagrams.

## Deliverables
1. The chosen architectural pattern, with a short justification that uses cohesion, coupling, testability and replaceability, and one honest trade-off.
2. A table mapping each layer to MVC roles, Django parts and files (models.py, views.py, forms.py, services.py, delivery.py, constants.py, templates/).
3. A responsibility table: for each component, what it does and what it must NOT do.
4. The dependency rule (which layer may import which).
5. A package/folder structure for the Django project and one app.
6. A PlantUML package diagram: grayscale only (fill #F1F1F1, border #181818, white background), Times-like font, no shadows, top-to-bottom, all labels visible.
7. A ready-to-paste GitHub Wiki page in Markdown with sections: Chosen pattern, Responsibilities, Why this pattern, Trade-off, Package structure, Dependency rule.

Keep the language simple; students must be able to explain every part in a viva.