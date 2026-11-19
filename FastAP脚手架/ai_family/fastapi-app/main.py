import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.discovery import discover_routers
from common.exception_handler import setup_exception_handlers
from database import database_lifespan
from settings import settings

app = FastAPI(title=settings.app_name, lifespan=database_lifespan)

# 异常处理要先注册，CORS 中间件后注册，这样异常响应也会带上跨域响应头
setup_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)

for router in discover_routers():
    app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
