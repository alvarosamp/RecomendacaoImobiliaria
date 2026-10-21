from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from urllib.parse import urlsplit
import json
import logging
import time
from uuid import uuid4

from .routes import scores, predict, mlops, indices, pipeline, analytics, auth, concept, leads, legal, market, projects, government, organizations, cases
from recomendacao_imobiliaria.config import load_settings

app = FastAPI(title="Recomendacao Imobiliaria API", version="1.0.0")
settings = load_settings()
request_log = logging.getLogger('urbia.http')
if not request_log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    request_log.addHandler(handler)
request_log.setLevel(logging.INFO)
request_log.propagate = False


@app.middleware('http')
async def request_metrics(request: Request, call_next):
    started, request_id = time.monotonic(), uuid4().hex
    try:
        response = await call_next(request)
    except Exception:
        request_log.error(json.dumps(dict(event='request_failed', route=getattr(request.scope.get('route'),'path','unmatched'), request_id=request_id)))
        return JSONResponse(status_code=500, content={'detail':'Não foi possível concluir a operação. Tente novamente ou informe o identificador ao responsável.', 'request_id':request_id}, headers={'X-Request-ID':request_id})
    route = getattr(request.scope.get('route'), 'path', 'unmatched')
    request_log.info(json.dumps(dict(event='request', route=route, status=response.status_code,
        duration_ms=round((time.monotonic()-started)*1000), request_id=request_id)))
    response.headers['X-Request-ID'] = request_id
    return response

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
    origin = request.headers.get("origin")
    if settings.app_env in {"production", "prod"} and origin and request.method not in {"GET", "HEAD", "OPTIONS"}:
        parsed = urlsplit(origin)
        same_origin = parsed.scheme == request.url.scheme and parsed.netloc == request.headers.get("host")
        if not same_origin and origin not in settings.cors_origins:
            return JSONResponse(status_code=403, content={"detail": "Origem nao autorizada"})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Login/cadastro são públicos; todo o resto exige usuário autenticado.
# Rotas que disparam processamento (pipeline) exigem administrador, ver pipeline.py.
authenticated = [Depends(auth.get_current_user)]

app.include_router(auth.router,     prefix="/api")
app.include_router(scores.router,   prefix="/api", dependencies=authenticated)
app.include_router(predict.router,  prefix="/api", dependencies=authenticated)
app.include_router(mlops.router,    prefix="/api", dependencies=authenticated)
app.include_router(indices.router,  prefix="/api", dependencies=authenticated)
app.include_router(pipeline.router, prefix="/api", dependencies=authenticated)
app.include_router(analytics.router, prefix="/api", dependencies=authenticated)
app.include_router(concept.router,  prefix="/api", dependencies=authenticated)
app.include_router(leads.router,    prefix="/api")
app.include_router(legal.router,    prefix="/api", dependencies=authenticated)
app.include_router(government.router, prefix="/api", dependencies=authenticated)
app.include_router(organizations.router, prefix="/api", dependencies=authenticated)
app.include_router(projects.router, prefix="/api", dependencies=authenticated)
app.include_router(market.router,   prefix="/api", dependencies=authenticated)
app.include_router(cases.router, prefix="/api", dependencies=authenticated)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get('/api/readiness')
@app.get('/health/ready')
def ready():
    from sqlalchemy import text
    try:
        with auth.engine.connect() as connection:
            connection.execute(text('SELECT 1'))
    except Exception:
        return JSONResponse(status_code=503, content={'status':'database_unavailable'})
    return {'status':'ready'}
