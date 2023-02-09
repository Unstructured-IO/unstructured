***REMOVED*** Configuration file for the Sphinx documentation builder.
***REMOVED***
***REMOVED*** This file only contains a selection of the most common options. For a full
***REMOVED*** list see the documentation:
***REMOVED*** https://www.sphinx-doc.org/en/master/usage/configuration.html

***REMOVED*** -- Path setup --------------------------------------------------------------

import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

***REMOVED*** -- Project information -----------------------------------------------------

from unstructured.__version__ import __version__

project = "Unstructured"
copyright = "2022-2023, Unstructured Technologies"
author = "Unstructured Technologies"

***REMOVED*** The full version, excluding alpha/beta/rc tags
release = __version__.split("-")[0]

***REMOVED*** -- General configuration ---------------------------------------------------

***REMOVED*** Add any Sphinx extension module names here, as strings. They can be
***REMOVED*** extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
***REMOVED*** ones.
extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.autosectionlabel",
]

***REMOVED*** Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

***REMOVED*** List of patterns, relative to source directory, that match files and
***REMOVED*** directories to ignore when looking for source files.
***REMOVED*** This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


***REMOVED*** -- Options for HTML output -------------------------------------------------

***REMOVED*** The theme to use for HTML and HTML Help pages.  See the documentation for
***REMOVED*** a list of builtin themes.
***REMOVED***
html_theme = "furo"

***REMOVED*** Add any paths that contain custom static files (such as style sheets) here,
***REMOVED*** relative to this directory. They are copied after the builtin static files,
***REMOVED*** so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

***REMOVED*** Adding a custom css file in order to add custom css file and can change the necessary elements.
html_favicon = "_static/images/unstructured_small.png"
html_css_files = ["unstructured.css"]
html_js_files = ["js/githubStargazers.js", "js/sidebarScrollPosition.js"]

html_theme_options = {
    "sidebar_hide_name": True,
    "light_logo": "images/logo-light-mode.svg",
    "dark_logo": "images/logo-dark-mode.svg",
    "light_css_variables": {
        "color-sidebar-background": "***REMOVED***FFFFFF",
        "color-sidebar-background-border": "***REMOVED***e9eaed",
        "color-sidebar-caption-text": "***REMOVED***484848",
        "color-sidebar-link-text": "***REMOVED***484848",
        "color-sidebar-link-text--top-level": "***REMOVED***484848",
        "color-sidebar-item-background--current": "transparent",
        "color-sidebar-item-background--hover": "transparent",
        "color-sidebar-item-expander-background": "transparent",
        "color-sidebar-item-expander-background--hover": "transparent",
        "color-sidebar-search-text": "***REMOVED***484848",
        "color-sidebar-search-background": "***REMOVED***FFFFFF",
        "color-sidebar-search-background--focus": "***REMOVED***FFFFFF",
        "color-sidebar-search-border": "***REMOVED***b9b9b9",
        "color-sidebar-search-border-focus": "***REMOVED***484848",
        "color-sidebar-current-text": "***REMOVED***ff675f",
        "color-content-foreground": "***REMOVED***484848",
        "color-toc-title": "***REMOVED***212529",
        "color-toc-item-text--hover": "***REMOVED***484848",
        "color-toc-item-text--active": "***REMOVED***484848",
        "color-table-header": "***REMOVED***FDDACA",
        "color-table-bg": "***REMOVED***FFE5D9",
        "color-table-row": "***REMOVED***FEEDE6",
        "color-link": "***REMOVED***ff675f",
        "color-link--hover": "***REMOVED***ff675f",
        "content-padding": "5em",
        "content-padding--small": "2em",
        "color-search-icon": "***REMOVED***484848",
        "color-search-placeholder": "***REMOVED***484848",
        "color-literal": "***REMOVED***FF675F",
        "toc-spacing-vertical": "3em",
        "color-page-info": "***REMOVED***646776",
        "toc-item-spacing-vertical": "1em",
        "color-img-background": "***REMOVED***ffffff",
        "sidebar-tree-space-above": "0",
        "sidebar-caption-space-above": "0",
    },
    "dark_css_variables": {
        "color-sidebar-background": "***REMOVED***131416",
        "color-sidebar-background-border": "***REMOVED***303335",
        "color-sidebar-caption-text": "***REMOVED***FFFFFF",
        "color-sidebar-link-text": "***REMOVED***FFFFFF",
        "color-sidebar-link-text--top-level": "***REMOVED***FFFFFF",
        "color-sidebar-item-background--current": "none",
        "color-sidebar-item-background--hover": "none",
        "color-sidebar-item-expander-background": "transparent",
        "color-sidebar-item-expander-background--hover": "transparent",
        "color-sidebar-search-text": "***REMOVED***FFFFFF",
        "color-sidebar-search-background": "***REMOVED***131416",
        "color-sidebar-search-background--focus": "transparent",
        "color-sidebar-search-border": "***REMOVED***FFFFFF",
        "color-sidebar-search-border-focus": "***REMOVED***FFFFFF",
        "color-sidebar-search-foreground": "***REMOVED***FFFFFF",
        "color-sidebar-current-text": "***REMOVED***FFC2BF",
        "color-content-foreground": "***REMOVED***FFFFFF",
        "color-toc-title": "***REMOVED***FFFFFF",
        "color-toc-item-text--hover": "***REMOVED***FFFFFF",
        "color-toc-item-text--active": "***REMOVED***FFFFFF",
        "color-table-header": "***REMOVED***131416",
        "color-table-bg": "***REMOVED***232427",
        "color-table-row": "***REMOVED***444444",
        "color-link": "***REMOVED***FFC2BF",
        "color-link--hover": "***REMOVED***FFC2BF",
        "color-search-icon": "***REMOVED***FFFFFF",
        "color-search-placeholder": "***REMOVED***FFFFFF",
        "color-literal": "***REMOVED***F8C0A7",
        "color-page-info": "***REMOVED***FFFFFF",
        "color-img-background": "***REMOVED***757575",
        "sidebar-tree-space-above": "0",
        "sidebar-caption-space-above": "0",
    },
}
