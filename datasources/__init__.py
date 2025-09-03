"""Data source clients for Albion Trade Optimizer."""

# Delay heavy imports to avoid circular dependencies
__all__ = ["AODPClient", "AODPAPIError"]

def __getattr__(name):  # pragma: no cover - simple lazy loader
    if name in __all__:
        from .aodp import AODPClient, AODPAPIError
        globals().update({"AODPClient": AODPClient, "AODPAPIError": AODPAPIError})
        return globals()[name]
    raise AttributeError(name)
