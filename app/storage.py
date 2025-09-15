from sqlalchemy import (create_engine, Column, Integer, String, DateTime, Boolean,
                        Numeric, ForeignKey, JSON)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True, echo=False)
Session = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(String, unique=True, index=True)
    plan = Column(String, default="free")  # free|premium
    plan_valid_to = Column(DateTime, nullable=True)
    free_trial_used = Column(Boolean, default=False)
    free_trial_used_at = Column(DateTime, nullable=True)
    trial_asset = Column(String, nullable=True)
    tz = Column(String, default="Europe/Moscow")
    created_at = Column(DateTime, default=datetime.utcnow)

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    stocks = Column(String, nullable=True)  # JSON строка с акциями {"SBER": 100, "GAZP": 50}
    updated_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", backref="portfolio")

class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    ticker = Column(String)   # GAZP / FXGD / ISIN для ОФЗ
    board = Column(String)    # TQBR/TQTF/TQOB
    qty = Column(Numeric)
    avg_price = Column(Numeric, nullable=True)
    currency = Column(String, default="RUB")

class WatchLevel(Base):
    __tablename__ = "watch_levels"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    ticker = Column(String)
    level_type = Column(String) # support|resistance
    value = Column(Numeric)
    note = Column(String, nullable=True)

class EventLog(Base):
    __tablename__ = "events_log"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    ticker = Column(String, nullable=True)
    event_type = Column(String)  # digest|trigger|system|billing
    payload = Column(JSON)
    sent_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(engine)
