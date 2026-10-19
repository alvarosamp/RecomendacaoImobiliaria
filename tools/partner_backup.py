"""Create a private PostgreSQL archive or verify it in a NEW disposable database.

No restore command targets the source database. Requires the Docker CLI and a
PostgreSQL container configured with POSTGRES_USER and POSTGRES_DB.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4


def docker(container, command, *args, stdin=None, stdout=None):
    return subprocess.run(['docker','exec',*(['-i'] if stdin else []),container,'sh','-c',command,'--',*args],
        stdin=stdin,stdout=stdout or subprocess.PIPE,stderr=subprocess.PIPE,check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['backup','restore-check'])
    parser.add_argument('--container',required=True)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--schema',default=None,help='Optional schema for isolated integration tests')
    args=parser.parse_args()
    if args.schema and not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*',args.schema):parser.error('Invalid schema name')
    if args.action=='backup':
        fd=os.open(args.archive,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            with os.fdopen(fd,'wb') as output:
                if args.schema:docker(args.container,'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --schema="$1"',args.schema,stdout=output)
                else:docker(args.container,'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc',stdout=output)
        except BaseException:
            args.archive.unlink(missing_ok=True)
            raise
        print(json.dumps({'backup':'created','bytes':args.archive.stat().st_size}))
    else:
        database='urbia_restore_check_'+uuid4().hex
        docker(args.container,'exec createdb -U "$POSTGRES_USER" "$1"',database)
        try:
            with args.archive.open('rb') as archive:
                docker(args.container,'exec pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$1"',database,stdin=archive)
            schema=args.schema or 'public'
            counts={}
            for table in ['users','land_studies','decision_cases','decision_case_versions']:
                query=f'SELECT count(*) FROM "{schema}"."{table}"'
                try:
                    result=docker(args.container,'exec psql -U "$POSTGRES_USER" -d "$1" -At -c "$2"',database,query)
                    counts[table]=int(result.stdout.decode().strip())
                except subprocess.CalledProcessError:counts[table]=None
            if counts['decision_cases'] is None:raise RuntimeError('Archive does not contain the decision cases table in the selected schema')
            print(json.dumps({'restore':'verified_in_disposable_database','rows':counts}))
        finally:
            docker(args.container,'exec dropdb -U "$POSTGRES_USER" "$1"',database)


if __name__=='__main__':main()
