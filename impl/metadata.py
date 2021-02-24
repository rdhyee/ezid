# =============================================================================
#
# EZID :: metadata.py
#
# Support for metadata profiles.  A profile is an ordered list of
# metadata elements, each of which has internal and display names and
# tooltip text.
#
# Note that this module, upon being loaded, writes
# .../PROJECT_ROOT/static/metadata_tooltips.js.
#
# Subtle point: to simplify referencing from django templates, this
# module enforces that metadata element names be globally unique.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import os.path
import re

import django.conf
import django.template.defaultfilters

import impl.config


class Element(object):
    """A metadata element."""

    def __init__(self, name, displayName, displayType, tooltip):
        self.name = name
        self.displayName = displayName
        self.displayType = displayType
        self.tooltip = tooltip

    def clone(self):
        return Element(self.name, self.displayName, self.displayType, self.tooltip)


class Profile(object):
    """A metadata profile.

    To support the (annoyingly limited) Django template language,
    metadata element names can be used as keys. Furthermore, a leading
    underscore is added to an element name if necessary.
    """

    def __init__(self, name, displayName, editable, elements):
        self.name = name
        self.displayName = displayName
        self.editable = editable
        self.elements = elements

    def clone(self):
        return Profile(
            self.name,
            self.displayName,
            self.editable,
            [e.clone() for e in self.elements],
        )

    def __getitem__(self, name):
        for e in self.elements:
            if e.name == name or e.name == "_" + name:
                return e
        raise KeyError(name)


_empty = re.compile("\s*$")
_pattern = re.compile(
    "\s*^element:([^\n]*)\ndisplayname:([^\n]*)\ndisplaytype:([^\n]*)\n"
    + "tooltip:(.*?)\n\n",
    re.M | re.S,
)


def _loadElements(file):
    f = open(file)
    s = "".join([l for l in f.readlines() if not l.startswith("#")]) + "\n\n"
    f.close()
    l = []
    while not _empty.match(s):
        m = _pattern.match(s)
        assert m, "profile parse error: " + file
        # This is a bit of a hack to get template-like variable inclusion
        # functionality in tooltip text.
        tooltip = m.group(4).strip()
        tooltip = re.sub("{{(.*?)}}", lambda m: eval(m.group(1)), tooltip)
        l.append(
            Element(m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), tooltip)
        )
        s = s[m.end() :]
    return l


_profiles = None


def loadConfig():
    global _profiles
    profiles = [
        Profile(
            getattr(django.conf.settings, f"PROFILE_{k}_NAME"),
            getattr(django.conf.settings, f"PROFILE_{k}_DISPLAY_NAME"),
            getattr(django.conf.settings, f"PROFILE_{k}_EDITABLE"),
            _loadElements(getattr(django.conf.settings, f"PROFILE_{k}_FILE")),
        )
        for k in django.conf.settings.PROFILES_KEYS.split(',')
    ]
    names = set()
    for p in profiles:
        for e in p.elements:
            assert e.name not in names, "non-globally-unique element name: " + e.name
            names.add(e.name)
    _profiles = profiles


_header = """/* This file is automatically generated by metadata._writeTooltips.
Do not edit!  Instead, modify the profile files under
PROJECT_ROOT/profiles and restart the server. */

$(document).ready(function () {
"""


def _writeTooltips():
    f = open(
        os.path.join(
            django.conf.settings.PROJECT_ROOT,
            "static",
            "javascripts",
            "metadata_tooltips.js",
        ),
        "w",
    )
    f.write(_header)
    # noinspection PyTypeChecker
    for p in _profiles:
        for e in p.elements:
            f.write(
                '$(".element_{}").tooltip({{ bodyHandler: function () {{ '.format(
                    django.template.defaultfilters.slugify(e.name)
                )
            )
            f.write(
                'return "{}"; }} }});\n'.format(
                    e.tooltip.replace("\n", " ")
                    .replace('\\', r'\\')
                    .replace('"', '\\"')
                )
            )
    f.write("});\n")
    # For popup windows...
    f.write("var all_help_tooltip_text = {};\n")
    # noinspection PyTypeChecker
    for p in _profiles:
        for e in p.elements:
            f.write(
                'all_help_tooltip_text["element_{}"] = "{}";\n'.format(
                    django.template.defaultfilters.slugify(e.name),
                    e.tooltip.replace('\n', " ")
                    .replace('\\', "\\\\")
                    .replace('"', "\\\""),
                )
            )
    f.close()


# _writeTooltips()


def getProfiles():
    """Returns a list of known metadata profiles.

    A deep copy is performed, so the caller is free to modify the
    returned objects.
    """
    # noinspection PyTypeChecker
    return [p.clone() for p in _profiles]


def getProfile(name):
    """Returns the named metadata profile, or None if there is no such profile.

    A deep copy is performed, so the caller is free to modify the
    returned object.
    """
    # noinspection PyTypeChecker
    for p in _profiles:
        if p.name == name:
            return p.clone()
    return None
