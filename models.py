Database models for Albion Trade Optimizer.

Defines SQLAlchemy models for storing market data, scans, flips, and craft plans.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Price(Base):
    """Market price data for items across cities."""
    
    __tablename__ = 'prices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(50), nullable=False, index=True)
    quality = Column(Integer, nullable=False, default=1, index=True)
    city = Column(String(50), nullable=False, index=True)
    sell_price_min = Column(Float, nullable=True)  # Lowest asking price
    sell_price_max = Column(Float, nullable=True)  # Highest asking price
    buy_price_min = Column(Float, nullable=True)   # Lowest buy order
    buy_price_max = Column(Float, nullable=True)   # Highest buy order
    observed_at_utc = Column(DateTime, nullable=False, default=func.now(), index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_item_city_quality_time', 'item_id', 'city', 'quality', 'observed_at_utc'),
        Index('idx_item_quality_time', 'item_id', 'quality', 'observed_at_utc'),
        Index('idx_city_time', 'city', 'observed_at_utc'),
    )
    
    def __repr__(self):
        return f"<Price(item={self.item_id}, city={self.city}, quality={self.quality})>"


class Scan(Base):
    """Record of market data scanning sessions."""
    
    __tablename__ = 'scans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at_utc = Column(DateTime, nullable=False, default=func.now())
    finished_at_utc = Column(DateTime, nullable=True)
