# Validation results

Validated on 2026-10-01 with Python 3.14.3 on Windows.

| Check | Result |
| --- | --- |
| Django system checks, default MariaDB settings | Passed: 0 issues |
| SQLite tests using `news_project.test_settings` | Passed: 70 tests |
| MariaDB tests using a unique temporary test database | Passed: 70 tests |
| Migration drift (`makemigrations --check --dry-run`) | Passed: no changes detected |
| Ruff syntax, imports and unused-code checks (E4/E7/E9/F/I/E501, 79 columns; generated migrations excluded) | Passed |
| Installed dependency consistency (`pip check`) | Passed |

The test suite includes migration from `0003_newsletter_articles` through `0004_newsletter_author` and `0005_role_groups`, with an existing newsletter and article relationship. Both are preserved, with the unknown author left null. Existing users receive the correct role group; unrelated group membership is preserved and invalid non-reader subscriptions are cleared. Original migrations 0001–0003 are unchanged.

The MariaDB run used the supplied local database connection configuration, with a uniquely named `test_news_submission_...` database. Django created and removed that temporary database. The existing application database was not migrated, cleared, or modified. No database dump, passwords, virtual environment, or Python caches are included in the submission ZIP.

Final SQLite test output:

```text
Found 70 test(s).
System check identified no issues (0 silenced).
Ran 70 tests in 1.438s
OK
```

Final MariaDB test output:

```text
Found 70 test(s).
System check identified no issues (0 silenced).
Ran 70 tests in 2.291s
OK
```

The tests exercise rendered templates, button visibility, submitted forms, session login, JWT requests, CSRF enforcement, permissions, notification callbacks and migration data preservation. They do not validate a deployed production mail server or a deployed production web server.


Full assignment review: the supplied nine-page PDF was read, and requirement pages 4–8 were also rendered and visually inspected. The corrected implementation and tests cover the previously missing groups, exact API routes, additional serializers and role-specific relation handling. `DESIGN_AND_REQUIREMENTS.md` maps every functional requirement and records the lecturer's editor-creation clarification and Twitter/X waiver.
