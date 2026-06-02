"""Service registry abstract interface.

This module defines the abstract interface for service discovery,
supporting Consul, Nacos, and other service registry systems.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jcia.core.entities.remote_call import RemoteEndpoint


@dataclass
class ServiceInfo:
    """Service information from registry.

    Attributes:
        name: Service name
        version: Service version
        host: Service host address
        port: Service port
        metadata: Additional service metadata
    """

    name: str
    version: str | None = None
    host: str | None = None
    port: int | None = None
    metadata: dict | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

    def to_endpoint(self) -> "RemoteEndpoint":
        """Convert to RemoteEndpoint.

        Returns:
            RemoteEndpoint for this service
        """
        from jcia.core.entities.remote_call import RemoteEndpoint

        return RemoteEndpoint(
            service_name=self.name,
            interface=self.name,
            method="",
            url=f"http://{self.host}:{self.port}" if self.host and self.port else None,
            version=self.version,
            group=None,
        )


class ServiceRegistry(ABC):
    """Abstract interface for service discovery.

    Service registries maintain a catalog of available microservices,
    enabling cross-service call chain analysis by resolving service names
    to actual network endpoints.

    Example:
        ```python
        registry = MockServiceRegistry()
        services = registry.list_services()
        endpoint = registry.resolve_service("order-service")
        ```
    """

    @abstractmethod
    def resolve_service(self, service_name: str) -> ServiceInfo | None:
        """Resolve a service name to its network endpoint.

        Args:
            service_name: Name of the service to resolve

        Returns:
            ServiceInfo if service is registered, None otherwise
        """

    @abstractmethod
    def list_services(self) -> list[ServiceInfo]:
        """List all registered services.

        Returns:
            List of all available services
        """

    @abstractmethod
    def get_service_version(self, service_name: str) -> str | None:
        """Get the version of a registered service.

        Args:
            service_name: Name of the service

        Returns:
            Version string if service exists, None otherwise
        """