## PR-Insight Pro Models

The default models used by PR-Insight Pro are a combination of Claude-3.5-sonnet and  OpenAI's GPT-4 models.

Users can configure PR-Insight Pro to use solely a specific model by editing the [configuration](https://pr-insight-docs.khulnasoft.com/usage-guide/configuration_options/) file.

For example, to restrict PR-Insight Pro to using only `Claude-3.5-sonnet`, add this setting:

```
[config]
model="claude-3-5-sonnet"
```

Or to restrict PR-Insight Pro to using only `GPT-4o`, add this setting:
```
[config]
model="gpt-4o"
```
