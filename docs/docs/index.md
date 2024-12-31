# Overview

PR-Insight is an open-source tool to help efficiently review and handle pull requests.

- See the [Installation Guide](./installation/index.md) for instructions on installing and running the tool on different git platforms.

- See the [Usage Guide](./usage-guide/index.md) for instructions on running the PR-Insight commands via different interfaces, including _CLI_, _online usage_, or by _automatically triggering_ them when a new PR is opened.

- See the [Tools Guide](./tools/index.md) for a detailed description of the different tools.


## PR-Insight Docs Smart Search

To search the documentation site using natural language:

1) Comment `/help "your question"` in either:

   - A pull request where PR-Insight is installed
   - A [PR Chat](https://pr-insight-docs.khulnasoft.com/chrome-extension/features/#pr-chat)

2) PR-Insight will respond with an [answer](https://github.com/KhulnaSoft/pr-insight/pull/1241#issuecomment-2365259334) that includes relevant documentation links.


## PR-Insight Features

PR-Insight offers extensive pull request functionalities across various git providers.

|       |                                                                                                         | GitHub             | GitLab             | Bitbucket          | Azure DevOps |
|-------|---------------------------------------------------------------------------------------------------------|:--------------------:|:--------------------:|:--------------------:|:------------:|
| TOOLS | [Review](https://pr-insight-docs.khulnasoft.com/tools/review/)                                                                                                  | ✅ | ✅ | ✅ |      ✅       |
|       | [Describe](https://pr-insight-docs.khulnasoft.com/tools/describe/)                                                                                                | ✅ | ✅ | ✅ |      ✅       |
|       | [Improve](https://pr-insight-docs.khulnasoft.com/tools/improve/)                                                                                                 | ✅ | ✅ | ✅ |      ✅       |
|       | [Ask](https://pr-insight-docs.khulnasoft.com/tools/ask/)                                                                                                     | ✅ | ✅ | ✅ |      ✅       |
|       | ⮑ [Ask on code lines](https://pr-insight-docs.khulnasoft.com/tools/ask#ask-lines)                              | ✅ | ✅ |                    |              |
|       | [Update CHANGELOG](https://pr-insight-docs.khulnasoft.com/tools/update_changelog/)                                                                                     | ✅ | ✅ | ✅ |      ✅       |
|       | [Ticket Context](https://pr-insight-docs.khulnasoft.com/core-abilities/fetching_ticket_context/) 💎  | ✅ | ✅ |  ✅                  |   |
|       | [Utilizing Best Practices](https://pr-insight-docs.khulnasoft.com/tools/improve/#best-practices) 💎  | ✅ | ✅ |  ✅                  |   |
|       | [PR Chat](https://pr-insight-docs.khulnasoft.com/chrome-extension/features/#pr-chat) 💎  | ✅ |  |                    |   |
|       | [Suggestion Tracking](https://pr-insight-docs.khulnasoft.com/tools/improve/#suggestion-tracking) 💎  | ✅ | ✅ |                    |   |
|       | [CI Feedback](https://pr-insight-docs.khulnasoft.com/tools/ci_feedback/) 💎                                    | ✅ |                    |                    |              |
|       | [PR Documentation](https://pr-insight-docs.khulnasoft.com/tools/documentation/) 💎                         | ✅ | ✅ |                   |              |
|       | [Custom Labels](https://pr-insight-docs.khulnasoft.com/tools/custom_labels/) 💎                                | ✅ | ✅ |                    |              |
|       | [Analyze](https://pr-insight-docs.khulnasoft.com/tools/analyze/) 💎                                            | ✅ | ✅ |                    |              |
|       | [Similar Code](https://pr-insight-docs.khulnasoft.com/tools/similar_code/) 💎                                  | ✅ |                    |                    |              |
|       | [Custom Prompt](https://pr-insight-docs.khulnasoft.com/tools/custom_prompt/) 💎                                | ✅ | ✅ | ✅ |              |
|       | [Test](https://pr-insight-docs.khulnasoft.com/tools/test/) 💎                                                  | ✅ | ✅ |                    |              |
|       |                                                                                                         |                    |                    |                    |              |
| USAGE | [CLI](https://pr-insight-docs.khulnasoft.com/usage-guide/automations_and_usage/#local-repo-cli)                                                                                                     | ✅ | ✅ | ✅ |      ✅       |
|       | [App / webhook](https://pr-insight-docs.khulnasoft.com/usage-guide/automations_and_usage/#github-app)                                                                                           | ✅ | ✅ | ✅ |      ✅       |
|       | [Tagging bot](https://github.com/KhulnaSoft/pr-insight#try-it-now)                                                                                             | ✅ |                    |                    |              |
|       | [Actions](https://pr-insight-docs.khulnasoft.com/installation/github/#run-as-a-github-action)                                                                                                 | ✅ |✅| ✅ |✅|
|       |                                                                                                         |                    |                    |                    |              |
| CORE  | [PR compression](https://pr-insight-docs.khulnasoft.com/core-abilities/compression_strategy/)                                                                  | ✅ | ✅ | ✅ |      ✅       |
|       | Adaptive and token-aware file patch fitting                                                             | ✅ | ✅ | ✅ |      ✅       |
|       | [Multiple models support](https://pr-insight-docs.khulnasoft.com/usage-guide/changing_a_model/)                                                                                 | ✅ | ✅ | ✅ |      ✅       |
|       | [Local and global metadata](https://pr-insight-docs.khulnasoft.com/core-abilities/metadata/)          | ✅ | ✅ | ✅ | ✅             |
|       | [Dynamic context](https://pr-insight-docs.khulnasoft.com/core-abilities/dynamic_context/)          | ✅ | ✅ | ✅ | ✅             |
|       | [Self reflection](https://pr-insight-docs.khulnasoft.com/core-abilities/self_reflection/)          | ✅ | ✅ | ✅ | ✅             |
|       | [Static code analysis](https://pr-insight-docs.khulnasoft.com/core-abilities/static_code_analysis/) 💎         | ✅ | ✅ | ✅ |              |
|       | [Global and wiki configurations](https://pr-insight-docs.khulnasoft.com/usage-guide/configuration_options/) 💎 | ✅ | ✅ | ✅ |              |
|       | [PR interactive actions](https://www.khulnasoft.com/images/pr_insight/pr-actions.mp4) 💎                       | ✅ |        ✅           |                    |              |
|       | [Impact Evaluation](https://pr-insight-docs.khulnasoft.com/core-abilities/impact_evaluation/) 💎  | ✅ | ✅ |                    |   |

💎 marks a feature available only in [PR-Insight Pro](https://www.khulnasoft.com/pricing/){:target="_blank"}


## Example Results
<hr>

#### [/describe](https://github.com/KhulnaSoft/pr-insight/pull/530)
<figure markdown="1">
![/describe](https://www.khulnasoft.com/images/pr_insight/describe_new_short_main.png){width=512}
</figure>
<hr>

#### [/review](https://github.com/KhulnaSoft/pr-insight/pull/732#issuecomment-1975099151)
<figure markdown="1">
![/review](https://www.khulnasoft.com/images/pr_insight/review_new_short_main.png){width=512}
</figure>
<hr>

#### [/improve](https://github.com/KhulnaSoft/pr-insight/pull/732#issuecomment-1975099159)
<figure markdown="1">
![/improve](https://www.khulnasoft.com/images/pr_insight/improve_new_short_main.png){width=512}
</figure>
<hr>

#### [/generate_labels](https://github.com/KhulnaSoft/pr-insight/pull/530)
<figure markdown="1">
![/generate_labels](https://www.khulnasoft.com/images/pr_insight/geneare_custom_labels_main_short.png){width=300}
</figure>
<hr>

## How it Works

The following diagram illustrates PR-Insight tools and their flow:

![PR-Insight Tools](https://khulnasoft.com/images/pr_insight/diagram-v0.9.png)

Check out the [core abilities](core-abilities/index.md) page for a comprehensive overview of the variety of core abilities used by PR-Insight.
