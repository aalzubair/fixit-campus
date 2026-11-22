I've added the fix, but I haven't been able to confirm in a browser that it closes the gap; please repeat your manual Back-button test. All 224 tests pass (5 new) and every CLAUDE.md check is clean.

## The fix
**`base.html`**: a 5-line `pageshow` script, rendered only inside `{% if user.is_authenticated %}`, so it appears only on pages built for a logged-in user. When the browser shows a page from its back-forward cache, `event.persisted` is true and the script reloads the page. The reload is a real request, so the server sees you're logged out and redirects to the login page. That's the same thing that already happens when you press Reload yourself.

The `never_cache` headers stay as they are; the script is an extra defence, not a replacement. Nothing else changed: no new library, no new file, no Python code.

## New tests
These are in `test_views_auth.py`, class `BackForwardCacheTests`:
- A logged-in page (home) contains the reload script.
- The 403 page also contains it, since it's a logged-in page too.
- The login page for a visitor has no script.
- The login page shown right after Log out has no script.
- Home still sends `no-cache`, `no-store`, `must-revalidate` and `private`.

**What the tests can't cover:** whether a real browser keeps the page in its back-forward cache and runs the script on Back. Django's test client doesn't run JavaScript or keep a history, so this stays a manual test:
1. Log in, open Home, then Log out.
2. Press Back.
3. Expected: a short flash, then the login page. You should not see the old Home page.

If you want it repeatable later, a browser tool like Selenium or Playwright could automate it, but that's a new dependency, so I haven't added one.

## Check results
| Check                                | Result                                                                                                             |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `flake8 src`                         | no issues                                                                                                          |
| `black --check src`                  | 31 files unchanged. Black first reformatted the new test (one `assertContains` line); the check passes after that. |
| `pylint src/campus src/fixit_campus` | 10.00/10                                                                                                           |
| `python manage.py check`             | no issues                                                                                                          |
| `python manage.py test`              | 224 tests, OK                                                                                                      |

## Assumptions
- **A brief flash of the old page is acceptable.** The browser draws the restored page before the script runs, so the old Home page may show for a split second. To avoid it, the script would have to hide the page first, which means more JavaScript. Tell me if that matters.
- **Users with JavaScript turned off aren't covered.** For them, Back can still show the stored copy. Reload or opening `/home/` still goes to login, so the server side stays correct. This could go into the SDS limitations.

I didn't commit anything, and I didn't touch `db.sqlite3` or `docs/`.