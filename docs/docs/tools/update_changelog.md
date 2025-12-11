## Overview
The `update_changelog` tool automatically updates the CHANGELOG.md file with the PR changes.
It can be invoked manually by commenting on any PR:
```
/update_changelog
```

## Example usage

![update_changelog_comment](https://khulnasoft.com/images/pr_insight/update_changelog_comment.png){width=768}

![update_changelog](https://khulnasoft.com/images/pr_insight/update_changelog.png){width=768}

## Configuration options

Under the section `pr_update_changelog`, the [configuration file](https://github.com/KhulnaSoft/pr-insight/blob/main/pr_insight/settings/configuration.toml#L50) contains options to customize the 'update changelog' tool:

- `push_changelog_changes`: whether to push the changes to CHANGELOG.md, or just print them. Default is false (print only).
- `extra_instructions`: Optional extra instructions to the tool. For example: "focus on the changes in the file X. Ignore change in ...