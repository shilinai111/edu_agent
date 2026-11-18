# scripts/seed_data.py
# 执行：python scripts/seed_data.py
# 用途：灌入本地开发测试账号

import asyncio
import os
import sys
import uuid

# 把项目根目录放进 sys.path：保证从任意目录直接运行脚本都能 import 到 backend 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext            # 密码哈希：bcrypt 算法，只存哈希不存明文
from sqlalchemy import text                         # text()：把原生 SQL 包装成可执行语句

# 直接复用项目里的数据库依赖，不重复造：
#   get_db() → 异步生成器：yield 一个会话，正常结束自动 commit、出错自动 rollback、最后自动关闭
#   engine   → 连接池，只在脚本结束时 dispose() 收尾用
from backend.dependencies import get_db, engine

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
TENANT_ID = "tenant_default"


async def seed_users():
    """灌入测试账号（已存在则跳过）。会话取自 dependencies.get_db()，提交/回滚/关闭全由它代管"""
    print("开始连接数据库，灌入测试账号...")
    try:
        # get_db() 是异步生成器：async for 取出它 yield 出来的会话（对应 get_db 里的 yield session）
        # 循环体正常走完 → get_db 内部自动 commit；循环体抛异常 → 自动 rollback
        async for session in get_db():
            users = [
                {"username": "admin",     "email": "admin@qq.com",     "pwd": "123456",   "role": "admin"},
                {"username": "teacher01", "email": "teacher01@eduagent.local", "pwd": "Teacher@123456", "role": "teacher"},
                {"username": "student01", "email": "student01@eduagent.local", "pwd": "Student@123456", "role": "student"},
                {"username": "student02", "email": "student02@eduagent.local", "pwd": "Student@123456", "role": "student"},
                {"username": "user1", "email": "user1@qq.com", "pwd": "123456", "role": "student"},
            ]
            for u in users:
                # 命名占位符 :键名 + 字典传参：值只会当值，不会被当成 SQL 执行（防注入）
                await session.execute(
                    text("""
                        INSERT INTO users (id, tenant_id, username, email, password_hash, role)
                        VALUES (:id, :tenant_id, :username, :email, :password_hash, :role)
                        ON CONFLICT (tenant_id, email) DO NOTHING
                    """),
                    {
                        "id": uuid.uuid4(),                          # users.id 是 UUID 列，直接给 UUID 对象
                        "tenant_id": TENANT_ID,
                        "username": u["username"],
                        "email": u["email"],
                        "password_hash": pwd_context.hash(u["pwd"]),  # 存哈希，绝不存明文
                        "role": u["role"],
                    },
                )
            # 这里不用写 session.commit()：async for 正常结束后，get_db 内部会提交

        print(f"✅ 数据库连接成功，测试账号灌入完成（{len(users)} 个，已存在则跳过）：")
        for u in users:
            print(f"   {u['email']:<26}/ {u['pwd']}")
    finally:
        await engine.dispose()              # 收尾：释放连接池（脚本结束前必做）


if __name__ == "__main__":
    asyncio.run(seed_users())
