from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import scores, predict, mlops, indices, pipeline, analytics, auth, concept, leads

app = FastAPI(title="Recomendacao Imobiliaria API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api")
app.include_router(scores.router,   prefix="/api")
app.include_router(predict.router,  prefix="/api")
app.include_router(mlops.router,    prefix="/api")
app.include_router(indices.router,  prefix="/api")
app.include_router(pipeline.router,  prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(concept.router, prefix="/api")
app.include_router(leads.router,   prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
