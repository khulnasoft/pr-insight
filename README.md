# PR-Insight

[![Made by Khulnasoft](https://img.shields.io/badge/Made%20by%20Khulnasoft-000000.svg?style=flat-square&logo=Khulnasoft&labelColor=000)](https://khulnasoft.com)
[![GitHub license](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/khulnasoft/pr-insight/blob/main/LICENSE)
[![CI status](https://img.shields.io/github/actions/workflow/status/khulnasoft/pr-insight/build-and-test.yaml?event=push&branch=main&style=flat-square&labelColor=000000)](https://github.com/khulnasoft/pr-insight/actions/workflows/build-and-test.yaml?query=event%3Apush+branch%3Amain)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-violet)](https://chromewebstore.google.com/detail/pr-insight-chrome-extension/ephlnjeghhogofkifjloamocljapahnl)
[![Code Benchmark](https://img.shields.io/badge/Code-Benchmark-blue)](https://khulnasoft.github.io/pr-insight/finetuning_benchmark/)
[![Discord](https://badgen.net/badge/icon/discord?icon=discord&label&color=purple)](https://discord.gg/NfDj6xsR)
[![Twitter Follow](https://img.shields.io/twitter/follow/khulnasoft)](https://twitter.com/khulnasoft)

### [Documentation](https://pr-insight-docs.khulnasoft.com/)

- See the [Installation Guide](https://pr-insight-docs.khulnasoft.com/installation/) for instructions on installing PR-Insight on different platforms.

- See the [Usage Guide](https://pr-insight-docs.khulnasoft.com/usage-guide/) for instructions on running PR-Insight tools via different interfaces, such as CLI, PR Comments, or by automatically triggering them when a new PR is opened.

- See the [Tools Guide](https://pr-insight-docs.khulnasoft.com/tools/) for a detailed description of the different tools, and the available configurations for each tool.


## Table of Contents

- [News and Updates](#news-and-updates)
- [Overview](#overview)
- [Example results](#example-results)
- [Try it now](#try-it-now)
- [Khulnasoft Merge 💎](https://pr-insight-docs.khulnasoft.com/overview/pr_insight_pro/)
- [How it works](#how-it-works)
- [Why use PR-Insight?](#why-use-pr-insight)

## News and Updates

### Jan 25, 2025

The open-source GitHub organization was updated:
`https://github.com/khulnasoft/pr-insight` →
`https://github.com/khulnasoft/pr-insight`

The Docker image should be redirected automatically to the new location.
However, if you have any issues, please update the GitHub action Docker image from
`uses: Khulnasoft/pr-insight@main`
to
`uses: khulnasoft-ai/pr-insight@main`


### Jan 2, 2025

New tool  [/Implement](https://pr-insight-docs.khulnasoft.com/tools/implement/) (💎), which converts human code review discussions and feedback into ready-to-commit code changes.


### Jan 1, 2025

Update logic and [documentation](https://pr-insight-docs.khulnasoft.com/usage-guide/changing_a_model/#ollama) for running local models via Ollama.

### December 30, 2024

Following feedback from the community, we have addressed two vulnerabilities identified in the open-source PR-Insight project. The fixes are now included in the newly released version (v0.26), available as of today.

### December 25, 2024

The `review` tool previously included a legacy feature for providing code suggestions (controlled by '--pr_reviewer.num_code_suggestion'). This functionality has been deprecated. Use instead the [`improve`](https://pr-insight-docs.khulnasoft.com/tools/improve/) tool, which offers higher quality and more actionable code suggestions.

### December 2, 2024

Open-source repositories can now freely use Khulnasoft Merge, and enjoy easy one-click installation using a marketplace [app](https://github.com/apps/khulnasoft-merge-pro-for-open-source).

<kbd><img src="https://github.com/user-attachments/assets/b0838724-87b9-43b0-ab62-73739a3a855c" width="512"></kbd>

See [here](https://pr-insight-docs.khulnasoft.com/installation/pr_insight_pro/) for more details about installing Khulnasoft Merge for private repositories.


### November 18, 2024

A new mode was enabled by default for code suggestions - `--pr_code_suggestions.focus_only_on_problems=true`:

- This option reduces the number of code suggestions received
- The suggestions will focus more on identifying and fixing code problems, rather than style considerations like best practices, maintainability, or readability.
- The suggestions will be categorized into just two groups: "Possible Issues" and "General".

Still, if you prefer the previous mode, you can set `--pr_code_suggestions.focus_only_on_problems=false` in the [configuration file](https://pr-insight-docs.khulnasoft.com/usage-guide/configuration_options/).


## Overview
<div style="text-align:left;">

Supported commands per platform:

|       |                                                                                                         | GitHub             | GitLab             | Bitbucket          | Azure DevOps |
|-------|---------------------------------------------------------------------------------------------------------|:--------------------:|:--------------------:|:--------------------:|:------------:|
| TOOLS | [Review](https://pr-insight-docs.khulnasoft.com/tools/review/)                                                                                                  | ✅ | ✅ | ✅ |      ✅       |
|       | [Describe](https://pr-insight-docs.khulnasoft.com/tools/describe/)                                                                                                | ✅ | ✅ | ✅ |      ✅       |
|       | [Improve](https://pr-insight-docs.khulnasoft.com/tools/improve/)                                                                                                 | ✅ | ✅ | ✅ |      ✅       |
|       | [Ask](https://pr-insight-docs.khulnasoft.com/tools/ask/)                                                                                                     | ✅ | ✅ | ✅ |      ✅       |
|       | ⮑ [Ask on code lines](https://pr-insight-docs.khulnasoft.com/tools/ask/#ask-lines)                              | ✅ | ✅ |                    |              |
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
|       | [Implement](https://pr-insight-docs.khulnasoft.com/tools/implement/) 💎                                        | ✅ | ✅ |         ✅          |              |
|       |                                                                                                         |                    |                    |                    |              |
| USAGE | [CLI](https://pr-insight-docs.khulnasoft.com/usage-guide/automations_and_usage/#local-repo-cli)                                                                                                     | ✅ | ✅ | ✅ |      ✅       |
|       | [App / webhook](https://pr-insight-docs.khulnasoft.com/usage-guide/automations_and_usage/#github-app)                                                                                           | ✅ | ✅ | ✅ |      ✅       |
|       | [Tagging bot](https://github.com/Khulnasoft/pr-insight#try-it-now)                                                                                             | ✅ |                    |                    |              |
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
- 💎 means this feature is available only in [Khulnasoft-Merge](https://www.khulnasoft.com/pricing/)

[//]: # (- Support for additional git providers is described in [here]&#40;./docs/Full_environments.md&#41;)
___

‣ **Auto Description ([`/describe`](https://pr-insight-docs.khulnasoft.com/tools/describe/))**: Automatically generating PR description - title, type, summary, code walkthrough and labels.
\
‣ **Auto Review ([`/review`](https://pr-insight-docs.khulnasoft.com/tools/review/))**: Adjustable feedback about the PR, possible issues, security concerns, review effort and more.
\
‣ **Code Suggestions ([`/improve`](https://pr-insight-docs.khulnasoft.com/tools/improve/))**: Code suggestions for improving the PR.
\
‣ **Question Answering ([`/ask ...`](https://pr-insight-docs.khulnasoft.com/tools/ask/))**: Answering free-text questions about the PR.
\
‣ **Update Changelog ([`/update_changelog`](https://pr-insight-docs.khulnasoft.com/tools/update_changelog/))**: Automatically updating the CHANGELOG.md file with the PR changes.
\
‣ **Find Similar Issue ([`/similar_issue`](https://pr-insight-docs.khulnasoft.com/tools/similar_issues/))**: Automatically retrieves and presents similar issues.
\
‣ **Add Documentation 💎  ([`/add_docs`](https://pr-insight-docs.khulnasoft.com/tools/documentation/))**: Generates documentation to methods/functions/classes that changed in the PR.
\
‣ **Generate Custom Labels 💎 ([`/generate_labels`](https://pr-insight-docs.khulnasoft.com/tools/custom_labels/))**: Generates custom labels for the PR, based on specific guidelines defined by the user.
\
‣ **Analyze 💎 ([`/analyze`](https://pr-insight-docs.khulnasoft.com/tools/analyze/))**: Identify code components that changed in the PR, and enables to interactively generate tests, docs, and code suggestions for each component.
\
‣ **Test 💎 ([`/test`](https://pr-insight-docs.khulnasoft.com/tools/test/))**: Generate tests for a selected component, based on the PR code changes.
\
‣ **Custom Prompt 💎 ([`/custom_prompt`](https://pr-insight-docs.khulnasoft.com/tools/custom_prompt/))**: Automatically generates custom suggestions for improving the PR code, based on specific guidelines defined by the user.
\
‣ **Generate Tests 💎 ([`/test component_name`](https://pr-insight-docs.khulnasoft.com/tools/test/))**: Generates unit tests for a selected component, based on the PR code changes.
\
‣ **CI Feedback 💎 ([`/checks ci_job`](https://pr-insight-docs.khulnasoft.com/tools/ci_feedback/))**: Automatically generates feedback and analysis for a failed CI job.
\
‣ **Similar Code 💎 ([`/find_similar_component`](https://pr-insight-docs.khulnasoft.com/tools/similar_code/))**: Retrieves the most similar code components from inside the organization's codebase, or from open-source code.
\
‣ **Implement 💎 ([`/implement`](https://pr-insight-docs.khulnasoft.com/tools/implement/))**: Generates implementation code from review suggestions.
___

## Try it now

Try the GPT-4 powered PR-Insight instantly on _your public GitHub repository_. Just mention `@KhulnaSoft-Agent` and add the desired command in any PR comment. The agent will generate a response based on your command.
For example, add a comment to any pull request with the following text:
```
@KhulnaSoft-Agent /review
```
and the agent will respond with a review of your PR.

Note that this is a promotional bot, suitable only for initial experimentation.
It does not have 'edit' access to your repo, for example, so it cannot update the PR description or add labels (`@KhulnaSoft-Agent /describe` will publish PR description as a comment). In addition, the bot cannot be used on private repositories, as it does not have access to the files there.


To set up your own PR-Insight, see the [Installation](https://pr-insight-docs.khulnasoft.com/installation/) section below.
Note that when you set your own PR-Insight or use Khulnasoft hosted PR-Insight, there is no need to mention `@KhulnaSoft-Agent ...`. Instead, directly start with the command, e.g., `/ask ...`.

---


## Khulnasoft Merge 💎
[Khulnasoft Merge](https://www.khulnasoft.com/pricing/) is a hosted version of PR-Insight, provided by Khulnasoft. It is available for a monthly fee, and provides the following benefits:
1. **Fully managed** - We take care of everything for you - hosting, models, regular updates, and more. Installation is as simple as signing up and adding the Khulnasoft Merge app to your GitHub\GitLab\BitBucket repo.
2. **Improved privacy** - No data will be stored or used to train models. Khulnasoft Merge will employ zero data retention, and will use an OpenAI account with zero data retention.
3. **Improved support** - Khulnasoft Merge users will receive priority support, and will be able to request new features and capabilities.
4. **Extra features** -In addition to the benefits listed above, Khulnasoft Merge will emphasize more customization, and the usage of static code analysis, in addition to LLM logic, to improve results.
See [here](https://pr-insight-docs.khulnasoft.com/overview/pr_insight_pro/) for a list of features available in Khulnasoft Merge.



## How it works

The following diagram illustrates PR-Insight tools and their flow:

Check out the [PR Compression strategy](https://pr-insight-docs.khulnasoft.com/core-abilities/#pr-compression-strategy) page for more details on how we convert a code diff to a manageable LLM prompt

## Why use PR-Insight?

A reasonable question that can be asked is: `"Why use PR-Insight? What makes it stand out from existing tools?"`

Here are some advantages of PR-Insight:

- We emphasize **real-life practical usage**. Each tool (review, improve, ask, ...) has a single GPT-4 call, no more. We feel that this is critical for realistic team usage - obtaining an answer quickly (~30 seconds) and affordably.
- Our [PR Compression strategy](https://pr-insight-docs.khulnasoft.com/core-abilities/#pr-compression-strategy)  is a core ability that enables to effectively tackle both short and long PRs.
- Our JSON prompting strategy enables to have **modular, customizable tools**. For example, the '/review' tool categories can be controlled via the [configuration](pr_insight/settings/configuration.toml) file. Adding additional categories is easy and accessible.
- We support **multiple git providers** (GitHub, Gitlab, Bitbucket), **multiple ways** to use the tool (CLI, GitHub Action, GitHub App, Docker, ...), and **multiple models** (GPT-4, GPT-3.5, Anthropic, Cohere, Llama2).


## Data privacy

### Self-hosted PR-Insight

- If you host PR-Insight with your OpenAI API key, it is between you and OpenAI. You can read their API data privacy policy here:
https://openai.com/enterprise-privacy

### Khulnasoft-hosted Khulnasoft Merge 💎

- When using Khulnasoft Merge 💎, hosted by Khulnasoft, we will not store any of your data, nor will we use it for training. You will also benefit from an OpenAI account with zero data retention.

- For certain clients, Khulnasoft-hosted Khulnasoft Merge will use Khulnasoft’s proprietary models — if this is the case, you will be notified.

- No passive collection of Code and Pull Requests’ data — Khulnasoft Merge will be active only when you invoke it, and it will then extract and analyze only data relevant to the executed command and queried pull request.

### Khulnasoft Merge Chrome extension

- The [Khulnasoft Merge Chrome extension](https://chromewebstore.google.com/detail/khulnasoft-merge-ai-powered-cod/ephlnjeghhogofkifjloamocljapahnl) serves solely to modify the visual appearance of a GitHub PR screen. It does not transmit any user's repo or pull request code. Code is only sent for processing when a user submits a GitHub comment that activates a PR-Insight tool, in accordance with the standard privacy policy of Khulnasoft-Merge.

## Links

- Discord community: https://discord.gg/kG35uSHDBc
- Khulnasoft site: https://www.khulnasoft.com/
- Blog: https://www.khulnasoft.com/blog/
- Troubleshooting: https://www.khulnasoft.com/blog/technical-faq-and-troubleshooting/
- Support: support@khulnasoft.com
