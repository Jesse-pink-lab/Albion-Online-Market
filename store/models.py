"""
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
    status = Column(String(50), nullable=True)
    items_count = Column(Integer, nullable=True)
    cities_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    flips = relationship('Flip', back_populates='scan', cascade='all, delete-orphan')


class Flip(Base):
    """Stored flip opportunity."""

    __tablename__ = 'flips'

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(Integer, ForeignKey('scans.id'), nullable=False, index=True)
    item_id = Column(String(50), nullable=False, index=True)
    quality = Column(Integer, nullable=False, default=1)
    src_city = Column(String(50), nullable=False)
    dst_city = Column(String(50), nullable=False)
    strategy = Column(String(50), nullable=False)
    profit_per_unit = Column(Float, nullable=False)
    suggested_qty = Column(Integer, nullable=False)
    expected_profit = Column(Float, nullable=False)
    risk = Column(String(20), nullable=True)
    buy_price = Column(Float, nullable=True)
    sell_price = Column(Float, nullable=True)
    buy_fees = Column(Float, nullable=True)
    sell_fees = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    scan = relationship('Scan', back_populates='flips')


class CraftPlan(Base):
    """Stored crafting plan."""

    __tablename__ = 'craft_plans'

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_cost = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())


class ActivityScore(Base):
    """Activity or liquidity score for an item in a city."""

    __tablename__ = 'activity_scores'

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(50), nullable=False, index=True)
    city = Column(String(50), nullable=False, index=True)
    score = Column(Float, nullable=False)
    last_updated_utc = Column(DateTime, nullable=False, default=func.now())


class AppSettings(Base):
    """Application key/value settings."""

    __tablename__ = 'app_settings'

    key = Column(String(100), primary_key=True)
    value = Column(String(500), nullable=True)
    value_type = Column(String(50), nullable=True)
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
