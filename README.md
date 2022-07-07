# concourse-gitea

A Concourse CI resource that triggers builds whenever a PR is submitted or updated.

## Example

Here is an example of how to use this resource to run some unit tests:

```
jobs:
  - name: tests
    on_failure:
      do:
        - put: my-pr
          params:
            status: FAILURE
    on_success:
      do:
        - put: my-pr
          params:
            status: SUCCESS
    plan:
      - get: example
        resource: my-pr
        trigger: true
      - put: my-pr
        params:
          status: PENDING
      - task: run-tests
        file: path/to/unit-tests.yml
resource_types:
  - name: pull-request
    source:
      repository: your.container.registry/concourse-gitea-pr
      tag: latest
      username: ((user))
      password: ((pw))
    type: docker-image

resources:
  - name: my-pr
    source:
      repo: repo_name
      owner: repo_owner
      hostname: git@git.example.com
      access_token: ((gitea-token))
      private_key: ((private-key))
    type: pull-request
```

## Behaviour

### `Check`

The `check` script lists all the PRs that are open and whose latest commit has a timestamp greater than the timestamp of the
last version that was fetched to Concourse. Then, it will select the oldest of these versions as the version to be fed into
the subsequent pipeline jobs.

### `In`

The `in` script pulls the branch associated with the version that was propagated by the check step. Additionally, it also
creates additional metadata to be used by subsequent steps of the pipeline (e.g. `out` or `put`)

### `Out`

The `out` script publishes the status of a job to the appropriate PR in Gitea, along with some information about the build
(e.g. URL and job name)

## Limitations

### Rebased branches

This resource does not trigger a build when the branch being pulled from is rebased on top of another branch. For instance:

- PR1 submitted to merge branch `feature/foo` into master
- Build for PR1 triggers
- PR2 submitted to merge branch `feature/bar` into master
- Build for PR2 triggers
- PR1 merged into master
- Dev pulls master and rebases `feature/bar` on top of it
- Dev pushes `feature/bar` to origin

In some systems, this will lead to starting a new build to check PR #2. However, this is not the case with this resource
because it relies on the timestamp of the last commit (the commit `feature/bar` points to). Because that does not change
after rebasing, the resource will effectively think there is no new version. A workaround is to push an empty commit to
`feature/bar`. A better approach is to think of this as an opportunity to write one more test to cover the brilliant
feature you've just implemented, or perhaps update the CHANGELOG :)

### Many open PRs

For each open PR, this resource needs to submit a `GET` request back to Gitea to fetch the timestamp of its latest commit.
As far as I can tell, this info is not returned via the `pulls` endpoint. At the moment this is done synchronously and will
take a long time to kick off the build if you have many open PRs in a given repo.
