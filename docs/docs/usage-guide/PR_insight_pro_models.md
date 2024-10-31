## Khulnasoft Merge Pro Models

The default models used by Khulnasoft Merge Pro are a combination of Claude-3.5-sonnet and  OpenAI's GPT-4 models.

Users can configure Khulnasoft Merge Pro to use solely a specific model by editing the [configuration](https://pr-insight-docs.khulnasoft.com/usage-guide/configuration_options/) file.

For example, to restrict Khulnasoft Merge Pro to using only `Claude-3.5-sonnet`, add this setting:

```
[config]
model="claude-3-5-sonnet"
```

Or to restrict Khulnasoft Merge Pro to using only `GPT-4o`, add this setting:
```
[config]
model="gpt-4o"
```
