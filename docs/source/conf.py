# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

# -- Project information -----------------------------------------------------

from unstructured.__version__ import __version__  # noqa: E402

project = "Unstructured"
copyright = "2022-2023, Unstructured Technologies"
author = "Unstructured Technologies"

# The full version, excluding alpha/beta/rc tags
release = __version__.split("-")[0]

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_rtd_theme",
    "sphinx_tabs.tabs",
    "myst_parser",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Adding a custom css file in order to add custom css file and can change the necessary elements.
# custom css and js for kapa.ai integration
html_favicon = "_static/images/unstructured_small.png"
html_js_files = ["js/githubStargazers.js", "js/sidebarScrollPosition.js", "custom.js"]
html_css_files = ["unstructured.css", "custom.css"]

html_theme_options = {
    "sidebar_hide_name": True,
    "light_logo": "images/logo-light-mode.svg",
    "dark_logo": "images/logo-dark-mode.svg",
    "light_css_variables": {
        "color-sidebar-background": "#FFFFFF",
        "color-sidebar-background-border": "#e9eaed",
        "color-sidebar-caption-text": "#484848",
        "color-sidebar-link-text": "#484848",
        "color-sidebar-link-text--top-level": "#484848",
        "color-sidebar-item-background--current": "transparent",
        "color-sidebar-item-background--hover": "transparent",
        "color-sidebar-item-expander-background": "transparent",
        "color-sidebar-item-expander-background--hover": "transparent",
        "color-sidebar-search-text": "#484848",
        "color-sidebar-search-background": "#FFFFFF",
        "color-sidebar-search-background--focus": "#FFFFFF",
        "color-sidebar-search-border": "#b9b9b9",
        "color-sidebar-search-border-focus": "#484848",
        "color-sidebar-current-text": "#ff675f",
        "color-content-foreground": "#484848",
        "color-toc-title": "#212529",
        "color-toc-item-text--hover": "#484848",
        "color-toc-item-text--active": "#484848",
        "color-table-header": "#FDDACA",
        "color-table-bg": "#FFE5D9",
        "color-table-row": "#FEEDE6",
        "color-link": "#ff675f",
        "color-link--hover": "#ff675f",
        "content-padding": "5em",
        "content-padding--small": "2em",
        "color-search-icon": "#484848",
        "color-search-placeholder": "#484848",
        "color-literal": "#FF675F",
        "toc-spacing-vertical": "3em",
        "color-page-info": "#646776",
        "toc-item-spacing-vertical": "1em",
        "color-img-background": "#ffffff",
        "sidebar-tree-space-above": "0",
        "sidebar-caption-space-above": "0",
    },
    "dark_css_variables": {
        "color-sidebar-background": "#131416",
        "color-sidebar-background-border": "#303335",
        "color-sidebar-caption-text": "#FFFFFF",
        "color-sidebar-link-text": "#FFFFFF",
        "color-sidebar-link-text--top-level": "#FFFFFF",
        "color-sidebar-item-background--current": "none",
        "color-sidebar-item-background--hover": "none",
        "color-sidebar-item-expander-background": "transparent",
        "color-sidebar-item-expander-background--hover": "transparent",
        "color-sidebar-search-text": "#FFFFFF",
        "color-sidebar-search-background": "#131416",
        "color-sidebar-search-background--focus": "transparent",
        "color-sidebar-search-border": "#FFFFFF",
        "color-sidebar-search-border-focus": "#FFFFFF",
        "color-sidebar-search-foreground": "#FFFFFF",
        "color-sidebar-current-text": "#FFC2BF",
        "color-content-foreground": "#FFFFFF",
        "color-toc-title": "#FFFFFF",
        "color-toc-item-text--hover": "#FFFFFF",
        "color-toc-item-text--active": "#FFFFFF",
        "color-table-header": "#131416",
        "color-table-bg": "#232427",
        "color-table-row": "#444444",
        "color-link": "#FFC2BF",
        "color-link--hover": "#FFC2BF",
        "color-search-icon": "#FFFFFF",
        "color-search-placeholder": "#FFFFFF",
        "color-literal": "#F8C0A7",
        "color-page-info": "#FFFFFF",
        "color-img-background": "#131416",
        "sidebar-tree-space-above": "0",
        "sidebar-caption-space-above": "0",
    },
}
