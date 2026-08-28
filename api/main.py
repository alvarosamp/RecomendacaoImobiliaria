from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .routes import scores, predict, mlops, indices, pipeline, analytics, auth, concept, leads, legal, market
from recomendacao_imobiliaria.config import load_settings

app = FastAPI(title="Recomendacao Imobiliaria API", version="1.0.0")
settings = load_settings()

if settings.app_env in {"production", "prod"} and settings.jwt_secret == "development-only-change-me":
    raise RuntimeError("JWT_SECRET deve ser configurado em producao.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.include_router(auth.router,     prefix="/api")
app.include_router(scores.router,   prefix="/api")
app.include_router(predict.router,  prefix="/api")
app.include_router(mlops.router,    prefix="/api")
app.include_router(indices.router,  prefix="/api")
app.include_router(pipeline.router,  prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(concept.router, prefix="/api")
app.include_router(leads.router,   prefix="/api")
app.include_router(legal.router,   prefix="/api")
app.include_router(market.router,  prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
