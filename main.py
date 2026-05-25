"""
小鱼骨GIS助手 — 主入口
启动 FastAPI 服务，所有业务逻辑分布在 app/ 目录中
"""
from app.routes import app
from app.config import SERVER_HOST, SERVER_PORT


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
