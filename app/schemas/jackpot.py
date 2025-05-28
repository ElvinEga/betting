from pydantic import BaseModel
from typing import List, Optional


class EventModel(BaseModel):
    Home: str
    Away: str
    Score: str
    Result: str


class JackpotDetails(BaseModel):
    Date: str
    JackpotId: int
    Events: List[EventModel]
    NextJackpotId: Optional[str]
