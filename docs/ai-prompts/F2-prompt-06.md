Manual browser test (Chrome, Incognito) found a gap in FR-03 criterion 2.
After Log out, pressing the browser Back button shows the old Faculty home
page. Pressing Reload on it, or typing /home/ in the address bar, correctly
goes to the login page. So the server is right (never_cache works); the browser
shows a stored copy (back-forward cache). Django tests cannot catch this because
they do not use a real browser.

Please make the smallest fix so the old page is not shown after Back:
- Suggested approach: a tiny pageshow handler that reloads the page when
  event.persisted is true, included only for logged-in pages. If you prefer
  another approach, say why in one or two sentences before you change anything.
- No new libraries and no big JavaScript. Follow CLAUDE.md.
- Add the tests that are possible (for example: the script is present for
  logged-in pages and absent on the login page; the no-cache headers are still
  there). Say clearly which part cannot be tested without a real browser.
- Run all checks from CLAUDE.md and report the results.
- Do not commit. Do not touch db.sqlite3 or docs/.