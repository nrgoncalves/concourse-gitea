import json
from io import StringIO

import pytest

from ...common import validate_and_parse_input
from ...exceptions import InvalidInstream, InvalidResourceError, InvalidVersionError


def _make_input(modifier=None):
    source = {
        "repo": "concourse-gitea",
        "owner": "owner",
        "access_token": "token",
        "hostname": "git.example.com",
        "private_key": "key",
    }
    version = {"number": 1, "sha": "d14a2e1", "committed_at": "2020-01-01 10:00:00.000"}

    input_ = {"source": source, "version": version}
    if modifier:
        input_ = modifier(input_)

    instream = json.dumps(input_)
    return StringIO(instream)


def test_valid():
    instream = _make_input()
    validate_and_parse_input(instream)


def test_valid_no_version():
    def _modify_input(v):
        v.pop("version")
        return v

    instream = _make_input(modifier=_modify_input)
    validate_and_parse_input(instream)


def test_invalid_instream():
    with pytest.raises(InvalidInstream):
        instream = json.dumps({"foo": 1})
        validate_and_parse_input(instream)


def test_invalid_source():
    def _modify_input(v):
        v["source"].pop("repo")
        return v

    with pytest.raises(InvalidResourceError):
        instream = _make_input(modifier=_modify_input)
        validate_and_parse_input(instream)


def test_invalid_version():
    def _modify_input(v):
        v["version"].pop("number")
        return v

    with pytest.raises(InvalidVersionError):
        instream = _make_input(modifier=_modify_input)
        validate_and_parse_input(instream)
