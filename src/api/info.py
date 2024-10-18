import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

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
        connection.execute(sqlalchemy.text(f"""INSERT INTO calendar (f_day, f_hour, r_date) VALUES (:day, :hour, CURRENT_TIMESTAMP AT TIME ZONE 'PST') RETURNING r_date"""), {"day": timsta.day, "hour": timsta.hour})
        #current_timestamp = result.fetchone()[0]
    print(f"Day: {timsta.day}  Hour: {timsta.hour}")
    #print(f"Current Timestamp: {current_timestamp}")
    return (f"Day: {timsta.day}  Hour: {timsta.hour}")
