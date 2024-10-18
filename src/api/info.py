import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from datetime import datetime

router = APIRouter(
    prefix="/info",
    tags=["info"],
    dependencies=[Depends(auth.get_api_key)],
)

class Timestamp(BaseModel):
    day: str
    hour: int

@router.post("/current_time")
def post_time(timsta: Timestamp):
    """Share current time."""
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"""
        INSERT INTO calendar (f_day, f_hour)
        VALUES ('{timsta.day}', {timsta.hour})"""))
    print(f"Day: {timsta.day}  Hour: {timsta.hour}")
    return (f"Day: {timsta.day}  Hour: {timsta.hour}")

