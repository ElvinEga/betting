from app.core.database import Base
from sqlalchemy import  Column, Integer, String,  ForeignKey
from sqlalchemy.orm import relationship


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    jackpot_id = Column(Integer, ForeignKey("jackpots.id"))
    home = Column(String, index=True)
    away = Column(String, index=True)
    score = Column(String, index=True)
    result = Column(String, index=True)
    jackpot = relationship("Jackpot", back_populates="events")


class Jackpot(Base):
    __tablename__ = "jackpots"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    jackpot_id = Column(String, index=True)
    next_jackpot_id = Column(String, index=True)
    events = relationship("Event", back_populates="jackpot")


metadata = Base.metadata
