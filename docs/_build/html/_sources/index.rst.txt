News Application Documentation
==============================

This Django application allows journalists to write articles and
newsletters, editors to review content, and readers to manage
subscriptions.

User roles
----------

* **Readers:** view approved articles and newsletters, and manage
  subscriptions to publishers and independent journalists.
* **Journalists:** create articles and newsletters, and update or
  delete their own content.
* **Editors:** review and approve articles, update or delete content,
  and manage publishers. Editors cannot create newsletters.

Article workflow
----------------

1. A journalist creates an article.
2. An editor reviews and approves it.
3. Subscribers receive an email notification.
4. If the journalist edits the article, it requires approval again.

Code reference
--------------

The following sections display documentation from the project's
Python modules, classes, and functions.

Views
~~~~~

.. automodule:: news_app.views
   :members:

Models
~~~~~~

.. automodule:: news_app.models
   :members:

Subscription queries
~~~~~~~~~~~~~~~~~~~~

.. automodule:: news_app.selectors
   :members:

