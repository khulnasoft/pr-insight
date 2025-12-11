
After [installation](https://pr-insight-docs.khulnasoft.com/installation/), there are three basic ways to invoke KhulnaSoftAI PR-Insight:

1. Locally running a CLI command
2. Online usage - by [commenting](https://github.com/KhulnaSoft/pr-insight/pull/229#issuecomment-1695021901) on a PR
3. Enabling PR-Insight tools to run automatically when a new PR is opened


Specifically, CLI commands can be issued by invoking a pre-built [docker image](https://pr-insight-docs.khulnasoft.com/installation/locally/#using-docker-image), or by invoking a [locally cloned repo](https://pr-insight-docs.khulnasoft.com/installation/locally/#run-from-source).

For online usage, you will need to setup either a [GitHub App](https://pr-insight-docs.khulnasoft.com/installation/github/#run-as-a-github-app) or a [GitHub Action](https://pr-insight-docs.khulnasoft.com/installation/github/#run-as-a-github-action) (GitHub), a [GitLab webhook](https://pr-insight-docs.khulnasoft.com/installation/gitlab/#run-a-gitlab-webhook-server) (GitLab), or a [BitBucket App](https://pr-insight-docs.khulnasoft.com/installation/bitbucket/#run-using-khulnasoft-hosted-bitbucket-app) (BitBucket).
These platforms also enable to run PR-Insight specific tools automatically when a new PR is opened, or on each push to a branch.

