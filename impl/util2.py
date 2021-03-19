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

_ezidUrl = None
_arkTestPrefix = None
_doiTestPrefix = None
_crossrefTestPrefix = None
_defaultArkProfile = None
_defaultDoiProfile = None
_defaultUuidProfile = None
_doiResolver = None
_arkResolver = None


def loadConfig():
    import impl.config

    global _ezidUrl, _arkTestPrefix, _doiTestPrefix, _defaultArkProfile
    global _defaultDoiProfile, _defaultUuidProfile, _doiResolver, _arkResolver
    global _crossrefTestPrefix
    _ezidUrl = django.conf.settings.EZID_BASE_URL
    _arkTestPrefix = django.conf.settings.SHOULDERS_ARK_TEST
    _doiTestPrefix = django.conf.settings.SHOULDERS_DOI_TEST
    _crossrefTestPrefix = django.conf.settings.SHOULDERS_CROSSREF_TEST
    _defaultArkProfile = (
        django.conf.settings.ARK_PROFILE
    )  # impl.config.get("default_ark_profile")
    _defaultDoiProfile = (
        django.conf.settings.DOI_PROFILE
    )  # impl.config.get("default_doi_profile")
    _defaultUuidProfile = (
        django.conf.settings.UUID_PROFILE
    )  # impl.config.get("default_uuid_profile")
    _doiResolver = django.conf.settings.RESOLVER_DOI  # impl.config.get("resolver.doi")
    _arkResolver = django.conf.settings.RESOLVER_ARK  # impl.config.get("resolver.ark")


def urlForm(identifier):
    """Returns the URL form of a qualified identifier, or "[None]" if there is
    no resolver defined for the identifier type."""
    if identifier.startswith("doi:"):
        return f"{_doiResolver}/{urllib.parse.quote(identifier[4:], ':/')}"
    elif identifier.startswith("ark:/"):
        return f"{_arkResolver}/{urllib.parse.quote(identifier, ':/')}"
    else:
        return "[None]"


def defaultTargetUrl(identifier):
    """Returns the default target URL for an identifier.

    The identifier is assumed to be in normalized, qualified form.
    """
    return f"{_ezidUrl}/id/{urllib.parse.quote(identifier, ':/')}"


def tombstoneTargetUrl(identifier):
    """Returns the "tombstone" target URL for an identifier.

    The identifier is assumed to be in normalized, qualified form.
    """
    return f"{_ezidUrl}/tombstone/id/{urllib.parse.quote(identifier, ':/')}"


def isTestIdentifier(identifier):
    """Returns True if the supplied qualified identifier is a test
    identifier."""
    return (
        identifier.startswith(_arkTestPrefix)
        or identifier.startswith(_doiTestPrefix)
        or identifier.startswith(_crossrefTestPrefix)
    )


def isTestArk(identifier):
    """Returns True if the supplied unqualified ARK (e.g., "12345/foo") is a
    test identifier."""
    return identifier.startswith(_arkTestPrefix[5:])


def isTestDoi(identifier):
    """Returns True if the supplied unqualified DOI (e.g., "10.1234/FOO") is a
    test identifier."""
    return identifier.startswith(_doiTestPrefix[4:])


def isTestCrossrefDoi(identifier):
    """Returns True if the supplied unqualified DOI (e.g., "10.1234/FOO") is a
    Crossref test identifier."""
    return identifier.startswith(_crossrefTestPrefix[4:])


def defaultProfile(identifier):
    """Returns the label of the default metadata profile (e.g., "erc") for a
    given qualified identifier."""
    if identifier.startswith("ark:/"):
        return _defaultArkProfile
    elif identifier.startswith("doi:"):
        return _defaultDoiProfile
    elif identifier.startswith("uuid:"):
        return _defaultUuidProfile
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