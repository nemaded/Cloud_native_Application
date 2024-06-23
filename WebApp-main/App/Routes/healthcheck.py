from fastapi import APIRouter, FastAPI, HTTPException, Response, status, Depends,Request, Query
from psycopg2 import OperationalError
from ..database import engine, DATABASE_URL
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
from .. import main
router = APIRouter(    
    tags=['health_check']
)

def request_has_body(request):
    content_length = request.headers.get("content-length")
    return content_length is not None and int(content_length) > 0
#to connect the and query to check if database is connected 
def postgres_status():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect():

            return "PostgreSQL server is running"
    except :
        raise HTTPException(status_code=503, detail="PostgreSQL server is not running")

@router.get("/healthz")
def root(request: Request,
         query_param: str = Query(None, title="Query Parameter", description="This parameter is not allowed.", regex=None)):
    client_host = request.client.host
    log_message = f"Root endpoint was accessed [Method: GET, Path: /healthz, Client: {client_host}]"
    main.statsduser.incr('health_check.calling')

    logging.info(f"{log_message} - Success: PostgreSQL server is running.")

    if query_param:
        raise HTTPException(status_code=400, detail="Query parameters are not allowed for this endpoint")
    if  request_has_body(request):
        raise HTTPException(status_code=400, detail="Request payload is not allowed for GET requests")
    status = postgres_status()
    if "running" in status.lower():
        headers = {"Cache-Control": "no-cache"}  
        return Response(headers=headers)
        
    else:
        raise HTTPException(status_code=503, detail="PostgreSQL server is not running")