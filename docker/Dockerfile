FROM python:3.12.3 AS base

WORKDIR /app
ADD pyproject.toml .
ADD requirements.txt .
RUN pip install . && rm pyproject.toml requirements.txt
ENV PYTHONPATH=/app

FROM base AS github_app
ADD pr_insight pr_insight
CMD ["python", "-m", "gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-c", "pr_insight/servers/gunicorn_config.py", "--forwarded-allow-ips", "*", "pr_insight.servers.github_app:app"]

FROM base AS bitbucket_app
ADD pr_insight pr_insight
CMD ["python", "pr_insight/servers/bitbucket_app.py"]

FROM base AS bitbucket_server_webhook
ADD pr_insight pr_insight
CMD ["python", "pr_insight/servers/bitbucket_server_webhook.py"]

FROM base AS github_polling
ADD pr_insight pr_insight
CMD ["python", "pr_insight/servers/github_polling.py"]

FROM base AS gitlab_webhook
ADD pr_insight pr_insight
CMD ["python", "pr_insight/servers/gitlab_webhook.py"]

FROM base AS azure_devops_webhook
ADD pr_insight pr_insight
CMD ["python", "pr_insight/servers/azuredevops_server_webhook.py"]

FROM base AS test
ADD requirements-dev.txt .
RUN pip install -r requirements-dev.txt && rm requirements-dev.txt
ADD pr_insight pr_insight
ADD tests tests

FROM base AS cli
ADD pr_insight pr_insight
ENTRYPOINT ["python", "pr_insight/cli.py"]
