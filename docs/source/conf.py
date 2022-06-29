***REMOVED*** Configuration file for the Sphinx documentation builder.
***REMOVED***
***REMOVED*** This file only contains a selection of the most common options. For a full
***REMOVED*** list see the documentation:
***REMOVED*** https://www.sphinx-doc.org/en/master/usage/configuration.html

***REMOVED*** -- Path setup --------------------------------------------------------------

***REMOVED*** If extensions (or modules to document with autodoc) are in another directory,
***REMOVED*** add these directories to sys.path here. If the directory is relative to the
***REMOVED*** documentation root, use os.path.abspath to make it absolute, like shown here.
***REMOVED***
***REMOVED*** import os
***REMOVED*** import sys
***REMOVED*** sys.path.insert(0, os.path.abspath('.'))


***REMOVED*** -- Project information -----------------------------------------------------

project = 'unstructured'
copyright = '2022, Unstructured Technologies'
author = 'Unstructured Technologies'

***REMOVED*** The full version, including alpha/beta/rc tags
release = '0.0.1'


***REMOVED*** -- General configuration ---------------------------------------------------

***REMOVED*** Add any Sphinx extension module names here, as strings. They can be
***REMOVED*** extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
***REMOVED*** ones.
extensions = [
    'sphinx_rtd_theme',
    'sphinx.ext.autosectionlabel',

]

***REMOVED*** Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

***REMOVED*** List of patterns, relative to source directory, that match files and
***REMOVED*** directories to ignore when looking for source files.
***REMOVED*** This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


***REMOVED*** -- Options for HTML output -------------------------------------------------

***REMOVED*** The theme to use for HTML and HTML Help pages.  See the documentation for
***REMOVED*** a list of builtin themes.
***REMOVED***
html_theme = 'sphinx_rtd_theme'

***REMOVED*** Add any paths that contain custom static files (such as style sheets) here,
***REMOVED*** relative to this directory. They are copied after the builtin static files,
***REMOVED*** so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
