from readyapi import ReadyAPI
from mangum import Mangum
from starlette.middleware import Middleware
from starlette_context.middleware import RawContextMiddleware

from pr_insight.servers.github_app import router


middleware = [Middleware(RawContextMiddleware)]
app = ReadyAPI(middleware=middleware)
app.include_router(router)

handler = Mangum(app, lifespan="off")


def serverless(event, context):
    return handler(event, context)
