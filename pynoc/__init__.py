"""Initialization of the pynoc package."""

# flake8: noqa
# pylint: disable=unused-import
# Since this is the package init, the imports here are not used within
# this file.

from pkg_resources import get_distribution

from cisco import CiscoSwitch
from apc import APC

# pylint: disable=maybe-no-member
# False positives: This message may report object members that are
# created dynamically, but exist at the time they are accessed.
__version__ = get_distribution('pynoc').version
