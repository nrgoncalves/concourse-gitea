"""Lists all open PRs.

- it filters PRs so that it returns only PRs that have been created or updated
  since last version
- sorts PRs by from least recently created/updated to most recently
  created/updated
- Prints list of resources to stdout
"""

import json
import sys
from typing import List, Optional, TextIO

import requests

from .common import log, validate_and_parse_input
from .defs import PrResource, PrVersion
from .exceptions import RequestError


def _select_new_versions(
    res: PrResource, versions: List[dict], current_version: Optional[PrVersion]
) -> List:
    """Select versions that are more recent that `current_version`.

    To do this, we need to submit individual requests to fetch branch details
    from Gitea's API.
    """

    # If a current version exists, get its latest commit datetime
    if current_version:
        since_dt = current_version.committed_at_dt

    # Endpoint and headers for HTTP requests
    endpoint = res.endpoint
    headers = {"Authorization": f"token {res.access_token}"}

    # For every version, get timestamp of last commit
    new_versions = []
    for v in versions:

        # Fetch corresponding branch from Gitea's API
        url = f"{endpoint}/branches/{v['head']['ref']}"
        r = requests.get(url, headers=headers)
        branch = r.json()

        # Create a version
        pr_version = PrVersion(
            number=v["number"],
            sha=v["head"]["sha"],
            committed_at=branch["commit"]["timestamp"],
        )

        # Append to new versions if no current_version exists or if this version
        # is more recent that current version
        if not current_version or pr_version.committed_at_dt > since_dt:
            new_versions.append(pr_version)

    return new_versions


def _fetch_open_prs(res: PrResource):
    """Fetch all open PRs from Gitea's API."""

    # Prepare and submit request
    params = {"state": "open", "sort": "oldest"}
    headers = {"Authorization": f"token {res.access_token}"}
    r = requests.get(f"{res.endpoint}/pulls", params=params, headers=headers)

    # Raise if response was not OK
    if r.status_code != 200:
        raise RequestError(f"Cannot fetch PRs. Reason: {r.reason}")

    # Get response body
    all_versions = r.json()

    return all_versions


def _fetch_next_versions(res: PrResource, current_version: Optional[PrVersion]):
    """Fetch open PRs and select versions newer than `current_version`."""

    # Fetch open PRs from Gitea
    all_versions = _fetch_open_prs(res)
    if not all_versions:
        return []

    # Get PRs that have been created/updated since the current version
    next_versions = _select_new_versions(
        res,
        all_versions,
        current_version,
    )

    # If the current version is the most recent version, return that same version
    if not next_versions:
        return [current_version]

    # Sort PRs
    return sorted(next_versions, key=lambda x: x.committed_at_dt)


def check(instream: TextIO):

    # Get resource configuration and current resource version
    resource, current_version = validate_and_parse_input(instream)

    # Get next versions
    versions = _fetch_next_versions(resource, current_version)
    log("{}", versions)

    return [v.output for v in versions]


def main():
    print(json.dumps(check(sys.stdin)))


if __name__ == "__main__":
    main()
