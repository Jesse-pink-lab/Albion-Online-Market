"""
Fee calculation engine for Albion Trade Optimizer.

Implements exact fee calculations for buying and selling operations according to specification.
"""

from typing import Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class FeeCalculation:
    """Result of fee calculation."""
    gross_amount: float
    fees: float
    net_amount: float
    fee_breakdown: Dict[str, float]


class FeeCalculator:
    """Calculates fees for trading operations in Albion Online."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize fee calculator with configuration."""
        self.config = config
        
        # Fee rates from config
        self.sales_tax_premium = config.get('fees', {}).get('sales_tax_premium', 0.04)
        self.sales_tax_no_premium = config.get('fees', {}).get('sales_tax_no_premium', 0.08)
        self.setup_fee = config.get('fees', {}).get('setup_fee', 0.025)
        
        # Premium status
        self.premium_enabled = config.get('premium_enabled', True)
    
    def get_sales_tax(self, premium: bool = None) -> float:
        """Get sales tax rate based on premium status."""
        if premium is None:
            premium = self.premium_enabled
        
        return self.sales_tax_premium if premium else self.sales_tax_no_premium
    
    def calculate_instant_buy_cost(self, market_price: float) -> FeeCalculation:
        """
        Calculate cost for instant buy (buy into sell orders).
        
        Instant buy: pay market sell_price_min, no fee.
        """
        return FeeCalculation(
            gross_amount=market_price,
            fees=0.0,
            net_amount=market_price,
            fee_breakdown={}
        )
    
    def calculate_buy_order_cost(self, order_price: float) -> FeeCalculation:
        """
        Calculate cost for placing a buy order.
        
        Buy order: use buy_price_max, pay 2.5% setup fee on that price.
        """
        setup_fee_amount = order_price * self.setup_fee
        total_cost = order_price + setup_fee_amount
        
        return FeeCalculation(
            gross_amount=order_price,
            fees=setup_fee_amount,
            net_amount=total_cost,
            fee_breakdown={'setup_fee': setup_fee_amount}
        )
    
    def calculate_instant_sell_revenue(self, market_price: float, premium: bool = None) -> FeeCalculation:
        """
        Calculate revenue for instant sell (sell into buy orders).
        
        Instant sell: sell into buy_price_max, pay sales tax only, no setup fee.
        """
        sales_tax_rate = self.get_sales_tax(premium)
        sales_tax_amount = market_price * sales_tax_rate
        net_revenue = market_price - sales_tax_amount
        
        return FeeCalculation(
            gross_amount=market_price,
            fees=sales_tax_amount,
            net_amount=net_revenue,
            fee_breakdown={'sales_tax': sales_tax_amount}
        )
    
    def calculate_sell_order_revenue(self, order_price: float, premium: bool = None) -> FeeCalculation:
        """
        Calculate revenue for placing a sell order.
        
        Sell order: use sell_price_min, pay sales tax AND 2.5% setup fee.
        """
        sales_tax_rate = self.get_sales_tax(premium)
        sales_tax_amount = order_price * sales_tax_rate
        setup_fee_amount = order_price * self.setup_fee
        
        total_fees = sales_tax_amount + setup_fee_amount
        net_revenue = order_price - total_fees
        
        return FeeCalculation(
            gross_amount=order_price,
            fees=total_fees,
            net_amount=net_revenue,
            fee_breakdown={
                'sales_tax': sales_tax_amount,
                'setup_fee': setup_fee_amount
            }
        )
    
    def calculate_flip_profit(self, src_prices: Dict[str, float], dst_prices: Dict[str, float], 
                            strategy: str = 'fast', premium: bool = None) -> Dict[str, Any]:
        """
        Calculate flip profit for both strategies.
        
        Args:
            src_prices: {'sell_price_min': float, 'buy_price_max': float}
            dst_prices: {'sell_price_min': float, 'buy_price_max': float}
            strategy: 'fast' or 'patient'
            premium: Premium status for tax calculation
        
        Returns:
            Dictionary with profit calculation details
        """
        if strategy == 'fast':
            # Strategy A (Fast): Instant Buy at source, Instant Sell at destination
            buy_calc = self.calculate_instant_buy_cost(src_prices['sell_price_min'])
            sell_calc = self.calculate_instant_sell_revenue(dst_prices['buy_price_max'], premium)
            
        elif strategy == 'patient':
            # Strategy B (Patient): Buy Order at source, Sell Order at destination
            buy_calc = self.calculate_buy_order_cost(src_prices['buy_price_max'])
            sell_calc = self.calculate_sell_order_revenue(dst_prices['sell_price_min'], premium)
            
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        profit_per_unit = sell_calc.net_amount - buy_calc.net_amount
        
        return {
            'strategy': strategy,
            'buy_price': buy_calc.gross_amount,
            'buy_fees': buy_calc.fees,
            'buy_cost': buy_calc.net_amount,
            'sell_price': sell_calc.gross_amount,
            'sell_fees': sell_calc.fees,
            'sell_revenue': sell_calc.net_amount,
            'profit_per_unit': profit_per_unit,
            'buy_fee_breakdown': buy_calc.fee_breakdown,
            'sell_fee_breakdown': sell_calc.fee_breakdown
        }
    
    def calculate_both_strategies(self, src_prices: Dict[str, float], dst_prices: Dict[str, float], 
                                premium: bool = None) -> Dict[str, Dict[str, Any]]:
        """
        Calculate profit for both fast and patient strategies.
        
        Returns:
            Dictionary with 'fast' and 'patient' strategy results
        """
        return {
            'fast': self.calculate_flip_profit(src_prices, dst_prices, 'fast', premium),
            'patient': self.calculate_flip_profit(src_prices, dst_prices, 'patient', premium)
        }
    
    def get_best_strategy(self, src_prices: Dict[str, float], dst_prices: Dict[str, float], 
                         premium: bool = None) -> Dict[str, Any]:
        """
        Get the strategy with the highest profit per unit.
        
        Returns:
            Best strategy result with additional 'is_best' flag
        """
        strategies = self.calculate_both_strategies(src_prices, dst_prices, premium)
        
        fast_profit = strategies['fast']['profit_per_unit']
        patient_profit = strategies['patient']['profit_per_unit']
        
        if fast_profit >= patient_profit:
            best = strategies['fast'].copy()
            best['is_best'] = True
            return best
        else:
            best = strategies['patient'].copy()
            best['is_best'] = True
            return best
    
    def calculate_crafting_costs(self, ingredient_costs: Dict[str, float], 
                               resource_return_rate: float = None,
                               focus_return_rate: float = None,
                               use_focus: bool = None,
                               station_fee: float = 0) -> Dict[str, Any]:
        """
        Calculate effective crafting costs with returns and fees.
        
        Args:
            ingredient_costs: {item_id: cost_per_unit}
            resource_return_rate: Resource return rate (default from config)
            focus_return_rate: Focus return rate (default from config)
            use_focus: Whether to use focus (default from config)
            station_fee: Station fee amount
        
        Returns:
            Dictionary with cost breakdown
        """
        if resource_return_rate is None:
            resource_return_rate = self.config.get('crafting', {}).get('resource_return_rate', 0.15)
        
        if focus_return_rate is None:
            focus_return_rate = self.config.get('crafting', {}).get('focus_return_rate', 0.35)
        
        if use_focus is None:
            use_focus = self.config.get('crafting', {}).get('use_focus', False)
        
        total_ingredient_cost = sum(ingredient_costs.values())
        
        # Apply resource return
        effective_cost_after_resource_return = total_ingredient_cost * (1 - resource_return_rate)
        
        # Apply focus return if enabled
        if use_focus:
            effective_cost_after_focus = effective_cost_after_resource_return * (1 - focus_return_rate)
        else:
            effective_cost_after_focus = effective_cost_after_resource_return
        
        # Add station fee
        total_cost = effective_cost_after_focus + station_fee
        
        return {
            'raw_ingredient_cost': total_ingredient_cost,
            'resource_return_savings': total_ingredient_cost * resource_return_rate,
            'focus_return_savings': effective_cost_after_resource_return * focus_return_rate if use_focus else 0,
            'station_fee': station_fee,
            'effective_cost': total_cost,
            'use_focus': use_focus,
            'resource_return_rate': resource_return_rate,
            'focus_return_rate': focus_return_rate if use_focus else 0
        }

