"""Mock service registry for testing and development.

Provides a mock implementation of ServiceRegistry for local development
and testing without requiring actual Consul/Nacos infrastructure.
"""

import logging

from jcia.core.interfaces.service_registry import (
    ServiceInfo,
    ServiceRegistry,
)

logger = logging.getLogger(__name__)


class MockServiceRegistry(ServiceRegistry):
    """Mock service registry for testing and development.

    Provides a simple in-memory service catalog for local development
    without requiring actual service registry infrastructure.

    Example:
        ```python
        registry = MockServiceRegistry()
        registry.register_service(ServiceInfo(
            name="order-service",
            version="1.0.0",
            host="localhost",
            port=8080
        ))
        info = registry.resolve_service("order-service")
        ```
    """

    def __init__(self) -> None:
        """Initialize the mock registry."""
        self._services: dict[str, ServiceInfo] = {}

    def register_service(self, service: ServiceInfo) -> None:
        """Register a service in the mock registry.

        Args:
            service: Service information to register
        """
        self._services[service.name] = service
        logger.debug(f"Registered service: {service.name}")

    def resolve_service(self, service_name: str) -> ServiceInfo | None:
        """Resolve a service name to its network endpoint.

        Args:
            service_name: Name of the service to resolve

        Returns:
            ServiceInfo if service is registered, None otherwise
        """
        return self._services.get(service_name)

    def list_services(self) -> list[ServiceInfo]:
        """List all registered services.

        Returns:
            List of all available services
        """
        return list(self._services.values())

    def get_service_version(self, service_name: str) -> str | None:
        """Get the version of a registered service.

        Args:
            service_name: Name of the service

        Returns:
            Version string if service exists, None otherwise
        """
        service = self._services.get(service_name)
        return service.version if service else None