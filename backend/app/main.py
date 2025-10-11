from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Gov Contracts AI API",
    description="AI-Powered Fraud Detection in Government Procurement",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar depois
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Gov Contracts AI API", "version": "0.1.0", "status": "healthy"}


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "database": "not_connected",  # Implementar depois
        "redis": "not_connected",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
