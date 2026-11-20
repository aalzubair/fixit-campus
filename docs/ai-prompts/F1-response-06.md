The pylint warning is gone, and flake8, black and pylint now all pass. I changed only line 89 of `src/fixit_campus/settings.py`, by adding the comment:

```python
"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # pylint: disable=line-too-long
```

| Check                                | Result                              |
| ------------------------------------ | ----------------------------------- |
| `flake8 src`                         | Clean                               |
| `black --check src`                  | Clean (26 files)                    |
| `pylint src/campus src/fixit_campus` | 10.00/10, no findings (was 9.99/10) |

This silences one warning on one line, as you asked. The line is now 124 characters long, but flake8 doesn't flag it because `.flake8` already ignores long lines (`E501`) in `settings.py`. black doesn't shorten the line either, because it never splits text inside quotes.

I didn't commit anything.