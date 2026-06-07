"""Transform Context Resolver payloads into production ML pipeline inputs."""

from ml.adapters.demand_adapter import adapt_demand_payload
from ml.adapters.eta_adapter import adapt_eta_payload
from ml.adapters.route_adapter import adapt_route_payload

__all__ = [
    "adapt_demand_payload",
    "adapt_eta_payload",
    "adapt_route_payload",
]
