import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TextIO

import requests

from concourse_gitea_pr.defs import PrResource, PrVersion
from concourse_gitea_pr.exceptions import (
    DirectoryNotFound,
    FileNotFound,
    InvalidPutParameters,
    RequestError,
)

from .common import (
    log,
    read_instream,
    validate_and_parse_resource,
    validate_and_parse_version,
)


class StatusDescription(Enum):
    PENDING = "is pending"
    SUCCESS = "has finished successfully"
    FAILURE = "has failed"
    # TODO: Tasks pending completion -@nuno at 10/02/2022, 00:29:30
    # Add WARNING and ERROR statuses


@dataclass
class PutParams:
    status: str

    def __post_init__(self):
        self.status_description = StatusDescription[self.status].value


def _validate_and_parse_params(params: dict) -> PutParams:
    """Validate and parse put parameters definition."""
    try:
        put_params = PutParams(**params)
    except TypeError:
        raise InvalidPutParameters(f"Invalid put parameters {params}")

    return put_params


def _compose_build_url() -> str:
    """Put together the build's URL."""
    return (
        f"{os.environ['ATC_EXTERNAL_URL']}/teams/{os.environ['BUILD_TEAM_NAME']}"
        f"/pipelines/{os.environ['BUILD_PIPELINE_NAME']}/jobs/"
        f"{os.environ['BUILD_JOB_NAME']}/builds/{os.environ['BUILD_NAME']}"
    )


def _post_commit_status(resource: PrResource, url: str, data: dict):

    headers = {"Authorization": f"token {resource.access_token}"}

    r = requests.post(url, data=data, headers=headers)

    if not r.ok:
        raise RequestError(
            f"Request to update build status failed with reason {r.reason}"
        )


def _update_build_status(resource: PrResource, params: PutParams, version: PrVersion):
    """Update build status by submitting a POST request to Gitea's API."""

    # Build request
    url = f"{resource.endpoint}/statuses/{version.sha}"
    body = {
        "context": os.environ["BUILD_JOB_NAME"],
        "state": params.status.lower(),
        "target_url": _compose_build_url(),
        "description": params.status_description,
    }

    # Submit POST request to update commit status
    _post_commit_status(resource, url, body)


def _read_metadata(srcdir: Path) -> dict:

    metadata_file = srcdir / "metadata.json"

    if not metadata_file.exists():
        raise FileNotFound(f"File {metadata_file} not found.")

    with open(metadata_file, "r") as f:
        metadata = json.load(f)

    return metadata


def out(srcdir_str: str, instream: TextIO) -> dict:
    """Notify Gitea of the status of a build."""

    # Verify that srcdir exists
    srcdir = Path(srcdir_str)
    if not srcdir.exists():
        raise DirectoryNotFound(f"Source directory {srcdir_str} does not exist.")

    # Get resource configuration and current resource version
    input_ = read_instream(instream)
    resource = validate_and_parse_resource(input_["source"])
    params = _validate_and_parse_params(input_["params"])

    # Read resource version from metadata file
    metadata = _read_metadata(srcdir / resource.repo)
    pr_version = validate_and_parse_version(metadata["version"])

    # Update status via Gitea's API
    _update_build_status(resource, params, pr_version)

    return {"version": pr_version.output, "metadata": metadata["metadata"]}


def main():
    srcdir = sys.argv[1]
    log("Source directory: {}", srcdir)

    print(json.dumps(out(srcdir, sys.stdin)))


if __name__ == "__main__":
    main()
