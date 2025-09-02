"""
Liquidity and activity scoring engine for Albion Trade Optimizer.

Tracks market activity and suggests trading volumes based on price update frequency.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from store.db import DatabaseManager


@dataclass
class ActivityMetrics:
    """Activity metrics for an item in a city."""
    item_id: str
    city: str
    quality: int
    score: float
    updates_per_day: float
    last_update: Optional[datetime]
    suggested_max_qty: int
    data_age_hours: float
    confidence: str  # 'high', 'medium', 'low'


class ActivityScorer:
    """Calculates activity scores and suggests trading volumes."""
    
    def __init__(self, config: Dict[str, Any], db_manager: DatabaseManager):
        """Initialize activity scorer."""
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.analysis_window_days = 7  # Days to look back for activity analysis
        self.min_updates_for_confidence = 5  # Minimum updates for high confidence
        self.default_max_qty = 1  # Default conservative quantity
        self.max_suggested_qty = 100  # Maximum suggested quantity
    
    def calculate_activity_scores(self, item_ids: List[str], cities: List[str], 
                                quality: int = 1) -> Dict[str, Dict[str, ActivityMetrics]]:
        """
        Calculate activity scores for items across cities.
        
        Returns:
            {item_id: {city: ActivityMetrics}}
        """
        results = {}
        
        for item_id in item_ids:
            results[item_id] = {}
            
            for city in cities:
                metrics = self._calculate_item_city_activity(item_id, city, quality)
                results[item_id][city] = metrics
        
        return results
    
    def _calculate_item_city_activity(self, item_id: str, city: str, quality: int) -> ActivityMetrics:
        """Calculate activity metrics for a specific item-city combination."""
        # Get price history for the analysis window
        cutoff_date = datetime.utcnow() - timedelta(days=self.analysis_window_days)
        
        session = self.db_manager.get_session()
        try:
            from store.models import Price
            from sqlalchemy import and_, func
            
            # Get all price updates in the window
            price_updates = session.query(Price).filter(
                and_(
                    Price.item_id == item_id,
                    Price.city == city,
                    Price.quality == quality,
                    Price.observed_at_utc >= cutoff_date
                )
            ).order_by(Price.observed_at_utc).all()
            
            # Get the most recent update
            latest_update = session.query(Price).filter(
                and_(
                    Price.item_id == item_id,
                    Price.city == city,
                    Price.quality == quality
                )
            ).order_by(Price.observed_at_utc.desc()).first()
            
        finally:
            session.close()
        
        # Calculate metrics
        num_updates = len(price_updates)
        updates_per_day = num_updates / self.analysis_window_days
        
        # Calculate activity score (0-100)
        score = self._calculate_score(updates_per_day, num_updates)
        
        # Suggest maximum quantity
        suggested_qty = self._suggest_quantity(score, updates_per_day, num_updates)
        
        # Determine confidence level
        confidence = self._determine_confidence(num_updates, updates_per_day)
        
        # Calculate data age
        data_age_hours = 0
        last_update = None
        if latest_update:
            last_update = latest_update.observed_at_utc
            data_age_hours = (datetime.utcnow() - last_update).total_seconds() / 3600
        
        return ActivityMetrics(
            item_id=item_id,
            city=city,
            quality=quality,
            score=score,
            updates_per_day=updates_per_day,
            last_update=last_update,
            suggested_max_qty=suggested_qty,
            data_age_hours=data_age_hours,
            confidence=confidence
        )
    
    def _calculate_score(self, updates_per_day: float, total_updates: int) -> float:
        """
        Calculate activity score (0-100) based on update frequency.
        
        Score factors:
        - Updates per day (frequency)
        - Total number of updates (volume)
        - Consistency over time
        """
        # Base score from updates per day (0-70 points)
        frequency_score = min(updates_per_day * 10, 70)
        
        # Bonus for having sufficient data points (0-20 points)
        volume_bonus = min(total_updates * 2, 20)
        
        # Consistency bonus (0-10 points) - placeholder for now
        consistency_bonus = 10 if total_updates >= self.min_updates_for_confidence else 0
        
        total_score = frequency_score + volume_bonus + consistency_bonus
        return min(total_score, 100)
    
    def _suggest_quantity(self, score: float, updates_per_day: float, total_updates: int) -> int:
        """Suggest maximum trading quantity based on activity."""
        if total_updates == 0:
            return self.default_max_qty
        
        # Base quantity from score
        base_qty = int(score / 10)  # 0-10 based on score
        
        # Adjust based on update frequency
        if updates_per_day >= 5:  # Very active
            multiplier = 3
        elif updates_per_day >= 2:  # Active
            multiplier = 2
        elif updates_per_day >= 0.5:  # Moderate
            multiplier = 1.5
        else:  # Low activity
            multiplier = 1
        
        suggested = int(base_qty * multiplier)
        
        # Apply bounds
        suggested = max(suggested, self.default_max_qty)
        suggested = min(suggested, self.max_suggested_qty)
        
        return suggested
    
    def _determine_confidence(self, total_updates: int, updates_per_day: float) -> str:
        """Determine confidence level for the activity assessment."""
        if total_updates >= self.min_updates_for_confidence and updates_per_day >= 1:
            return 'high'
        elif total_updates >= 2 and updates_per_day >= 0.2:
            return 'medium'
        else:
            return 'low'
    
    def get_market_overview(self, activity_data: Dict[str, Dict[str, ActivityMetrics]]) -> Dict[str, Any]:
        """Generate market overview statistics."""
        all_metrics = []
        for item_data in activity_data.values():
            all_metrics.extend(item_data.values())
        
        if not all_metrics:
            return {
                'total_markets': 0,
                'active_markets': 0,
                'average_score': 0,
                'high_confidence_markets': 0
            }
        
        # Calculate statistics
        total_markets = len(all_metrics)
        active_markets = len([m for m in all_metrics if m.score > 20])
        average_score = sum(m.score for m in all_metrics) / total_markets
        high_confidence = len([m for m in all_metrics if m.confidence == 'high'])
        
        # Find most active markets
        top_markets = sorted(all_metrics, key=lambda x: x.score, reverse=True)[:10]
        
        return {
            'total_markets': total_markets,
            'active_markets': active_markets,
            'average_score': average_score,
            'high_confidence_markets': high_confidence,
            'activity_distribution': self._get_activity_distribution(all_metrics),
            'top_markets': [(m.item_id, m.city, m.score) for m in top_markets],
            'stale_data_warning': len([m for m in all_metrics if m.data_age_hours > 24])
        }
    
    def _get_activity_distribution(self, metrics: List[ActivityMetrics]) -> Dict[str, int]:
        """Get distribution of markets by activity level."""
        distribution = {
            'very_high': 0,  # 80-100
            'high': 0,       # 60-79
            'medium': 0,     # 40-59
            'low': 0,        # 20-39
            'very_low': 0    # 0-19
        }
        
        for metric in metrics:
            if metric.score >= 80:
                distribution['very_high'] += 1
            elif metric.score >= 60:
                distribution['high'] += 1
            elif metric.score >= 40:
                distribution['medium'] += 1
            elif metric.score >= 20:
                distribution['low'] += 1
            else:
                distribution['very_low'] += 1
        
        return distribution
    
    def update_activity_scores_in_db(self, activity_data: Dict[str, Dict[str, ActivityMetrics]]):
        """Update activity scores in the database."""
        session = self.db_manager.get_session()
        try:
            from store.models import ActivityScore
            from sqlalchemy import and_
            
            for item_id, city_data in activity_data.items():
                for city, metrics in city_data.items():
                    # Check if record exists
                    existing = session.query(ActivityScore).filter(
                        and_(
                            ActivityScore.item_id == item_id,
                            ActivityScore.city == city,
                            ActivityScore.quality == metrics.quality
                        )
                    ).first()
                    
                    if existing:
                        # Update existing record
                        existing.score = metrics.score
                        existing.updates_per_day = metrics.updates_per_day
                        existing.last_update_utc = metrics.last_update
                        existing.suggested_max_qty = metrics.suggested_max_qty
                        existing.computed_at_utc = datetime.utcnow()
                    else:
                        # Create new record
                        new_score = ActivityScore(
                            item_id=item_id,
                            city=city,
                            quality=metrics.quality,
                            score=metrics.score,
                            updates_per_day=metrics.updates_per_day,
                            last_update_utc=metrics.last_update,
                            suggested_max_qty=metrics.suggested_max_qty
                        )
                        session.add(new_score)
            
            session.commit()
            self.logger.info("Updated activity scores in database")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to update activity scores: {e}")
            raise
        finally:
            session.close()
    
    def get_activity_warnings(self, activity_data: Dict[str, Dict[str, ActivityMetrics]]) -> List[str]:
        """Generate warnings about market activity."""
        warnings = []
        
        for item_id, city_data in activity_data.items():
            for city, metrics in city_data.items():
                # Warn about stale data
                if metrics.data_age_hours > 48:
                    warnings.append(f"{item_id} in {city}: Data is {metrics.data_age_hours:.1f} hours old")
                
                # Warn about low activity
                if metrics.confidence == 'low' and metrics.score < 10:
                    warnings.append(f"{item_id} in {city}: Very low market activity (score: {metrics.score:.1f})")
                
                # Warn about no recent updates
                if metrics.updates_per_day < 0.1:
                    warnings.append(f"{item_id} in {city}: No recent price updates")
        
        return warnings
    
    def filter_by_activity(self, opportunities: List[Any], min_score: float = 20,
                          activity_data: Optional[Dict[str, Dict[str, ActivityMetrics]]] = None) -> List[Any]:
        """
        Filter opportunities by minimum activity score.
        
        Args:
            opportunities: List of flip opportunities or other market opportunities
            min_score: Minimum activity score required
            activity_data: Activity data to use for filtering
        
        Returns:
            Filtered list of opportunities
        """
        if not activity_data:
            return opportunities
        
        filtered = []
        
        for opp in opportunities:
            # Get activity scores for source and destination cities
            item_activity = activity_data.get(opp.item_id, {})
            src_activity = item_activity.get(opp.src_city, ActivityMetrics(
                opp.item_id, opp.src_city, 1, 0, 0, None, 1, 0, 'low'
            ))
            dst_activity = item_activity.get(opp.dst_city, ActivityMetrics(
                opp.item_id, opp.dst_city, 1, 0, 0, None, 1, 0, 'low'
            ))
            
            # Require both cities to meet minimum activity
            if src_activity.score >= min_score and dst_activity.score >= min_score:
                filtered.append(opp)
        
        return filtered

