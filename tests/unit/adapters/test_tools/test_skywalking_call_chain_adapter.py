"""Tests for SkyWalkingCallChainAdapter.

This module tests the SkyWalking call chain adapter.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime

from jcia.adapters.tools.skywalking_call_chain_adapter import (
    DubboCall,
    ServiceEndpoint,
    SkyWalkingCallChainAdapter,
)
from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)


class TestDubboCall:
    """Tests for DubboCall dataclass."""

    def test_create_dubbo_call(self) -> None:
        """Test creating a Dubbo call."""
        call = DubboCall(
            interface="com.example.UserService",
            method="getUser",
            version="1.0.0",
            group="default",
            consumer="order-service",
            provider="user-service",
        )
        assert call.interface == "com.example.UserService"
        assert call.method == "getUser"
        assert call.version == "1.0.0"
        assert call.group == "default"
        assert call.consumer == "order-service"
        assert call.provider == "user-service"

    def test_dubbo_call_defaults(self) -> None:
        """Test DubboCall default values."""
        call = DubboCall(
            interface="com.example.TestService",
            method="testMethod",
        )
        assert call.version is None
        assert call.group is None
        assert call.consumer == ""
        assert call.provider == ""


class TestServiceEndpoint:
    """Tests for ServiceEndpoint dataclass."""

    def test_create_endpoint(self) -> None:
        """Test creating a service endpoint."""
        endpoint = ServiceEndpoint(
            service_id="svc-123",
            service_name="user-service",
            endpoint_name="/api/users",
            type="HTTP",
            tags={"env": "prod", "region": "us-east-1"},
        )
        assert endpoint.service_id == "svc-123"
        assert endpoint.service_name == "user-service"
        assert endpoint.endpoint_name == "/api/users"
        assert endpoint.type == "HTTP"
        assert endpoint.tags == {"env": "prod", "region": "us-east-1"}

    def test_endpoint_default_tags(self) -> None:
        """Test ServiceEndpoint default tags."""
        endpoint = ServiceEndpoint(
            service_id="svc-456",
            service_name="order-service",
            endpoint_name="processOrder",
            type="DUBBO",
        )
        assert endpoint.tags == {}


class TestSkyWalkingCallChainAdapter:
    """Tests for SkyWalkingCallChainAdapter."""

    def test_initialization_defaults(self) -> None:
        """Test adapter initialization with default values."""
        adapter = SkyWalkingCallChainAdapter()
        assert adapter._oap_server == "http://localhost:12800"
        assert adapter._token is None
        assert adapter._time_range == 7
        assert adapter._timeout == 30
        assert adapter._graphql_endpoint == "http://localhost:12800/graphql"

    def test_initialization_custom_values(self) -> None:
        """Test adapter initialization with custom values."""
        adapter = SkyWalkingCallChainAdapter(
            oap_server="http://skywalking.example.com:12800",
            api_token="test-token-123",
            time_range=14,
            timeout=60,
        )
        assert adapter._oap_server == "http://skywalking.example.com:12800"
        assert adapter._token == "test-token-123"
        assert adapter._time_range == 14
        assert adapter._timeout == 60
        assert adapter._graphql_endpoint == "http://skywalking.example.com:12800/graphql"

    def test_initialization_trailing_slash(self) -> None:
        """Test that trailing slash is removed from OAP server URL."""
        adapter = SkyWalkingCallChainAdapter(oap_server="http://skywalking:12800/")
        assert adapter._oap_server == "http://skywalking:12800"
        assert adapter._graphql_endpoint == "http://skywalking:12800/graphql"

    def test_analyzer_type(self) -> None:
        """Test that analyzer type is DYNAMIC."""
        adapter = SkyWalkingCallChainAdapter()
        assert adapter.analyzer_type == AnalyzerType.DYNAMIC

    def test_supports_cross_service(self) -> None:
        """Test that cross-service analysis is supported."""
        adapter = SkyWalkingCallChainAdapter()
        assert adapter.supports_cross_service is True

    def test_parse_method_to_endpoint_http(self) -> None:
        """Test parsing HTTP method to endpoint."""
        adapter = SkyWalkingCallChainAdapter()
        service, endpoint = adapter._parse_method_to_endpoint(
            "GET:/api/users/{id}"
        )
        # For strings without dots (no "."), implementation returns (method, method)
        assert service == "GET:/api/users/{id}"
        assert endpoint == "GET:/api/users/{id}"

    def test_parse_method_to_endpoint_dubbo(self) -> None:
        """Test parsing Dubbo method to endpoint."""
        adapter = SkyWalkingCallChainAdapter()
        service, endpoint = adapter._parse_method_to_endpoint(
            "com.example.UserService.getUser"
        )
        # Implementation splits by dots and returns last segment as service
        assert service == "UserService"
        assert endpoint == "getUser"

    def test_parse_method_to_endpoint_simple(self) -> None:
        """Test parsing simple method name."""
        adapter = SkyWalkingCallChainAdapter()
        service, endpoint = adapter._parse_method_to_endpoint("processOrder")
        # Implementation returns full string as service if no dots
        assert service == "processOrder"
        assert endpoint == "processOrder"


class TestSkyWalkingErrorHandling:
    """Tests for error handling in SkyWalking adapter."""

    @patch("requests.post")
    def test_execute_graphql_success(self, mock_post: MagicMock) -> None:
        """Test successful GraphQL execution."""
        adapter = SkyWalkingCallChainAdapter()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"testQuery": "result"}}
        mock_post.return_value = mock_response

        result = adapter._execute_graphql("query { testQuery }", {})

        # Implementation returns data.get("data", {}) so returns inner data dict
        assert result == {"testQuery": "result"}
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_execute_graphql_http_error(self, mock_post: MagicMock) -> None:
        """Test GraphQL execution with HTTP error raises RuntimeError."""
        adapter = SkyWalkingCallChainAdapter()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        # raise_for_status will raise an HTTPError
        import requests
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        # Implementation raises RuntimeError on HTTP errors
        with pytest.raises(RuntimeError):
            adapter._execute_graphql("query { testQuery }", {})

    @patch("requests.post")
    def test_execute_graphql_exception(self, mock_post: MagicMock) -> None:
        """Test GraphQL execution with exception raises RuntimeError."""
        from requests import RequestException

        adapter = SkyWalkingCallChainAdapter()
        # Use RequestException which is what the implementation catches
        mock_post.side_effect = RequestException("Connection refused")

        # Implementation raises RuntimeError on exceptions
        with pytest.raises(RuntimeError):
            adapter._execute_graphql("query { testQuery }", {})

