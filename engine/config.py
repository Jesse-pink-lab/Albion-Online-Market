"""
Configuration manager for Albion Trade Optimizer.

Handles loading and managing application configuration from YAML files.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
from utils.paths import CONFIG_PATH, DB_PATH, LOG_DIR


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        self.logger = logging.getLogger(__name__)
        
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = CONFIG_PATH
        
        self._config = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            if not self.config_path.exists():
                self.logger.warning(f"Config file not found at {self.config_path}, using defaults")
                self._config = self.get_default_config()
                return self._config
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Merge with defaults to ensure all required keys exist
            default_config = self.get_default_config()
            merged_config = self._merge_configs(default_config, config)
            merged_config = self._migrate_config(merged_config)

            self._config = merged_config
            self.logger.info(f"Configuration loaded from {self.config_path}")
            
            return self._config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.logger.info("Using default configuration")
            return self.get_default_config()
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration, loading if necessary."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)."""
        config = self.get_config()
        
        # Support dot notation for nested keys
        keys = key.split('.')
        value = config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value by key (supports dot notation)."""
        config = self.get_config()
        
        # Support dot notation for nested keys
        keys = key.split('.')
        current = config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the value
        current[keys[-1]] = value
    
    def save_config(self, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        """Save configuration to YAML file."""
        if config is not None:
            self._config = config
        
        if not self._config:
            self.logger.warning("No configuration to save")
            return
        
        save_path = Path(config_path) if config_path else self.config_path
        
        try:
            tmp_path = save_path.with_suffix(save_path.suffix + ".tmp")
            with open(tmp_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, save_path)

            self.logger.info(f"Configuration saved to {save_path}")

        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration values."""
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'cities': [
                "Martlock",
                "Lymhurst",
                "Bridgewatch",
                "Fort Sterling",
                "Thetford",
                "Caerleon",
                "Black Market"
            ],
            'freshness': {
                'max_age_hours': 24
            },
            'fees': {
                'sales_tax_premium': 0.04,
                'sales_tax_no_premium': 0.08,
                'setup_fee': 0.025
            },
            'premium_enabled': True,
            'fetch_all_items': True,
            'items_per_request': 150,
            'max_concurrency': 4,
            'global_rate_per_sec': 2.0,
            'global_rate_capacity': 4,
            'cache_ttl_sec': 120,
            'city_batch_size': 3,
            'only_visible_first': True,
            'risk': {
                'caerleon_high_risk': True
            },
            'crafting': {
                'resource_return_rate': 0.15,
                'use_focus': False,
                'focus_return_rate': 0.35,
                'default_station_fee': 0
            },
            'aodp': {
                'base_url': "https://www.albion-online-data.com/api/v2/stats",
                'server': 'europe',
                'chunk_size': 40,
                'rate_delay_seconds': 1,
                'timeout_seconds': 30
            },
            'uploader': {
                'enabled': True,
                'ingest_base': "http+pow://albion-online-data.com",
                'enable_websocket': True,
                'interface': None,
                'no_cpu_limit': False,
                'binary_path_win': None,
                'binary_path_linux': None,
            },
            'client': {
                'flags': [],
            },
            'app': {
                'name': "Albion Trade Optimizer",
                'version': "1.0.0",
                'author': "Manus AI",
                'description': "Trade optimization tool for Albion Online"
            },
            'database': {
                'path': str(DB_PATH),
                'backup_count': 5
            },
            'logging': {
                'level': "INFO",
                'file': str(LOG_DIR / "app.log"),
                'max_size_mb': 10,
                'backup_count': 5
            },
            'ui': {
                'theme': "light",
                'window_width': 1200,
                'window_height': 800,
                'refresh_interval_seconds': 300
            }
        }
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user configuration with defaults."""
        result = default.copy()

        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _migrate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Handle legacy configuration keys."""
        app_cfg = config.get('app', {})
        logging_cfg = config.setdefault('logging', {})
        if 'log_level' in app_cfg and 'level' not in logging_cfg:
            logging_cfg['level'] = app_cfg['log_level']
        app_cfg.pop('log_level', None)
        return config
    
    def get_cities(self) -> List[str]:
        """Get list of supported cities."""
        return self.get('cities', [])
    
    def get_max_age_hours(self) -> int:
        """Get maximum age for price data in hours."""
        return self.get('freshness.max_age_hours', 24)
    
    def get_sales_tax(self, premium: bool = None) -> float:
        """Get sales tax rate based on premium status."""
        if premium is None:
            premium = self.get('premium_enabled', True)
        
        if premium:
            return self.get('fees.sales_tax_premium', 0.04)
        else:
            return self.get('fees.sales_tax_no_premium', 0.08)
    
    def get_setup_fee(self) -> float:
        """Get order setup fee rate."""
        return self.get('fees.setup_fee', 0.025)
    
    def is_caerleon_high_risk(self) -> bool:
        """Check if Caerleon routes are considered high risk."""
        return self.get('risk.caerleon_high_risk', True)
    
    def get_resource_return_rate(self) -> float:
        """Get resource return rate for crafting."""
        return self.get('crafting.resource_return_rate', 0.15)
    
    def get_focus_return_rate(self) -> float:
        """Get focus return rate for crafting."""
        return self.get('crafting.focus_return_rate', 0.35)
    
    def is_focus_enabled(self) -> bool:
        """Check if focus is enabled for crafting."""
        return self.get('crafting.use_focus', False)
    
    def get_aodp_config(self) -> Dict[str, Any]:
        """Get AODP API configuration."""
        return self.get('aodp', {})
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        config = self.get_config()
        
        # Validate required sections
        required_sections = ['cities', 'fees', 'aodp']
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Validate cities
        cities = self.get_cities()
        if not cities:
            errors.append("No cities configured")
        
        # Validate fee rates
        sales_tax_premium = self.get_sales_tax(True)
        sales_tax_no_premium = self.get_sales_tax(False)
        setup_fee = self.get_setup_fee()
        
        if not (0 <= sales_tax_premium <= 1):
            errors.append("Sales tax (premium) must be between 0 and 1")
        
        if not (0 <= sales_tax_no_premium <= 1):
            errors.append("Sales tax (no premium) must be between 0 and 1")
        
        if not (0 <= setup_fee <= 1):
            errors.append("Setup fee must be between 0 and 1")
        
        # Validate AODP config
        aodp_config = self.get_aodp_config()
        if 'base_url' not in aodp_config:
            errors.append("AODP base_url not configured")
        if 'server' not in aodp_config:
            errors.append("AODP server not configured")

        return errors

    def get_uploader_config(self):
        cfg = self._config.get('uploader', {}) if self._config else {}
        return {
            'enabled': cfg.get('enabled', True),
            'ingest_base': cfg.get('ingest_base', 'http+pow://albion-online-data.com'),
            'enable_websocket': cfg.get('enable_websocket', True),
            'interface': cfg.get('interface', None),
            'no_cpu_limit': cfg.get('no_cpu_limit', False),
            'binary_path_win': cfg.get('binary_path_win', None),
            'binary_path_linux': cfg.get('binary_path_linux', None),
        }

