from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import research, financial

app = FastAPI(
    title="Autonomous Research Assistant API",
    description="Decomposes research queries, retrieves multi-source data, scores credibility, and synthesizes structured reports.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router, prefix="/api/v1/research", tags=["Research"])
app.include_router(financial.router, prefix="/api/v1/financial", tags=["Financial"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
