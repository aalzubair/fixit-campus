# FixIt Campus

**FixIt Campus** (the Campus Complaint & Maintenance System) is a web application where students, faculty members and administrators report campus facility problems (for example a broken fan or a leaking tap), maintenance staff handle them, and supervisors monitor delays. Every complaint is tracked from report to resolution.

CSC545 / CSE451 Software Engineering, Section 2, Autumn 2026, Independent University, Bangladesh (IUB).
Course teacher: Dr. Md Musfique Anwar.

**Team:** Abdullah Al Zubair, Jannatun Naim, Puja Sur, Asiful Islam.

**Version:** v1.0.0 (the version submitted on 28 November 2026).

## Features

| ID | Feature | Requirements | Owner | Status in v1.0.0 |
|---|---|---|---|---|
| F1 | Register with OTP | FR-01 | Abdullah | Done |
| F2 | Log in, log out, reset password | FR-02 to FR-04 | Abdullah | Done |
| F3 | Submit a complaint | FR-06 to FR-08 | Jannatun | Done |
| F4 | Track, reopen, browse complaints | FR-09, FR-10, FR-21 | Jannatun | Done |
| F5 | Staff actions (filter, accept, resolve, location history, reject) | FR-11 to FR-14, FR-20 | Puja | Done |
| F6 | Supervisor (overdue, monitor, assign) | FR-15 to FR-17 | Puja | Not in v1.0.0 (UI designed) |
| F7 | Reports | FR-18, FR-19 | Asiful | Not in v1.0.0 |
| F8 | Notifications | FR-05 | Asiful | Not in v1.0.0 |

What is missing or only partly done is listed on the Wiki page [Risks and Limitations](https://github.com/aalzubair/fixit-campus/wiki/Risks-and-Limitations).

## Technology

Python, Django 6.0, SQLite, Django templates with Bootstrap 5. Layered architecture (Presentation, Application, Storage) with MVC inside the Presentation layer.

## Setup and run

You need Python 3.14 (tested; 3.13 also passes the tests) and Git.

```
git clone https://github.com/aalzubair/fixit-campus.git
cd fixit-campus
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd src
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/login/ (the address `/` alone shows "Not Found"; use `/login/` or `/register/`).

All Django commands are run from the `src/` folder.

## Try it

Registration is limited to people listed in the university records. In this version the records come from the file `src/campus/data/iub_records.json`, so you can register with one of these ID numbers:

**Development only:** the demo ID numbers, the OTP printed in the terminal and the JSON records file are for development and testing. A real deployment needs a real university records system and email or SMS delivery (see [Risks and Limitations](https://github.com/aalzubair/fixit-campus/wiki/Risks-and-Limitations)).

| ID number | Role |
|---|---|
| 2310001 | Student |
| 2310002 | Faculty member |
| 2310003 | Maintenance staff |
| 2310004 | Supervisor |
| 2310005 | Administrator |

1. Open `/register/`, enter an ID number from the table and choose a password (at least 8 characters).
2. The one-time password (OTP) is **printed in the terminal** where `runserver` is running, because no email or SMS is sent in this version.
3. Enter the OTP, then log in at `/login/`.

## Tests and quality checks

Run these from the repository root unless noted.

```
cd src && python manage.py test                 # all automated tests
cd src && coverage run --branch --source=campus --omit="*/migrations/*,*/tests/*" manage.py test
cd src && coverage report -m                    # coverage
flake8 src
black --check src
pylint src/campus
interrogate -v --exclude src/campus/migrations src/campus   # docstring coverage
```

The tests use fake OTP and university-records classes, so no real email, SMS or university system is needed.

## Source code documentation

The documentation is generated from the docstrings with Sphinx:

```
cd docs/sphinx
make html          # Windows: make.bat html
```

A built copy is kept in `docs/sphinx-html/`: open `docs/sphinx-html/index.html` in a browser, no build needed. A new build goes to `docs/sphinx/build/html/`, which git ignores.

## Folder structure

```
src/
  manage.py
  fixit_campus/     Django project (settings and root URLs)
  campus/           the one Django app: views, forms, services, models, constants, tests
docs/               SRS, SDS, diagrams, UI design, AI prompts, meeting notes, Sphinx
CLAUDE.md           rules for AI coding assistants (architecture, style)
```

The allowed imports between layers are written in `CLAUDE.md` and checked automatically by `test_architecture.py`.

## Project documents

All project documents are on the Wiki: https://github.com/aalzubair/fixit-campus/wiki

- Software Requirements Specification (SRS) and Software Design Specification (SDS)
- Architecture, Coding Standards, Source Code Documentation
- UI design and Nielsen's usability heuristics
- Code Review, Unit Testing, Git Usage
- Risks and Limitations, Change Log, AI Usage Log, Team Contributions

## Working rules

- The `main` branch is protected: every change goes through a pull request with at least one approval and uses a merge commit.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), for example `feat(F5): staff actions`.
- AI assistants were used for parts of the code, tests and documents. Every prompt and response is stored in `docs/ai-prompts/`.