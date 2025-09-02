"""
Database manager for Albion Trade Optimizer.

Handles database initialization, connections, and data access operations.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import create_engine, and_, or_, desc, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, Price, Scan, Flip, CraftPlan, ActivityScore, AppSettings


class DatabaseManager:
    """Manages database operations for the application."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize database manager with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get database path from config
        db_path = config.get('database', {}).get('path', 'data/albion_trade.db')
        self.db_path = Path(db_path)

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create database URL
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Initialize engine and session factory
        self.engine = None
        self.SessionLocal = None
        
    def initialize_database(self):
        """Initialize database engine and create tables."""
        try:
            self.logger.info(f"Initializing database at {self.db_path}")
            
            # Create engine
            self.engine = create_engine(
                self.db_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                connect_args={"check_same_thread": False}  # For SQLite
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize_database() first.")
        return self.SessionLocal()
    
    def save_prices(self, prices_data: List[Dict[str, Any]]) -> int:
        """Save price data to database."""
        if not prices_data:
            return 0
            
        session = self.get_session()
        try:
            price_objects = []
            for price_data in prices_data:
                price = Price(
                    item_id=price_data['item_id'],
                    quality=price_data.get('quality', 1),
                    city=price_data['city'],
                    sell_price_min=price_data.get('sell_price_min'),
                    sell_price_max=price_data.get('sell_price_max'),
                    buy_price_min=price_data.get('buy_price_min'),
                    buy_price_max=price_data.get('buy_price_max'),
                    observed_at_utc=price_data.get('observed_at_utc', datetime.utcnow())
                )
                price_objects.append(price)
            
            session.add_all(price_objects)
            session.commit()
            
            self.logger.info(f"Saved {len(price_objects)} price records")
            return len(price_objects)
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to save prices: {e}")
            raise
        finally:
            session.close()
    
    def get_latest_prices(self, item_ids: List[str], cities: List[str], 
                         max_age_hours: int = 24, quality: int = 1) -> List[Price]:
        """Get latest prices for specified items and cities within age limit."""
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            # Subquery to get the latest observation time for each item-city combination
            latest_times = session.query(
                Price.item_id,
                Price.city,
                Price.quality,
                func.max(Price.observed_at_utc).label('latest_time')
            ).filter(
                and_(
                    Price.item_id.in_(item_ids),
                    Price.city.in_(cities),
                    Price.quality == quality,
                    Price.observed_at_utc >= cutoff_time
                )
            ).group_by(Price.item_id, Price.city, Price.quality).subquery()
            
            # Join with the subquery to get the actual price records
            prices = session.query(Price).join(
                latest_times,
                and_(
                    Price.item_id == latest_times.c.item_id,
                    Price.city == latest_times.c.city,
                    Price.quality == latest_times.c.quality,
                    Price.observed_at_utc == latest_times.c.latest_time
                )
            ).all()
            
            return prices
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get latest prices: {e}")
            raise
        finally:
            session.close()
    
    def create_scan(self, items_count: int, cities_count: int) -> Scan:
        """Create a new scan record."""
        session = self.get_session()
        try:
            scan = Scan(
                items_count=items_count,
                cities_count=cities_count,
                status='running'
            )
            session.add(scan)
            session.commit()
            session.refresh(scan)
            
            self.logger.info(f"Created scan {scan.id}")
            return scan
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to create scan: {e}")
            raise
        finally:
            session.close()
    
    def finish_scan(self, scan_id: int, status: str = 'completed', errors: Optional[List[str]] = None):
        """Mark a scan as finished."""
        session = self.get_session()
        try:
            scan = session.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.finished_at_utc = datetime.utcnow()
                scan.status = status
                if errors:
                    import json
                    scan.errors_json = json.dumps(errors)
                session.commit()
                
                self.logger.info(f"Finished scan {scan_id} with status {status}")
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to finish scan: {e}")
            raise
        finally:
            session.close()
    
    def save_flips(self, scan_id: int, flips_data: List[Dict[str, Any]]) -> int:
        """Save flip opportunities to database."""
        if not flips_data:
            return 0
            
        session = self.get_session()
        try:
            flip_objects = []
            for flip_data in flips_data:
                flip = Flip(
                    scan_id=scan_id,
                    item_id=flip_data['item_id'],
                    quality=flip_data.get('quality', 1),
                    src_city=flip_data['src_city'],
                    dst_city=flip_data['dst_city'],
                    strategy=flip_data['strategy'],
                    profit_per_unit=flip_data['profit_per_unit'],
                    suggested_qty=flip_data.get('suggested_qty', 1),
                    expected_profit=flip_data['expected_profit'],
                    risk=flip_data.get('risk', 'low'),
                    buy_price=flip_data['buy_price'],
                    sell_price=flip_data['sell_price'],
                    buy_fees=flip_data.get('buy_fees', 0),
                    sell_fees=flip_data.get('sell_fees', 0)
                )
                flip_objects.append(flip)
            
            session.add_all(flip_objects)
            session.commit()
            
            self.logger.info(f"Saved {len(flip_objects)} flip opportunities")
            return len(flip_objects)
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to save flips: {e}")
            raise
        finally:
            session.close()
    
    def get_top_flips(self, scan_id: Optional[int] = None, limit: int = 100, 
                     min_profit: float = 0, risk_filter: Optional[str] = None) -> List[Flip]:
        """Get top flip opportunities."""
        session = self.get_session()
        try:
            query = session.query(Flip)
            
            if scan_id:
                query = query.filter(Flip.scan_id == scan_id)
            else:
                # Get latest scan
                latest_scan = session.query(Scan).filter(Scan.status == 'completed').order_by(desc(Scan.finished_at_utc)).first()
                if latest_scan:
                    query = query.filter(Flip.scan_id == latest_scan.id)
            
            if min_profit > 0:
                query = query.filter(Flip.profit_per_unit >= min_profit)
            
            if risk_filter:
                query = query.filter(Flip.risk == risk_filter)
            
            flips = query.order_by(desc(Flip.profit_per_unit)).limit(limit).all()
            return flips
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get top flips: {e}")
            raise
        finally:
            session.close()
    
    def save_craft_plans(self, plans_data: List[Dict[str, Any]]) -> int:
        """Save craft plans to database."""
        if not plans_data:
            return 0

        session = self.get_session()
        try:
            plan_objects = []
            for plan_data in plans_data:
                plan = CraftPlan(
                    item_id=plan_data['item_id'],
                    quantity=plan_data.get('quantity', 1),
                    total_cost=plan_data['min_cost'] * plan_data.get('quantity', 1),
                )
                plan_objects.append(plan)

            session.add_all(plan_objects)
            session.commit()

            self.logger.info(f"Saved {len(plan_objects)} craft plans")
            return len(plan_objects)

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to save craft plans: {e}")
            raise
        finally:
            session.close()

    def get_craft_plan(self, item_id: str) -> Optional[CraftPlan]:
        """Get craft plan for an item."""
        session = self.get_session()
        try:
            return session.query(CraftPlan).filter(CraftPlan.item_id == item_id).first()

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get craft plan: {e}")
            raise
        finally:
            session.close()
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to keep database size manageable."""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Delete old prices
            old_prices = session.query(Price).filter(Price.observed_at_utc < cutoff_date).delete()
            
            # Delete old scans and related data (cascading deletes will handle flips and craft_plans)
            old_scans = session.query(Scan).filter(Scan.started_at_utc < cutoff_date).delete()
            
            session.commit()
            
            self.logger.info(f"Cleaned up {old_prices} old price records and {old_scans} old scans")
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to cleanup old data: {e}")
            raise
        finally:
            session.close()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get application setting value."""
        session = self.get_session()
        try:
            setting = session.query(AppSettings).filter(AppSettings.key == key).first()
            if setting:
                # Convert value based on type
                if setting.value_type == 'int':
                    return int(setting.value)
                elif setting.value_type == 'float':
                    return float(setting.value)
                elif setting.value_type == 'bool':
                    return setting.value.lower() in ('true', '1', 'yes')
                elif setting.value_type == 'json':
                    import json
                    return json.loads(setting.value)
                else:
                    return setting.value
            return default
            
        except (SQLAlchemyError, ValueError) as e:
            self.logger.error(f"Failed to get setting {key}: {e}")
            return default
        finally:
            session.close()
    
    def set_setting(self, key: str, value: Any, description: str = None):
        """Set application setting value."""
        session = self.get_session()
        try:
            # Determine value type
            if isinstance(value, bool):
                value_type = 'bool'
                value_str = str(value).lower()
            elif isinstance(value, int):
                value_type = 'int'
                value_str = str(value)
            elif isinstance(value, float):
                value_type = 'float'
                value_str = str(value)
            elif isinstance(value, (dict, list)):
                value_type = 'json'
                import json
                value_str = json.dumps(value)
            else:
                value_type = 'string'
                value_str = str(value)
            
            # Update or create setting
            setting = session.query(AppSettings).filter(AppSettings.key == key).first()
            if setting:
                setting.value = value_str
                setting.value_type = value_type
                if description:
                    setting.description = description
                setting.updated_at = datetime.utcnow()
            else:
                setting = AppSettings(
                    key=key,
                    value=value_str,
                    value_type=value_type,
                    description=description
                )
                session.add(setting)
            
            session.commit()
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to set setting {key}: {e}")
            raise
        finally:
            session.close()


    def get_recent_prices(self, item_ids: List[str], cities: List[str], 
                         max_age_hours: int = 24, quality: int = 1) -> List[Dict[str, Any]]:
        """Get recent prices for specified items and cities within age limit."""
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            query = session.query(Price).filter(
                and_(
                    Price.item_id.in_(item_ids),
                    Price.city.in_(cities),
                    Price.quality == quality,
                    Price.observed_at_utc >= cutoff_time
                )
            ).order_by(desc(Price.observed_at_utc))
            
            prices = query.all()
            
            # Convert to dictionaries
            result = []
            for price in prices:
                result.append({
                    'item_id': price.item_id,
                    'city': price.city,
                    'quality': price.quality,
                    'sell_price_min': price.sell_price_min,
                    'sell_price_max': price.sell_price_max,
                    'buy_price_min': price.buy_price_min,
                    'buy_price_max': price.buy_price_max,
                    'observed_at_utc': price.observed_at_utc
                })
            
            return result
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get recent prices: {e}")
            return []
        finally:
            session.close()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        session = self.get_session()
        try:
            # Count total price records
            total_prices = session.query(Price).count()
            
            # Count recent prices (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            recent_prices = session.query(Price).filter(
                Price.observed_at_utc >= cutoff_time
            ).count()
            
            # Count unique items
            unique_items = session.query(Price.item_id).distinct().count()
            
            # Count unique cities
            unique_cities = session.query(Price.city).distinct().count()
            
            return {
                'total_records': total_prices,
                'recent_records': recent_prices,
                'unique_items': unique_items,
                'unique_cities': unique_cities,
                'database_size_mb': self._get_database_size_mb()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {
                'total_records': 0,
                'recent_records': 0,
                'unique_items': 0,
                'unique_cities': 0,
                'database_size_mb': 0
            }
        finally:
            session.close()
    
    def clear_cache(self):
        """Clear volatile tables used for price/flip/scan caching."""
        s = self.get_session()
        try:
            s.query(Price).delete()
            s.query(Flip).delete()
            s.query(Scan).delete()
            s.commit()
            self.logger.info("Cache cleared")
        finally:
            s.close()
    
    def _get_database_size_mb(self) -> float:
        """Get database file size in MB."""
        try:
            if self.db_path.exists():
                size_bytes = self.db_path.stat().st_size
                return size_bytes / (1024 * 1024)  # Convert to MB
            return 0.0
        except Exception:
            return 0.0
    
    def close(self):
        """Cleanly dispose sessions and engine."""
        if getattr(self, "SessionLocal", None):
            self.SessionLocal.close_all()
        if getattr(self, "engine", None):
            self.engine.dispose()

