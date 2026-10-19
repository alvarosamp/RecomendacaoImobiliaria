"""Disposable authenticated API for real browser integration; no production data.

Set URBIA_TEST_DATABASE_URL to a disposable PostgreSQL database. All records live
in a random schema removed on shutdown. Frontend browser tests proxy requests to
this server, so no production deployment or data import is required.
"""
import json
import os
from pathlib import Path
from uuid import uuid4
import uvicorn
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema,DropSchema
from api.routes import auth,cases,projects,organizations


def main():
    url=os.environ['URBIA_TEST_DATABASE_URL']
    engine=create_engine(url)
    schema='urbia_case_browser_'+uuid4().hex
    with engine.begin() as connection:connection.execute(CreateSchema(schema))
    translated=engine.execution_options(schema_translate_map={None:schema})
    auth.Base.metadata.create_all(translated)
    factory=sessionmaker(bind=translated)
    app=FastAPI()
    def db():
        with factory() as session:yield session
    app.dependency_overrides[auth.get_db]=db
    for module in [auth,cases,projects,organizations]:app.include_router(module.router,prefix='/api')
    @app.get('/api/scores')
    def scores():return []
    @app.get('/api/indices/timeseries')
    def dates():return {'dates':[],'records':[]}
    @app.get('/api/pipeline/status')
    def status():return {'status':'idle'}
    # The fixture purposely has no geographic tables; absence must stay pending.
    cases.territory_for_city=lambda city:[]
    info=Path('/private/tmp/urbia-case-browser.json')
    info.write_text(json.dumps({'schema':schema,'port':8773}))
    try:uvicorn.run(app,host='127.0.0.1',port=8773,log_level='warning')
    finally:
        with engine.begin() as connection:connection.execute(DropSchema(schema,cascade=True))
        engine.dispose();info.unlink(missing_ok=True)

if __name__=='__main__':main()
