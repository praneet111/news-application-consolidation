"""Configure Sphinx documentation for the News Application."""

import os
import sys
from pathlib import Path

import django

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load Django without requiring a running MariaDB server.
os.environ["DJANGO_SETTINGS_MODULE"] = "news_project.test_settings"
django.setup()

project = "News Application"
copyright = "2026, Praneet Chiba"
author = "Praneet Chiba"
release = "1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = ["_static"]