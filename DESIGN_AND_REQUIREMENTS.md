# Design and requirement checklist

This is the design record for the corrected resubmission, checked against **06-052 Capstone Project – News Application**, pages 2–8, and the lecturer's later feedback. It documents the implemented design; it does not claim to be an original pre-implementation planning document.

## Conflicts and scope decisions

- Page 4 loosely allows editors to create newsletters, but page 5 grants editors view/change/delete only. The lecturer explicitly confirmed journalist-only creation. That stricter rule is applied to groups, forms, templates and APIs.
- The PDF requires Twitter/X posting. The lecturer explicitly waived it. There is no X credential, dependency or network call.
- Many-to-many fields and reverse relations cannot be assigned Python `None` in Django. For inapplicable roles, subscription join tables stay empty and the user API returns JSON `null`; journalist-only reverse properties return Python `None` for other roles. Existing authored content is preserved on role changes rather than deleted.
- Page 7 explicitly requires a list of all approved articles. Its subscribed endpoint is the restricted feed referred to by the page 8 subscription tests. The general approved list remains available to all; the subscribed feed returns only the authenticated reader's subscriptions.
- Publisher membership governs journalist submission choices. Editors retain the existing project's application-wide editorial scope; the brief does not require editor ownership of a publisher to approve its articles.

## Functional requirements and evidence

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Django project and application | `news_project`, `news_app` | System checks and URL tests |
| Article title, content, author, timestamps, approval, optional publisher | `Article` model | Original model tests and API tests |
| Independent/publisher content distinction | Required journalist author, optional publisher | Publisher validation and independent reverse-relation tests |
| Publishers with multiple editors/journalists | Two many-to-many membership relations | Publisher form and directory API tests |
| Newsletter fields and curated article collection | `Newsletter`, journalist author, many-to-many articles | Web/API CRUD and migration tests |
| Reader, Editor, Journalist roles with matching groups | `roles.py`, user-save signal, migration 0005 | Exact group-permission and role-change tests |
| Reader view-only article/newsletter permissions | Reader group has view permissions only; server denies writes | Web and API forbidden-request tests |
| Editor view/change/delete, approval | Editor group and object permissions | Approval/update/delete tests; creation denied |
| Journalist content creation and own-content CRUD | Authenticated ownership assignment and object checks | Author-forgery, own/other-content tests |
| Reader publisher/journalist subscriptions | Two many-to-many relations, My Subscriptions page | Subscribe/unsubscribe, CSRF and feed tests |
| Journalist independent article/newsletter relations | Filtered reverse properties on `CustomUser` | Role-specific profile and reverse-relation tests |
| Inapplicable role fields empty/None | Relation guard, role-change cleanup, API null values | Direct/reverse relation and serializer tests |
| Editor review/approval UI | Role dashboard and POST approval form | Dashboard, CSRF and approval tests |
| Email approved articles to subscribers | Approval-transition signals, commit callbacks | Mocked send, in-memory email, rollback tests |
| Subscribers can receive newsletters | Email after a new newsletter and its articles are saved | Mocked website/API delivery tests |
| Exact REST article endpoints | List/create and retrieve/update/delete routes | Canonical route tests, including denied requests |
| Token authentication | JWT token and refresh endpoints | Real JWT request and refresh test |
| Article, User, Newsletter, Publisher serializers | `serializers.py`; used by actual endpoints | Serializer output/privacy and CRUD tests |
| Automated Python tests, including failures | `news_app/tests/` | Full suite on SQLite and MariaDB |
| MariaDB database | MySQL backend and mysqlclient dependency | Full suite in a separate MariaDB test database |
| X/Twitter | Waived by lecturer | No dependency or external call |

## Non-functional requirements

- **Correctness:** migrations, model/form validation, ownership checks and a regression test suite cover both accepted and rejected requests.
- **Security:** JWT authentication for API writes, sessions and CSRF for website actions, POST-only destructive actions, automatic author assignment, no public privilege escalation, no credential in source or archive. Group model permissions complement role and object-level checks; broad model permissions never replace ownership checks.
- **Readability:** descriptive functions, docstrings, shared permission/query helpers, consistent formatting and 79-column checks for maintained Python code. Historical generated migrations remain unchanged.
- **Efficiency:** related objects are selected/prefetched for article, publisher and newsletter listings. Feeds use database filters and distinct results; recipients are deduplicated.
- **Defensive behavior:** invalid roles/actions/targets/publishers/articles are rejected; duplicate subscription submissions are harmless; draft content stays hidden; transaction rollback prevents email callbacks.
- **Operational setup:** pinned dependencies, environment-based MariaDB configuration, a console email default and explicit SMTP settings, separate test settings, safe upgrade instructions.
- **Usability:** navigation tailored to roles, clearly labeled forms and buttons, empty-state messages, visible subscription state, and links from the reader dashboard to subscription management.

## Normalized database design

The schema keeps entities separate and uses foreign keys and junction tables rather than repeated/comma-separated data.

| Entity/relation | Key and dependencies |
| --- | --- |
| CustomUser | User ID determines username, authentication fields and role |
| Publisher | Publisher ID determines its name |
| Article | Article ID determines title/content, author ID, publisher ID, approval and timestamps |
| Newsletter | Newsletter ID determines title/description, author ID, publisher ID and creation time |
| Publisher editors | Unique publisher/user pair |
| Publisher journalists | Unique publisher/user pair |
| Reader publisher subscriptions | Unique reader/publisher pair |
| Reader journalist subscriptions | Unique reader/journalist pair; directional, not symmetric |
| Newsletter articles | Unique newsletter/article pair |
| Django group membership/permissions | Built-in group, permission, content-type and junction tables |

These relations meet the practical goals of third normal form: scalar entity attributes, no repeated groups, and entity descriptions stored only with the entity they describe. Author and publisher names are not copied onto every article. Independent article/newsletter collections are reverse queries rather than duplicate ownership tables.

`role` is the source of truth for the three managed groups. Membership is synchronized on user save, Admin save and migration; unrelated groups are preserved. This deliberately maintained role/group mapping is required by the brief.

Relationships:

```text
CustomUser (journalist) 1 --- many Article
CustomUser (journalist) 1 --- many Newsletter
Publisher              1 --- many Article/Newsletter (optional publisher)
Publisher           many --- many CustomUser (editor assignments)
Publisher           many --- many CustomUser (journalist assignments)
Newsletter          many --- many Article
CustomUser (reader) many --- many Publisher (subscriptions)
CustomUser (reader) many --- many CustomUser (journalist subscriptions)
```

Newsletter author is temporarily nullable for legacy records only. New application-created newsletters always have an author. Migration 0004 does not invent legacy ownership; a trusted administrator can assign a known journalist later. Migration 0005 backfills role groups without deleting users, articles or newsletters. It removes non-reader subscriptions because those fields are inapplicable to those roles.

## UI/UX plan and implemented pages

```text
Shared navigation
  Home | Dashboard | Newsletters | My Subscriptions (reader)
       | Publishers (editor) | Logout

Reader dashboard
  All approved news | My subscribed news | Manage Subscriptions
  Article cards -> full article

My Subscriptions
  Publisher cards: name, current state, Subscribe/Unsubscribe
  Journalist cards: name, current state, Subscribe/Unsubscribe
  Read my subscribed news

Journalist dashboard
  Create Article
  Own article cards: pending/approved, View, Edit, Delete
  Newsletters: Create; View all; Edit/Delete owned newsletters

Editor dashboard
  Article author, review state, View, Approve, Edit, Delete
  Manage publishers and editorial assignments
  Newsletters: View, Edit, Delete (no Create)
```

Form errors are displayed with Django forms. All destructive buttons submit protected forms. Role visibility matches backend authorization, so hidden buttons are not the only protection.

## Publication and delivery flow

1. A journalist submits an article; the server sets author and pending approval.
2. An editor reviews and approves it through the UI or API.
3. The signal checks the previous approval state and schedules emails after commit.
4. Publisher articles notify that publisher's readers; independent articles notify the journalist's readers.
5. A journalist's later edit returns the article to draft until reapproved.
6. A journalist creates a newsletter from approved articles. After the newsletter and article relationships are saved, its subscribers receive the assembled newsletter by email.

New newsletter emails are sent once per creation, not every editorial correction. The default console email backend makes the delivery observable without SMTP credentials. Configure the SMTP environment variables described in the README for real delivery.

## Review evidence

See `VALIDATION.md` for executed checks and `CHANGES.md` for the correction summary. The archive contains the project, migrations, requirements and test code. Submission/upload to the learning platform remains the student's action; nothing is uploaded automatically.
