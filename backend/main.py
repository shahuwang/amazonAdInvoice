from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import companies, shops, uploads, reports

app = FastAPI(title="Temu/Amazon 数据管理平台", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(companies.router)
app.include_router(shops.router)
app.include_router(uploads.router)
app.include_router(reports.router)

@app.get("/")
async def root():
    return {"message": "Temu/Amazon 数据管理平台 API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
