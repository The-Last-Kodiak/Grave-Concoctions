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
    print(f"Day: {timsta.day}  Hour: {timsta.hour}")
    return (f"Day: {timsta.day}  Hour: {timsta.hour}")

