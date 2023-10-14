from fastapi import FastAPI, Request, exceptions
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from src.api import audit, carts, catalog, bottler, barrels, admin
import json
import logging
import sys

description = """
Central Coast Cauldrons is the premier ecommerce site for all your alchemical desires.
"""

app = FastAPI(
    title="Central Coast Cauldrons",
    description=description,
    version="0.0.1",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "Lucas Pierce",
        "email": "lupierce@calpoly.edu",
    },
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):

    body = await request.body()
    logging.info(f"Request: {request.method} {body}")

    response = await call_next(request)

    logging.info(f"Response: {response.status_code} {response.body}")
    return response

app.include_router(audit.router)
app.include_router(carts.router)
app.include_router(catalog.router)
app.include_router(bottler.router)
app.include_router(barrels.router)
app.include_router(admin.router)

@app.exception_handler(exceptions.RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    logging.error(f"The client sent invalid data!: {exc}")
    exc_json = json.loads(exc.json())
    response = {"message": [], "data": None}
    for error in exc_json:
        response['message'].append(f"{error['loc']}: {error['msg']}")

    return JSONResponse(response, status_code=422)

@app.get("/")
async def root():
    return {"message": "Welcome to the Central Coast Cauldrons."}
