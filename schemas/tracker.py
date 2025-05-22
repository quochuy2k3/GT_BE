from typing import List

from beanie import PydanticObjectId
from pydantic import BaseModel
from typing import Optional

class DayStatus(BaseModel):
    date: str
    isHasValue: bool
    tracker_id: list[str] = []

class TrackerSummary(BaseModel):
    id: str
    date: str
    time: Optional[str]
    img: Optional[str]