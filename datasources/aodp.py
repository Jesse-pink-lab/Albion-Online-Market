"""
Albion Online Data Project (AODP) API client.

Handles fetching market price data from the AODP API with rate limiting and error handling.
"""

import logging
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urljoin
import json


class AODPAPIError(Exception):
    """Custom exception for AODP API errors."""
    pass


class AODPClient:
    """Client for the Albion Online Data Project API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize AODP client with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # API configuration
        aodp_config = config.get('aodp', {})
        self.base_url = aodp_config.get(
            'base_url', 'https://www.albion-online-data.com/api/v2/stats'
        )
        self.chunk_size = aodp_config.get('chunk_size', 40)
        self.rate_delay = aodp_config.get('rate_delay_seconds', 1)
        self.timeout = aodp_config.get('timeout_seconds', 30)
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_window_start = time.time()
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AlbionTradeOptimizer/1.0.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })
    
    def _enforce_rate_limit(self):
        """Enforce API rate limits."""
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - self.rate_limit_window_start > 60:
            self.request_count = 0
            self.rate_limit_window_start = current_time
        
        # Check rate limits (180 per minute, 300 per 5 minutes)
        if self.request_count >= 180:
            sleep_time = 60 - (current_time - self.rate_limit_window_start)
            if sleep_time > 0:
                self.logger.info(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                self.request_count = 0
                self.rate_limit_window_start = time.time()
        
        # Enforce minimum delay between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_delay:
            time.sleep(self.rate_delay - time_since_last)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the AODP API with error handling."""
        self._enforce_rate_limit()
        
        # Ensure proper URL joining - base_url should end with / for urljoin to work correctly
        base_url = self.base_url
        if not base_url.endswith('/'):
            base_url += '/'
        
        url = urljoin(base_url, endpoint)
        
        try:
            self.logger.debug(f"Making request to {url} with params {params}")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            self.logger.debug(f"Received {len(data) if isinstance(data, list) else 1} records")
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise AODPAPIError(f"API request failed: {e}")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            raise AODPAPIError(f"Invalid JSON response: {e}")
    
    def get_current_prices(self, item_ids: List[str], locations: Optional[List[str]] = None,
                          qualities: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Get current market prices for items.
        
        Args:
            item_ids: List of item IDs (e.g., ['T4_SWORD', 'T5_SWORD'])
            locations: List of city names (e.g., ['Martlock', 'Lymhurst'])
            qualities: List of quality levels (e.g., [1, 2, 3])
        
        Returns:
            List of price records
        """
        if not item_ids:
            return []
        
        # Default values
        if locations is None:
            locations = self.config.get('cities', [])
        
        if qualities is None:
            qualities = [1]  # Default to normal quality
        
        all_prices = []
        
        # Process items in chunks to avoid URL length limits
        for i in range(0, len(item_ids), self.chunk_size):
            chunk_items = item_ids[i:i + self.chunk_size]
            
            try:
                chunk_prices = self._get_prices_chunk(chunk_items, locations, qualities)
                all_prices.extend(chunk_prices)
                
            except AODPAPIError as e:
                self.logger.error(f"Failed to get prices for chunk {chunk_items}: {e}")
                # Continue with other chunks
                continue
        
        self.logger.info(f"Retrieved {len(all_prices)} price records for {len(item_ids)} items")
        return all_prices
    
    def _get_prices_chunk(self, item_ids: List[str], locations: List[str], 
                         qualities: List[int]) -> List[Dict[str, Any]]:
        """Get prices for a chunk of items."""
        # Build endpoint URL - note: base_url already includes /api/v2/stats
        items_str = ','.join(item_ids)
        endpoint = f"prices/{items_str}.json"
        
        # Build query parameters
        params = {}
        
        if locations:
            params['locations'] = ','.join(locations)
        
        if qualities:
            params['qualities'] = ','.join(map(str, qualities))
        
        # Make API request
        data = self._make_request(endpoint, params)
        
        # Process response data
        processed_prices = []
        
        for price_record in data:
            processed_price = self._process_price_record(price_record)
            if processed_price:
                processed_prices.append(processed_price)
        
        return processed_prices
    
    def _process_price_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single price record from the API."""
        try:
            # Extract data from API response - the field is 'item_id' not 'item_type_id'
            item_id = record.get('item_id')
            city = record.get('city')
            quality = record.get('quality', 1)
            
            # Price data
            sell_price_min = record.get('sell_price_min')
            sell_price_max = record.get('sell_price_max')
            buy_price_min = record.get('buy_price_min')
            buy_price_max = record.get('buy_price_max')
            
            # Timestamps
            sell_price_min_date = record.get('sell_price_min_date')
            buy_price_max_date = record.get('buy_price_max_date')
            
            # Use the most recent timestamp
            observed_at = None
            if sell_price_min_date and buy_price_max_date:
                observed_at = max(sell_price_min_date, buy_price_max_date)
            elif sell_price_min_date:
                observed_at = sell_price_min_date
            elif buy_price_max_date:
                observed_at = buy_price_max_date
            
            # Parse timestamp
            if observed_at:
                try:
                    observed_at_utc = datetime.fromisoformat(observed_at.replace('Z', '+00:00'))
                except ValueError:
                    observed_at_utc = datetime.utcnow()
            else:
                observed_at_utc = datetime.utcnow()
            
            return {
                'item_id': item_id,
                'city': city,
                'quality': quality,
                'sell_price_min': sell_price_min,
                'sell_price_max': sell_price_max,
                'buy_price_min': buy_price_min,
                'buy_price_max': buy_price_max,
                'observed_at_utc': observed_at_utc
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to process price record: {e}")
            return None
    
    def get_historical_prices(self, item_ids: List[str], locations: Optional[List[str]] = None,
                            qualities: Optional[List[int]] = None, 
                            days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get historical price data for items.
        
        Args:
            item_ids: List of item IDs
            locations: List of city names
            qualities: List of quality levels
            days_back: Number of days to look back
        
        Returns:
            List of historical price records
        """
        if not item_ids:
            return []
        
        # Default values
        if locations is None:
            locations = self.config.get('cities', [])
        
        if qualities is None:
            qualities = [1]
        
        all_history = []
        
        # Process items in chunks
        for i in range(0, len(item_ids), self.chunk_size):
            chunk_items = item_ids[i:i + self.chunk_size]
            
            try:
                chunk_history = self._get_history_chunk(chunk_items, locations, qualities, days_back)
                all_history.extend(chunk_history)
                
            except AODPAPIError as e:
                self.logger.error(f"Failed to get history for chunk {chunk_items}: {e}")
                continue
        
        self.logger.info(f"Retrieved {len(all_history)} historical records")
        return all_history
    
    def _get_history_chunk(self, item_ids: List[str], locations: List[str],
                          qualities: List[int], days_back: int) -> List[Dict[str, Any]]:
        """Get historical data for a chunk of items."""
        # Build endpoint URL
        items_str = ','.join(item_ids)
        endpoint = f"history/{items_str}.json"
        
        # Calculate date range
        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Build query parameters
        params = {
            'date': start_date.strftime('%m-%d-%Y'),
            'end_date': end_date.strftime('%m-%d-%Y'),
            'time-scale': 24  # Daily data
        }
        
        if locations:
            params['locations'] = ','.join(locations)
        
        if qualities:
            params['qualities'] = ','.join(map(str, qualities))
        
        # Make API request
        data = self._make_request(endpoint, params)
        
        # Process response data
        processed_history = []
        
        for history_record in data:
            processed_record = self._process_history_record(history_record)
            if processed_record:
                processed_history.append(processed_record)
        
        return processed_history
    
    def _process_history_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single historical price record."""
        try:
            # Extract data from API response
            item_id = record.get('item_type_id')
            location = record.get('location')
            quality = record.get('quality', 1)
            
            # Price data (historical data typically has avg_price)
            avg_price = record.get('avg_price')
            item_count = record.get('item_count', 0)
            
            # Timestamp
            timestamp_str = record.get('timestamp')
            if timestamp_str:
                try:
                    observed_at_utc = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    observed_at_utc = datetime.utcnow()
            else:
                observed_at_utc = datetime.utcnow()
            
            return {
                'item_id': item_id,
                'city': location,
                'quality': quality,
                'avg_price': avg_price,
                'item_count': item_count,
                'observed_at_utc': observed_at_utc
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to process history record: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test connection to the AODP API."""
        try:
            # Try to get prices for a common item
            test_data = self.get_current_prices(['T4_SWORD'], ['Martlock'], [1])
            self.logger.info("AODP API connection test successful")
            return True
            
        except Exception as e:
            self.logger.error(f"AODP API connection test failed: {e}")
            return False
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get API server status information."""
        try:
            # Make a simple request to check server status
            response = self.session.get(self.base_url.replace('/stats', ''), timeout=10)
            
            return {
                'status': 'online' if response.status_code == 200 else 'error',
                'status_code': response.status_code,
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'base_url': self.base_url
            }
            
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e),
                'base_url': self.base_url
            }
    
    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()

