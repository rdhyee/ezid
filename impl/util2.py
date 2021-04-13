# =============================================================================
#
# EZID :: util2.py
#
# Utility functions that require that EZID's configuration be loaded.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import urllib.error
import urllib.parse
import urllib.request
import urllib.response
import django.conf


def urlForm(identifier):
    """Returns the URL form of a qualified identifier, or "[None]" if there is
    no resolver defined for the identifier type."""
    if identifier.startswith("doi:"):
        return f"{django.conf.settings.RESOLVER_DOI}/{urllib.parse.quote(identifier[4:], ':/')}"
    elif identifier.startswith("ark:/"):
        return f"{django.conf.settings.RESOLVER_ARK}/{urllib.parse.quote(identifier, ':/')}"
    else:
        return "[None]"


def defaultTargetUrl(identifier):
    """Returns the default target URL for an identifier.

    The identifier is assumed to be in normalized, qualified form.
    """
    return f"{django.conf.settings.EZID_BASE_URL}/id/{urllib.parse.quote(identifier, ':/')}"


def tombstoneTargetUrl(identifier):
    """Returns the "tombstone" target URL for an identifier.

    The identifier is assumed to be in normalized, qualified form.
    """
    return f"{django.conf.settings.EZID_BASE_URL}/tombstone/id/{urllib.parse.quote(identifier, ':/')}"


def isTestIdentifier(identifier):
    """Returns True if the supplied qualified identifier is a test
    identifier."""
    return (
        identifier.startswith(django.conf.settings.SHOULDERS_ARK_TEST)
        or identifier.startswith(django.conf.settings.SHOULDERS_DOI_TEST)
        or identifier.startswith(django.conf.settings.SHOULDERS_CROSSREF_TEST)
    )


def isTestArk(identifier):
    """Returns True if the supplied unqualified ARK (e.g., "12345/foo") is a
    test identifier."""
    return identifier.startswith(django.conf.settings.SHOULDERS_ARK_TEST[5:])


def isTestDoi(identifier):
    """Returns True if the supplied unqualified DOI (e.g., "10.1234/FOO") is a
    test identifier."""
    return identifier.startswith(django.conf.settings.SHOULDERS_DOI_TEST[4:])


def isTestCrossrefDoi(identifier):
    """Returns True if the supplied unqualified DOI (e.g., "10.1234/FOO") is a
    Crossref test identifier."""
    return identifier.startswith(django.conf.settings.SHOULDERS_CROSSREF_TEST[4:])


def defaultProfile(identifier):
    """Returns the label of the default metadata profile (e.g., "erc") for a
    given qualified identifier."""
    if identifier.startswith("ark:/"):
        return django.conf.settings.ARK_PROFILE
    elif identifier.startswith("doi:"):
        return django.conf.settings.DOI_PROFILE
    elif identifier.startswith("uuid:"):
        return django.conf.settings.UUID_PROFILE
    else:
        assert False, "unhandled case"


_labelMapping = {
    "_o": "_owner",
    "_g": "_ownergroup",
    "_c": "_created",
    "_u": "_updated",
    "_t": "_target",
    "_p": "_profile",
    "_is": "_status",
    "_x": "_export",
    "_d": "_datacenter",
    "_cr": "_crossref",
}
