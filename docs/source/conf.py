# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
# for conversion from markdown to html
import recommonmark.parser
sys.path.insert(0, os.path.abspath('../../src/optac/'))

project = 'OPTac'
copyright = '2023, David Palecek'
author = 'David Palecek'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'recommonmark',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# add a source file parser for markdown
source_parsers = {
    '.md': 'recommonmark.parser.CommonMarkParser',
}

autodoc_default_options = {
    "members": True, 
    "undoc-members": True,
    "private-members": True}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# add type of source files
source_suffix = ['.rst', '.md']
