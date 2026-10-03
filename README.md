# Django News Application

Developed by **Praneet Chiba** for educational purposes. This resubmission preserves the original Django/Bootstrap project and implements the lecturer's four corrections and the full PDF assignment brief. See `DESIGN_AND_REQUIREMENTS.md` for the requirement-by-requirement checklist.

## Requirements and setup

Tested with Python 3.14.3, Django 6.0.8, Django REST Framework 3.18.1, SimpleJWT 5.5.1 and mysqlclient 2.3.0. Use Python 3.12 or newer. MariaDB remains the default database; the MySQL backend and original database name, username, host and port are retained.

Extract the ZIP and open a terminal inside `news_application` (the folder containing `manage.py`). On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DB_PASSWORD = "YOUR_EXISTING_MARIADB_PASSWORD"
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

If you already have a virtual environment, activate it and install the requirements there instead. If script activation is unavailable, run `.\.venv\Scripts\python.exe` in place of `python`.

Open http://127.0.0.1:8000/. Keep your existing database and accounts. Do not recreate an existing `news_db` database or delete migrations. For a **new installation only**, create the MariaDB database first:

```sql
CREATE DATABASE news_db CHARACTER SET utf8mb4;
```

Set environment variables in the same terminal used to run Django. Supported overrides:

| Variable | Default / purpose |
| --- | --- |
| `DB_NAME` | `news_db` |
| `DB_USER` | `root` |
| `DB_PASSWORD` | Empty; set your existing database password |
| `DB_HOST` | `localhost` |
| `DB_PORT` | `3306` |
| `DJANGO_SECRET_KEY` | Development-only fallback; set a private value for deployment |
| `DJANGO_DEBUG` | `1` for local development; `0` for deployment |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` |
| `NEWS_USE_SQLITE` | Set to `1` only for the optional SQLite demo |
| `EMAIL_BACKEND` | Console backend by default |

The original database password is deliberately not included in the submission. No existing MariaDB data or credentials were changed. Environment variables are read directly; an `.env` file is not loaded automatically. Bootstrap uses a CDN; the forms and content still work without that stylesheet.

### Optional demo without MariaDB

MariaDB is the intended submission database. If it is unavailable, a separate SQLite demo can be selected explicitly:

```powershell
python -m pip install -r requirements-core.txt
$env:NEWS_USE_SQLITE = "1"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

This creates a separate `db.sqlite3`; it does not transfer or replace MariaDB data. Remove that environment variable to return to MariaDB:

```powershell
Remove-Item Env:NEWS_USE_SQLITE
```

If mysqlclient installation fails, use a supported Python version and a compatible wheel, or install the MariaDB client development libraries/build tools required by mysqlclient. Do not replace the database backend or remove its dependency just to hide the error.

## Existing database upgrade

Back up your database before applying migrations. Migrations `0001`–`0003` are unchanged. The included `0004_newsletter_author` adds a nullable author field, preserving existing newsletters and their article relationships. Run `python manage.py migrate`; generating new migrations is unnecessary. Migration `0005_role_groups` creates the Reader, Editor and Journalist groups, grants their required article/newsletter permissions and backfills existing accounts. It removes subscriptions from non-reader accounts to enforce the brief; users and authored content are preserved.

Older newsletters have **unassigned ownership** because the previous schema did not record an author. Editors can still view, edit and delete these newsletters. A trusted administrator can assign the correct journalist in Django Admin once the original author is known. Journalists cannot claim other people's legacy newsletters. Every newsletter newly created through the application automatically records the authenticated journalist as author.

If you already applied the `0004_newsletter_author` migration from the earlier conversation, it has the same name and field definition; Django will recognize it as already applied. Do not fake, delete or reapply migrations unnecessarily.

## Roles and workflow

| Action | Reader | Journalist | Editor |
| --- | --- | --- | --- |
| View approved articles and newsletters | Yes | Yes | Yes |
| View draft articles | No | Own only | All |
| Create articles | No | Yes | No |
| Update/delete articles | No | Own only | All |
| Approve articles | No | No | Yes |
| Create newsletters | No | Yes | No |
| Update/delete newsletters | No | Own only | All |
| Manage own subscriptions | Yes | No | No |
| Manage publishers and assignments | No | No | Yes |

Roles are automatically synchronized with Django groups: Reader has view permissions, Editor has view/change/delete, and Journalist has add/view/change/delete for articles and newsletters. Object-level ownership checks still restrict journalists to their own content. Change an account's role to change its managed group; unrelated groups are preserved.

Editors retain the original application's application-wide editorial scope. Publisher membership controls where journalists can submit articles and newsletters. A journalist may leave the publisher blank to publish independently. Django Admin is a separate, trusted administration interface; ordinary roles do not grant staff access.

Registration creates reader or journalist accounts. To prevent public self-promotion into an editorial role, create editor accounts or set an existing user's role to **Editor** using a superuser at `/admin/`. Editors do not need staff or superuser access to use their dashboard. `createsuperuser` prompts for a news role. Any existing superuser with a blank role can administer accounts but needs a role assigned to use a role dashboard.

1. Register a journalist and a reader; provision an editor in Admin.
2. As editor, create a publisher and assign journalists through **Publishers**.
3. As journalist, create an article under an assigned publisher or leave it independent.
4. As editor, review and approve the article. Approval and deletion use POST forms with CSRF protection.
5. As reader, open **My Subscriptions**, subscribe to publishers and/or independent journalist articles, then select **Read my subscribed news**.
6. As journalist, create a newsletter from approved articles, then edit or delete your own newsletter. Editors can edit/delete but cannot create newsletters.

Journalist article edits return the article to pending review, even if it was previously approved. Article author IDs and timestamps cannot be forged through the API. Editors can approve through the dashboard or the API `approved` field. Editorial edits preserve the existing approval status unless explicitly changed through the API. Newsletter lists hide linked articles that have returned to draft.

## Reader subscriptions and notifications

`/subscriptions/` is a reader-only page linked in the navigation and dashboard. Each publisher and journalist shows an explicit Subscribe or Unsubscribe button and its current subscription state. Requests modify only the logged-in reader, and repeated submissions are harmless.

A publisher subscription follows that publisher's approved articles. A journalist subscription follows their approved **independent** articles (those without a publisher). All journalist accounts are listed because a journalist can publish independent work even when also assigned to a publisher. Subscribe to their publisher separately for publisher-owned articles. The reader dashboard and subscription API use the same filtering rule.

Signals send approval notification emails after the database transaction commits. Recipients are active readers, duplicate email addresses are removed, and messages are sent separately to keep recipient addresses private. Editing an already-approved article does not resend a notification. Resubmitting and approving an article again sends a new notification.

New newsletters are also emailed to their publisher subscribers or independent journalist subscribers after the full article selection has been saved. Updating an existing newsletter does not resend it.

By default, notification emails are printed in the server terminal, as in the original project. To deliver real emails, set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` (`1` for TLS), and `DEFAULT_FROM_EMAIL` in your environment. No external notification service is needed to run or test the project.

**Twitter/X integration was waived by the lecturer.** There is no Twitter/X dependency, credential requirement, or placeholder external HTTP POST.

## REST API

Public endpoints expose only approved articles, except that an authenticated journalist can retrieve their own draft and an editor can retrieve any draft.

| Method | Endpoint | Permission |
| --- | --- | --- |
| GET | `/api/articles/` | Public; approved only |
| GET | `/api/articles/<id>/` | Approved, own draft, or editor |
| POST | `/api/articles/` | Journalist |
| PUT/PATCH | `/api/articles/<id>/` | Author journalist or editor |
| DELETE | `/api/articles/<id>/` | Author journalist or editor |
| GET | `/api/articles/subscribed/` | Reader |
| GET | `/api/me/` | Own safe profile; authenticated |
| GET | `/api/publishers/` | Read-only directory; authenticated |
| GET/POST | `/api/newsletters/` | Authenticated read; journalist create |
| GET/PUT/PATCH/DELETE | `/api/newsletters/<id>/` | Authenticated read; author journalist/editor modify |
| POST | `/api/token/` | Username/password |
| POST | `/api/token/refresh/` | Refresh token |

The original `/api/articles/create/`, `/api/articles/<id>/update/` and `/api/articles/<id>/delete/` remain compatible aliases. The canonical routes above match page 7 of the brief.

Obtain tokens by posting JSON to `/api/token/`:

```json
{"username": "your_username", "password": "your_password"}
```

Send `Authorization: Bearer <access_token>` on protected API requests. Website login uses Django sessions; the API uses JWT. Create an article with:

```json
{"title": "News headline", "content": "Article text", "publisher": null}
```

Do not send an author ID; it is assigned automatically. Journalists cannot set `approved` to true. Read-only author/timestamp fields are ignored by DRF and cannot change ownership. Unauthenticated writes return 401, authenticated forbidden actions return 403, and hidden drafts return 404. Validation failures return 400. Newsletter CRUD is available through both the website and API. Subscription changes use the reader-facing website. The profile API excludes passwords and privilege fields; inapplicable subscription or independent-content fields return JSON `null`. Many-to-many fields stay empty in the database rather than being assigned an invalid Python `None`.

## Checks and automated tests

Run from the directory containing `manage.py`:

```powershell
python manage.py check
python manage.py test --settings=news_project.test_settings
python manage.py makemigrations --check --dry-run --settings=news_project.test_settings
```

`test_settings` uses an isolated in-memory SQLite database, fast test-only password hashing and an in-memory email backend. It never accesses your MariaDB database. Running tests from another working directory can lead to zero tests being discovered; always use the project directory, or pass the explicit `news_app.tests` label.

For MariaDB tests on your machine, set your database password and run `python manage.py test`. Django creates a separate test database (normally `test_news_db`); the database account must have permission to create and drop it. If Django reports an existing test database, investigate it rather than deleting it blindly.

Validation for this ZIP: **70 tests passed on both SQLite and MariaDB**, including migration from existing newsletter data. Django system checks passed and migration drift check reported **No changes detected**. MariaDB validation used a uniquely named temporary test database, which was removed by the test runner; the existing application database was not migrated or modified. See `VALIDATION.md`.

Tests cover role and ownership matrices, API PUT/PATCH/DELETE, JWT authentication, author forgery, publisher assignments, newsletter CRUD and button visibility, legacy ownership, subscriptions and feed filtering, CSRF, POST-only actions, draft privacy, registration restrictions and approval notification behavior.

## Project layout

- `news_app/models.py`, `migrations/`: existing models plus safe newsletter ownership and role-group migrations.
- `news_app/permissions.py`: shared role/ownership rules and DRF permissions.
- `news_app/views.py`, `forms.py`, `templates/`: role dashboards and website flows.
- `news_app/api_views.py`, `serializers.py`, `api_urls.py`: protected JWT article API.
- `news_app/selectors.py`: shared subscription feed query.
- `news_app/signals.py`, `notifications.py`: approval and newsletter emails.
- `news_app/roles.py`: Django role-group setup and membership synchronization.
- `news_app/tests/`: original tests retained/updated, plus regression and migration tests.
- `news_project/settings.py`: MariaDB defaults and explicit configuration overrides.
- `news_project/test_settings.py`: isolated SQLite test configuration.

## Scope

The corrected project has been checked against the supplied ZIP, the full PDF brief and the lecturer's feedback. The lecturer's specific editor/newsletter restriction and X/Twitter waiver override the conflicting older PDF wording. `DESIGN_AND_REQUIREMENTS.md` records the normalized schema, functional/non-functional requirements, UI plan and implementation evidence. Actual grading remains the lecturer's decision.

## Running with Docker

Install and start Docker Desktop. Open a terminal in the project
directory containing `manage.py` and `compose.yaml`.

For first-time setup, copy the example configuration:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace the password and secret-key placeholders.
Use different database and root passwords. Keep this file private.
Do not overwrite an existing configured `.env`.

Build and start the application:

```powershell
docker compose up --build -d
```

Docker starts MariaDB, waits for it to become healthy, applies Django
migrations, and starts the application.

Open http://127.0.0.1:8000/ in your browser.

Create an administrator account:

```powershell
docker compose exec web python manage.py createsuperuser
```

Run automated tests with an isolated SQLite test database:

```powershell
docker compose exec web python manage.py test --settings=news_project.test_settings
```

Stop the containers while preserving database data:

```powershell
docker compose down
```

MariaDB data is stored in a named Docker volume. This configuration
uses Django's development server for local demonstration.

## Building the Sphinx documentation

From the project directory, with the virtual environment created:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-docs.txt
.\.venv\Scripts\python.exe -m sphinx -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in your browser.
Generated HTML is included in Git as required by the assignment.

## Git branches

- `docs`: docstring improvements and Sphinx documentation.
- `container`: Dockerfile and MariaDB container configuration.
- `main`: the merged application, documentation, and Docker setup.
