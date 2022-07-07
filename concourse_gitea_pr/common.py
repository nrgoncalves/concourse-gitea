import json
import sys
from typing import TextIO

from .defs import PrResource, PrVersion
from .exceptions import InvalidInstream, InvalidResourceError, InvalidVersionError


def log(msg: str, *args, **kwargs):
    """Prints a message `msg` to to stderr to be included in concourse's logs."""
    print(msg.format(*args, **kwargs), file=sys.stderr)


def validate_and_parse_input(instream: TextIO):
    """Validate and parse input provided by Concource."""

    input_ = read_instream(instream)
    resource = validate_and_parse_resource(input_["source"])
    if version := input_.get("version"):
        version = validate_and_parse_version(version)

    return resource, version


def read_instream(instream: TextIO) -> dict:
    """Read input provided on stdin."""
    try:
        v = json.load(instream)
    except Exception:
        raise InvalidInstream(f"Instream {instream} is invalid.")

    return v


def validate_and_parse_resource(source: dict) -> PrResource:
    """Validate and parse resource definition."""
    try:
        resource = PrResource(**source)
    except TypeError:
        raise InvalidResourceError(f"Invalid resource configuration {source}")

    return resource


def validate_and_parse_version(version_dict: dict) -> PrVersion:
    """Validate and parse version definition."""
    try:
        version = PrVersion(**version_dict)
    except TypeError:
        raise InvalidVersionError(f"Invalid version {version_dict}")

    return version
