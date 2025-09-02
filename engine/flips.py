"""
Flip strategy calculator for Albion Trade Optimizer.

Calculates profitable flip opportunities between cities with risk assessment.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .fees import FeeCalculator


@dataclass
class FlipOpportunity:
    """Represents a flip opportunity between cities."""
    item_id: str
    quality: int
    src_city: str
    dst_city: str
    strategy: str
    profit_per_unit: float
    suggested_qty: int
    expected_profit: float
    risk: str
    buy_price: float
    sell_price: float
    buy_fees: float
    sell_fees: float
    last_update_age_hours: float
    
    @property
    def risk_level(self) -> str:
        """Get risk level (alias for risk)."""
        return self.risk
    
    @property
    def source_city(self) -> str:
        """Get source city (alias for src_city)."""
        return self.src_city
    
    @property
    def destination_city(self) -> str:
        """Get destination city (alias for dst_city)."""
        return self.dst_city
    
    @property
    def roi_percent(self) -> float:
        """Calculate ROI percentage."""
        if self.buy_price > 0:
            return (self.profit_per_unit / self.buy_price) * 100
        return 0.0
    
    @property
    def investment_per_unit(self) -> float:
        """Get investment per unit (buy price + fees)."""
        return self.buy_price + self.buy_fees


class RiskClassifier:
    """Classifies trading routes by risk level."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize risk classifier with configuration."""
        self.config = config
        self.caerleon_high_risk = config.get('risk', {}).get('caerleon_high_risk', True)
    
    def classify_route_risk(self, src_city: str, dst_city: str) -> str:
        """
        Classify route risk based on cities involved.
        
        High-risk route: any path that requires passing through red zones to Caerleon.
        Low-risk: all other city pairs.
        """
        if not self.caerleon_high_risk:
            return 'low'
        
        # Routes involving Caerleon are high-risk
        if src_city == 'Caerleon' or dst_city == 'Caerleon':
            return 'high'
        
        return 'low'


class FlipCalculator:
    """Calculates flip opportunities between cities."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize flip calculator with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.fee_calculator = FeeCalculator(config)
        self.risk_classifier = RiskClassifier(config)
        
        # Configuration values
        self.cities = config.get('cities', [])
        self.max_age_hours = config.get('freshness', {}).get('max_age_hours', 24)
    
    def calculate_flip_opportunities(self, prices_by_item: Dict[str, List[Dict[str, Any]]], 
                                   activity_scores: Optional[Dict[str, Dict[str, Any]]] = None) -> List[FlipOpportunity]:
        """
        Calculate all flip opportunities from price data.
        
        Args:
            prices_by_item: {item_id: [price_records]}
            activity_scores: {item_id: {city: activity_data}}
        
        Returns:
            List of flip opportunities sorted by profit
        """
        opportunities = []
        
        for item_id, price_records in prices_by_item.items():
            # Group prices by city and quality
            prices_by_city = {}
            for price in price_records:
                key = (price['city'], price['quality'])
                if key not in prices_by_city:
                    prices_by_city[key] = price
                else:
                    # Keep the most recent price
                    if price['observed_at_utc'] > prices_by_city[key]['observed_at_utc']:
                        prices_by_city[key] = price
            
            # Calculate opportunities for each quality level
            qualities = set(key[1] for key in prices_by_city.keys())
            
            for quality in qualities:
                quality_prices = {city: price for (city, q), price in prices_by_city.items() if q == quality}
                
                # Calculate flips between all city pairs
                city_pairs = [(src, dst) for src in quality_prices.keys() for dst in quality_prices.keys() if src != dst]
                
                for src_city, dst_city in city_pairs:
                    src_price = quality_prices[src_city]
                    dst_price = quality_prices[dst_city]
                    
                    # Calculate both strategies
                    flip_results = self._calculate_city_pair_flips(
                        item_id, quality, src_city, dst_city, src_price, dst_price, activity_scores
                    )
                    
                    opportunities.extend(flip_results)
        
        # Sort by profit descending
        opportunities.sort(key=lambda x: x.profit_per_unit, reverse=True)
        
        return opportunities
    
    def _calculate_city_pair_flips(self, item_id: str, quality: int, src_city: str, dst_city: str,
                                  src_price: Dict[str, Any], dst_price: Dict[str, Any],
                                  activity_scores: Optional[Dict[str, Dict[str, Any]]] = None) -> List[FlipOpportunity]:
        """Calculate flip opportunities for a specific city pair."""
        opportunities = []
        
        # Prepare price data for fee calculator
        src_prices = {
            'sell_price_min': src_price.get('sell_price_min'),
            'buy_price_max': src_price.get('buy_price_max')
        }
        
        dst_prices = {
            'sell_price_min': dst_price.get('sell_price_min'),
            'buy_price_max': dst_price.get('buy_price_max')
        }
        
        # Skip if essential prices are missing
        if not all([src_prices['sell_price_min'], dst_prices['buy_price_max']]):
            return opportunities
        
        # Calculate both strategies
        strategies = self.fee_calculator.calculate_both_strategies(src_prices, dst_prices)
        
        # Classify route risk
        risk = self.risk_classifier.classify_route_risk(src_city, dst_city)
        
        # Get activity score for quantity suggestion
        suggested_qty = self._get_suggested_quantity(item_id, src_city, dst_city, activity_scores)
        
        # Calculate age of price data
        src_age = self._calculate_age_hours(src_price['observed_at_utc'])
        dst_age = self._calculate_age_hours(dst_price['observed_at_utc'])
        max_age = max(src_age, dst_age)
        
        # Create opportunities for both strategies
        for strategy_name, strategy_data in strategies.items():
            if strategy_data['profit_per_unit'] > 0:  # Only profitable flips
                opportunity = FlipOpportunity(
                    item_id=item_id,
                    quality=quality,
                    src_city=src_city,
                    dst_city=dst_city,
                    strategy=strategy_name,
                    profit_per_unit=strategy_data['profit_per_unit'],
                    suggested_qty=suggested_qty,
                    expected_profit=strategy_data['profit_per_unit'] * suggested_qty,
                    risk=risk,
                    buy_price=strategy_data['buy_price'],
                    sell_price=strategy_data['sell_price'],
                    buy_fees=strategy_data['buy_fees'],
                    sell_fees=strategy_data['sell_fees'],
                    last_update_age_hours=max_age
                )
                opportunities.append(opportunity)
        
        return opportunities
    
    def _get_suggested_quantity(self, item_id: str, src_city: str, dst_city: str,
                              activity_scores: Optional[Dict[str, Dict[str, Any]]] = None) -> int:
        """Get suggested quantity based on activity scores."""
        if not activity_scores or item_id not in activity_scores:
            return 1  # Conservative default
        
        item_activity = activity_scores[item_id]
        
        # Get activity for both cities
        src_activity = item_activity.get(src_city, {})
        dst_activity = item_activity.get(dst_city, {})
        
        # Use the lower of the two suggested quantities
        src_qty = src_activity.get('suggested_max_qty', 1)
        dst_qty = dst_activity.get('suggested_max_qty', 1)
        
        return min(src_qty, dst_qty)
    
    def _calculate_age_hours(self, observed_at_utc) -> float:
        """Calculate age of price data in hours."""
        from datetime import datetime
        
        if isinstance(observed_at_utc, str):
            # Parse string timestamp if needed
            from datetime import datetime
            observed_at_utc = datetime.fromisoformat(observed_at_utc.replace('Z', '+00:00'))
        
        age = datetime.utcnow() - observed_at_utc
        return age.total_seconds() / 3600
    
    def filter_opportunities(self, opportunities: List[FlipOpportunity],
                           min_profit: float = 0,
                           max_age_hours: Optional[float] = None,
                           risk_filter: Optional[str] = None,
                           cities_filter: Optional[List[str]] = None) -> List[FlipOpportunity]:
        """
        Filter flip opportunities based on criteria.
        
        Args:
            opportunities: List of flip opportunities
            min_profit: Minimum profit per unit
            max_age_hours: Maximum age of price data in hours
            risk_filter: 'low', 'high', or None for all
            cities_filter: List of cities to include (both src and dst)
        
        Returns:
            Filtered list of opportunities
        """
        filtered = opportunities
        
        # Filter by minimum profit
        if min_profit > 0:
            filtered = [opp for opp in filtered if opp.profit_per_unit >= min_profit]
        
        # Filter by age
        if max_age_hours is not None:
            filtered = [opp for opp in filtered if opp.last_update_age_hours <= max_age_hours]
        
        # Filter by risk
        if risk_filter:
            filtered = [opp for opp in filtered if opp.risk == risk_filter]
        
        # Filter by cities
        if cities_filter:
            filtered = [opp for opp in filtered 
                       if opp.src_city in cities_filter and opp.dst_city in cities_filter]
        
        return filtered
    
    def get_best_opportunities_by_item(self, opportunities: List[FlipOpportunity]) -> Dict[str, FlipOpportunity]:
        """
        Get the best opportunity for each item (highest profit per unit).
        
        Returns:
            Dictionary mapping item_id to best opportunity
        """
        best_by_item = {}
        
        for opp in opportunities:
            key = f"{opp.item_id}_q{opp.quality}"
            if key not in best_by_item or opp.profit_per_unit > best_by_item[key].profit_per_unit:
                best_by_item[key] = opp
        
        return best_by_item
    
    def calculate_portfolio_profit(self, opportunities: List[FlipOpportunity], 
                                 capital_limit: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate total profit for a portfolio of opportunities.
        
        Args:
            opportunities: List of selected opportunities
            capital_limit: Maximum capital to invest
        
        Returns:
            Portfolio analysis
        """
        total_investment = 0
        total_profit = 0
        selected_opportunities = []
        
        # Sort by profit per unit descending
        sorted_opps = sorted(opportunities, key=lambda x: x.profit_per_unit, reverse=True)
        
        for opp in sorted_opps:
            investment_needed = opp.buy_price * opp.suggested_qty
            
            if capital_limit is None or total_investment + investment_needed <= capital_limit:
                total_investment += investment_needed
                total_profit += opp.expected_profit
                selected_opportunities.append(opp)
            
            if capital_limit and total_investment >= capital_limit:
                break
        
        return {
            'total_investment': total_investment,
            'total_profit': total_profit,
            'roi_percentage': (total_profit / total_investment * 100) if total_investment > 0 else 0,
            'num_opportunities': len(selected_opportunities),
            'selected_opportunities': selected_opportunities
        }

