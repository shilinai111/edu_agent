# backend/api/router.py
# API 路由总入口

from fastapi import APIRouter,FastAPI
from starlette.middleware.cors import CORSMiddleware

from backend.api.v1 import auth, qa, exam, resume, interview, unified_chat  # 六个子模块

api_router = APIRouter()                              # 总路由

# 把每个子 router 带前缀 + 标签聚合进来
api_router.include_router(auth.router,          prefix="/auth",      tags=["认证"])
api_router.include_router(unified_chat.router,  prefix="/chat",      tags=["AI助手"])   # 本章统一入口
api_router.include_router(qa.router,            prefix="/qa",        tags=["智能问答"])  # 第 5 章
api_router.include_router(exam.router,          prefix="/exam",      tags=["试卷批改"])  # 第 6 章
api_router.include_router(resume.router,        prefix="/resume",    tags=["简历审查"])  # 第 4 章
api_router.include_router(interview.router,     prefix="/interview", tags=["模拟面试"])  # 第 7 章

if __name__ == '__main__':
    import os
    #
    # os.environ["LANGCHAIN_TRACING_V2"] = "true"
    # os.environ["LANGCHAIN_PROJECT"] = "resume_trace_pro"
    import uvicorn
    app = FastAPI(title="eduagent")

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",  # 开发环境放开所有 Origin（含 file:// 页面发出的 Origin: null）
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_private_network=True,
    )

    app.include_router(api_router,prefix="/api/v1")


    uvicorn.run(app,host="0.0.0.0",port=8003)
