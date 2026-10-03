# Resubmission changes

1. **DRF role restrictions:** article creation is journalist-only; updates and deletion require journalist ownership or editor role. Reader writes are denied. Ownership cannot be forged, journalists cannot approve articles, publisher assignment is validated, and drafts are hidden from unauthorized readers.
2. **Journalist newsletters:** new newsletters automatically record their journalist author. Journalists can view newsletters and edit/delete their own. Migration 0004 safely adds nullable ownership for existing records without assigning a guessed author.
3. **Editor newsletters:** editors can view/edit/delete newsletters, including unassigned legacy records, but cannot create them. Forms, buttons, server checks and README now agree.
4. **Reader subscriptions:** a dedicated My Subscriptions page provides Subscribe/Unsubscribe buttons for publishers and independent journalist articles. Navigation, dashboard feed and API filtering are connected.

Related fixes:

- Role-protected dashboards and consistent draft access.
- POST and CSRF for deletion and approval; journalist edits require reapproval.
- No unapproved article titles exposed through newsletter links.
- Public registration cannot create privileged editor or staff accounts; trusted admins provision editors.
- Proper custom-user Admin support with secure password handling.
- Approval emails sent after commit, once per approval transition, deduplicated and privately addressed.
- Removed placeholder external HTTP requests and requests dependency; Twitter/X remains waived.
- Preserved MariaDB as default, moved credentials to environment variables, added an explicit isolated SQLite test/demo option, and pinned validated dependencies.
- Consolidated test discovery into `news_app/tests/`; preserved and updated original tests and added role, ownership, subscription, notification and migration regression tests.

See README.md for setup, existing-database migration instructions and a role matrix. See VALIDATION.md for the completed checks.


## Full-PDF review additions

- Automatic Django Reader/Editor/Journalist groups with the required model permissions, plus a safe existing-account backfill migration (0005).
- Canonical `POST /api/articles/` and `PUT/PATCH/DELETE /api/articles/<id>/` routes; original routes retained as aliases.
- User, Publisher and Newsletter serializers used by private profile, publisher directory and role-protected newsletter CRUD endpoints.
- Role-inapplicable relations kept empty, profile fields returned as null, and explicit independent-content reverse properties.
- New-newsletter emails after commit, with article content, and configurable SMTP environment variables.
- Safe role changes in Django Admin, preservation of unrelated groups/content, and tests for both.
- Full design/normalization/UI plan and assignment requirement checklist.
- Expanded regression suite and 79-column style checks for maintained Python code.
