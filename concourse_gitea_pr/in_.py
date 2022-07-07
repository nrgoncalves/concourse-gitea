import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TextIO

import requests

from concourse_gitea_pr.defs import PrMetadata, PrResource, PrVersion

from .common import log, validate_and_parse_input
from .exceptions import DirectoryNotFound, RequestError


def _fetch_pr(res: PrResource, version: PrVersion) -> dict:
    """Fetch a particular PR version from Gitea's API."""

    # Prepare and submit request
    headers = {"Authorization": f"token {res.access_token}"}
    r = requests.get(f"{res.endpoint}/pulls/{version.number}", headers=headers)

    # Raise if response was not OK
    if not r.ok:
        raise RequestError(f"Cannot fetch PRs. Reason: {r.reason}")

    # Return response body
    return r.json()


def _get_pr_user(user: dict) -> str:
    """Determine the user that created a given PR."""
    return (
        user.get("full_name")
        or user.get("login")
        or user.get("user_name")
        or "Unknown user"
    )


def _validate_dir(destdir: str) -> Path:
    """Verify that destination directory exists."""

    dest = Path(destdir)
    if not dest.exists():
        raise DirectoryNotFound(f"Destination directory {destdir} does not exist.")
    return dest


def _build_response(pr: dict, version: PrVersion) -> dict:
    """Build version and metadata response to be printed to stdout."""

    pr_meta = PrMetadata(
        number=pr["number"],
        title=pr["title"],
        base=pr["base"]["ref"],
        head=pr["head"]["ref"],
        created_at=pr["created_at"],
        created_by=_get_pr_user(pr["user"]),
    )

    return {"version": version.output, "metadata": pr_meta.output}


def _setup_ssh_access(resource: PrResource):
    """Create SSH key file and configure git ssh access."""

    # Create file with SSH key
    home = Path.home()
    pvt_key = home / "private_key"
    with open(pvt_key, "w") as f:
        f.write(resource.private_key + "\n")
    pvt_key.chmod(0o500)

    # Create a dedicated environment with altered GIT_SSH_COMMAND env variable
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = f"ssh -o StrictHostKeyChecking=no -l git -i {pvt_key}"

    return env


def _setup_repository(repo_dir: Path, resource: PrResource, pr_number: int):
    """Clone repo and checkout the tip of the branch for PR `pr_number`."""

    # Setup SSH access
    env = _setup_ssh_access(resource)

    # Define helper function for running shell commands
    def _command(command, **kwargs):
        subprocess.run(command, cwd=repo_dir, text=True, env=env, **kwargs)

    # Clone repo
    _command(["git", "clone", "--depth", "1", resource.uri, "."])

    # Fetch PR head
    _command(["git", "fetch", "--no-tags", "origin", f"+refs/pull/{pr_number}/head"])

    # Checkout
    _command(["git", "checkout", "-qf", "FETCH_HEAD"])


def in_(destdir: str, instream: TextIO) -> dict:
    """Fetch source code for relevant PR."""

    # Parse and validate
    resource, version = validate_and_parse_input(instream)

    # Verify that directory exists
    dest = _validate_dir(destdir)

    # Get PR for this version
    pr = _fetch_pr(resource, version)

    # Build stdout response
    response = _build_response(pr, version)

    # Setup repository
    _setup_repository(dest, resource, pr["number"])

    # Save metadata file
    with open(dest / "metadata.json", "w") as f:
        json.dump(response, f)

    return response


def main():
    destdir = sys.argv[1]
    log("Output directory: {}", destdir)

    response = in_(destdir, sys.stdin)
    print(json.dumps(response))


if __name__ == "__main__":
    main()
