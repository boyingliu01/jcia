"""Tests for SkyWalkingCallChainAdapter.

This module tests the SkyWalking call chain adapter.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from jcia.adapters.tools.skywalking_call_chain_adapter import (
    DubboCall,
    ServiceEndpoint,
    SkyWalkingCallChainAdapter,
)
from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainDirection,
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
        service, endpoint = adapter._parse_method_to_endpoint("GET:/api/users/{id}")
        # For strings without dots (no "."), implementation returns (method, method)
        assert service == "GET:/api/users/{id}"
        assert endpoint == "GET:/api/users/{id}"

    def test_parse_method_to_endpoint_dubbo(self) -> None:
        """Test parsing Dubbo method to endpoint."""
        adapter = SkyWalkingCallChainAdapter()
        service, endpoint = adapter._parse_method_to_endpoint("com.example.UserService.getUser")
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


@pytest.fixture()
def adapter() -> SkyWalkingCallChainAdapter:
    """Provide a default-configured adapter instance."""
    return SkyWalkingCallChainAdapter()


class TestExecuteGraphqlExtended:
    """Extended coverage for the _execute_graphql network boundary."""

    @patch("requests.post")
    def test_includes_token_header(self, mock_post: MagicMock) -> None:
        """API token is sent as SW-TOKEN header when configured."""
        adapter = SkyWalkingCallChainAdapter(api_token="secret-token")
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"ok": True}}
        mock_post.return_value = mock_response

        adapter._execute_graphql("query { ok }", {"a": 1})

        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["SW-TOKEN"] == "secret-token"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["json"] == {"query": "query { ok }", "variables": {"a": 1}}

    @patch("requests.post")
    def test_no_token_header_when_unset(self, mock_post: MagicMock) -> None:
        """No SW-TOKEN header when token is not configured."""
        adapter = SkyWalkingCallChainAdapter()
        mock_response = Mock()
        mock_response.json.return_value = {"data": {}}
        mock_post.return_value = mock_response

        adapter._execute_graphql("query { ok }", {})

        _, kwargs = mock_post.call_args
        assert "SW-TOKEN" not in kwargs["headers"]

    @patch("requests.post")
    def test_raises_on_graphql_errors_key(self, mock_post: MagicMock) -> None:
        """A GraphQL 'errors' payload is surfaced as RuntimeError."""
        adapter = SkyWalkingCallChainAdapter()
        mock_response = Mock()
        mock_response.json.return_value = {"errors": [{"message": "boom"}]}
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="boom"):
            adapter._execute_graphql("query { x }", {})

    @patch("requests.post")
    def test_returns_empty_when_no_data_key(self, mock_post: MagicMock) -> None:
        """Missing 'data' key yields an empty dict."""
        adapter = SkyWalkingCallChainAdapter()
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        assert adapter._execute_graphql("query { x }", {}) == {}


class TestIdentifyCallTypeFromSpan:
    """Branch coverage for _identify_call_type_from_span."""

    def test_dubbo_by_component(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {"component": "Dubbo", "tags": [{"key": "dubbo.interface", "value": "com.I"}]}
        assert adapter._identify_call_type_from_span(span) == ("dubbo", "com.I")

    def test_dubbo_by_tag(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {"component": "", "tags": [{"key": "dubbo.interface", "value": "com.Tag"}]}
        assert adapter._identify_call_type_from_span(span) == ("dubbo", "com.Tag")

    def test_grpc_by_component(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {"component": "gRPC", "peer": "grpc-svc", "tags": []}
        assert adapter._identify_call_type_from_span(span) == ("grpc", "grpc-svc")

    def test_grpc_by_url_keyword(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {"component": "", "peer": "p", "tags": [{"key": "url", "value": "http://RPC/x"}]}
        assert adapter._identify_call_type_from_span(span) == ("grpc", "p")

    def test_rest_by_protocol(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {
            "component": "",
            "tags": [
                {"key": "protocol", "value": "HTTP/1.1"},
                {"key": "url", "value": "/api/x"},
            ],
        }
        assert adapter._identify_call_type_from_span(span) == ("rest", "/api/x")

    def test_rest_by_spring_component(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {"component": "Spring", "tags": [{"key": "url", "value": "/spring"}]}
        assert adapter._identify_call_type_from_span(span) == ("rest", "/spring")

    def test_database(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {"component": "", "tags": [{"key": "db.type", "value": "mysql"}]}
        assert adapter._identify_call_type_from_span(span) == ("database", "mysql")

    def test_message_queue(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {"component": "", "tags": [{"key": "mq.type", "value": "kafka"}]}
        assert adapter._identify_call_type_from_span(span) == ("message_queue", "kafka")

    def test_local_with_peer(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {"component": "", "peer": "local-peer", "tags": []}
        assert adapter._identify_call_type_from_span(span) == ("local", "local-peer")

    def test_local_without_peer(self, adapter: SkyWalkingCallChainAdapter) -> None:
        span = {"component": "", "tags": []}
        assert adapter._identify_call_type_from_span(span) == ("local", "")


class TestPureGraphHelpers:
    """Coverage for pure graph-construction helpers."""

    def test_create_empty_graph(self, adapter: SkyWalkingCallChainAdapter) -> None:
        graph = adapter._create_empty_graph("com.example.Svc.m", 5)
        assert graph.root.class_name == "Svc"
        assert graph.root.method_name == "m"
        assert graph.direction == CallChainDirection.BOTH
        assert graph.max_depth == 5
        assert graph.total_nodes == 1
        assert graph.root.children == []

    def test_build_full_graph_from_topology_empty(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        graph = adapter._build_full_graph_from_topology({})
        assert graph.root.class_name == "root"
        assert graph.direction == CallChainDirection.BOTH
        assert graph.total_nodes == 0
        assert graph.root.children == []

    def test_build_full_graph_from_topology_links(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        topology = {
            "links": [
                {"sourceId": "svc-a", "targetId": "svc-b"},
                {"sourceId": "svc-b", "targetId": "svc-c"},
            ]
        }
        graph = adapter._build_full_graph_from_topology(topology)
        assert graph.total_nodes == 2
        assert len(graph.root.children) == 2
        first = graph.root.children[0]
        assert first.class_name == "svc-b"
        assert first.metadata == {"link_type": "service_dependency", "source": "svc-a"}

    def test_identify_dubbo_calls_empty(self, adapter: SkyWalkingCallChainAdapter) -> None:
        assert adapter._identify_dubbo_calls({}) == {}
        assert adapter._identify_dubbo_calls({"traces": []}) == {}

    def test_identify_dubbo_calls_collects_spans(self, adapter: SkyWalkingCallChainAdapter) -> None:
        traces_data = {
            "traces": [
                {
                    "segments": [
                        {
                            "serviceCode": "order-service",
                            "spans": [
                                {
                                    "spanId": "7",
                                    "component": "Dubbo",
                                    "peer": "user-service",
                                    "tags": [
                                        {"key": "dubbo.interface", "value": "com.example.User"},
                                        {"key": "dubbo.method", "value": "getUser"},
                                        {"key": "dubbo.version", "value": "1.0.0"},
                                        {"key": "dubbo.group", "value": "g1"},
                                    ],
                                },
                                {"spanId": "8", "component": "Spring", "tags": []},
                            ],
                        }
                    ]
                }
            ]
        }
        calls = adapter._identify_dubbo_calls(traces_data)
        assert set(calls.keys()) == {"7"}
        call = calls["7"]
        assert isinstance(call, DubboCall)
        assert call.interface == "com.example.User"
        assert call.method == "getUser"
        assert call.version == "1.0.0"
        assert call.group == "g1"
        assert call.consumer == "order-service"
        assert call.provider == "user-service"


class TestBuildGraphsFromTraces:
    """Coverage for _build_upstream_graph / _build_downstream_graph / _add_upstream_nodes."""

    def test_build_upstream_graph_empty(self, adapter: SkyWalkingCallChainAdapter) -> None:
        graph = adapter._build_upstream_graph({}, "com.example.Svc.m", 10)
        assert graph.direction == CallChainDirection.UPSTREAM
        assert graph.total_nodes == 1
        assert graph.root.children == []

    def test_build_upstream_graph_adds_parented_non_entry_span(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        traces_data = {
            "traces": [
                {
                    "segments": [
                        {
                            "spans": [
                                {
                                    "spanId": "1",
                                    "parentSpanId": "0",
                                    "peer": "user-service",
                                    "operationName": "getUser",
                                    "type": "Exit",
                                    "component": "Dubbo",
                                    "tags": [{"key": "dubbo.interface", "value": "com.U"}],
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        graph = adapter._build_upstream_graph(traces_data, "com.example.Svc.m", 10)
        assert graph.direction == CallChainDirection.UPSTREAM
        assert graph.total_nodes == 2
        assert len(graph.root.children) == 1
        child = graph.root.children[0]
        assert child.class_name == "user-service"
        assert child.method_name == "getUser"
        assert child.metadata["call_type"] == "dubbo"
        assert child.metadata["component"] == "Dubbo"
        assert child.metadata["span_id"] == "1"

    def test_build_upstream_graph_skips_entry_and_root_spans(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        traces_data = {
            "traces": [
                {
                    "segments": [
                        {
                            "spans": [
                                {
                                    "spanId": "1",
                                    "parentSpanId": "0",
                                    "type": "Entry",
                                    "peer": "a",
                                    "operationName": "op-a",
                                    "component": "",
                                    "tags": [],
                                },
                                {
                                    "spanId": "2",
                                    "type": "Exit",
                                    "peer": "b",
                                    "operationName": "op-b",
                                    "component": "",
                                    "tags": [],
                                },
                            ]
                        }
                    ]
                }
            ]
        }
        graph = adapter._build_upstream_graph(traces_data, "Svc.m", 10)
        assert graph.root.children == []
        assert graph.total_nodes == 1

    def test_add_upstream_nodes_respects_max_depth(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        root = CallChainNode(class_name="R", method_name="m")
        current = CallChainNode(class_name="C", method_name="m")
        spans = [
            {
                "spanId": "2",
                "parentSpanId": "1",
                "peer": "p",
                "operationName": "o",
                "component": "",
                "tags": [],
            }
        ]
        adapter._add_upstream_nodes(root, current, spans, "1", depth=5, max_depth=5)
        assert current.children == []

    def test_add_upstream_nodes_appends_matching_child(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        root = CallChainNode(class_name="R", method_name="m")
        current = CallChainNode(class_name="C", method_name="m")
        spans = [
            {
                "spanId": "2",
                "parentSpanId": "1",
                "peer": "p",
                "operationName": "o",
                "component": "Dubbo",
                "tags": [],
            }
        ]
        adapter._add_upstream_nodes(root, current, spans, "1", depth=1, max_depth=10)
        assert len(current.children) == 1
        child = current.children[0]
        assert child.class_name == "p"
        assert child.metadata["call_type"] == "dubbo"

    def test_build_downstream_graph_empty(self, adapter: SkyWalkingCallChainAdapter) -> None:
        graph = adapter._build_downstream_graph({}, "Svc.m", 10)
        assert graph.direction == CallChainDirection.DOWNSTREAM
        assert graph.total_nodes == 1
        assert graph.root.children == []

    def test_build_downstream_graph_only_exit_spans(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        traces_data = {
            "traces": [
                {
                    "segments": [
                        {
                            "spans": [
                                {
                                    "spanId": "1",
                                    "type": "Exit",
                                    "peer": "db",
                                    "operationName": "query",
                                    "component": "",
                                    "tags": [{"key": "db.type", "value": "mysql"}],
                                },
                                {
                                    "spanId": "2",
                                    "type": "Entry",
                                    "peer": "web",
                                    "operationName": "handle",
                                    "component": "",
                                    "tags": [],
                                },
                            ]
                        }
                    ]
                }
            ]
        }
        graph = adapter._build_downstream_graph(traces_data, "Svc.m", 10)
        assert graph.direction == CallChainDirection.DOWNSTREAM
        assert graph.total_nodes == 2
        assert len(graph.root.children) == 1
        child = graph.root.children[0]
        assert child.class_name == "db"
        assert child.metadata["call_type"] == "database"


class TestAnalyzeOrchestration:
    """Coverage for public analyze_* / build_full_graph / get_service_topology."""

    def test_analyze_upstream_success(self, adapter: SkyWalkingCallChainAdapter) -> None:
        with patch.object(adapter, "_execute_graphql", return_value={"getTrace": {"traces": []}}):
            graph = adapter.analyze_upstream("com.example.Svc.m", 10)
        assert graph.direction == CallChainDirection.UPSTREAM
        assert graph.total_nodes == 1

    def test_analyze_upstream_exception_returns_empty(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("net down")):
            graph = adapter.analyze_upstream("com.example.Svc.m", 10)
        assert graph.direction == CallChainDirection.BOTH
        assert graph.total_nodes == 1
        assert graph.root.children == []

    def test_analyze_downstream_success(self, adapter: SkyWalkingCallChainAdapter) -> None:
        with patch.object(adapter, "_execute_graphql", return_value={"getTrace": {"traces": []}}):
            graph = adapter.analyze_downstream("com.example.Svc.m", 10)
        assert graph.direction == CallChainDirection.DOWNSTREAM

    def test_analyze_downstream_exception_returns_empty(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("net down")):
            graph = adapter.analyze_downstream("Svc.m", 10)
        assert graph.direction == CallChainDirection.BOTH
        assert graph.total_nodes == 1

    def test_analyze_both_directions_returns_pair(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        with patch.object(adapter, "_execute_graphql", return_value={"getTrace": {"traces": []}}):
            upstream, downstream = adapter.analyze_both_directions("com.example.Svc.m", 10)
        assert upstream.direction == CallChainDirection.UPSTREAM
        assert downstream.direction == CallChainDirection.DOWNSTREAM

    def test_build_full_graph_success(self, adapter: SkyWalkingCallChainAdapter) -> None:
        topology = {"links": [{"sourceId": "a", "targetId": "b"}]}
        with patch.object(adapter, "_execute_graphql", return_value={"topology": topology}):
            graph = adapter.build_full_graph()
        assert graph.total_nodes == 1
        assert len(graph.root.children) == 1

    def test_build_full_graph_exception_returns_empty(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("down")):
            graph = adapter.build_full_graph()
        assert graph.root.class_name == "root"
        assert graph.total_nodes == 1

    def test_get_service_topology_success(self, adapter: SkyWalkingCallChainAdapter) -> None:
        payload = {"services": [{"key": "1", "label": "svc"}], "topology": {"links": []}}
        with patch.object(adapter, "_execute_graphql", return_value=payload):
            result = adapter.get_service_topology()
        assert result == {"services": [{"key": "1", "label": "svc"}], "topology": {"links": []}}

    def test_get_service_topology_exception_returns_empty(
        self, adapter: SkyWalkingCallChainAdapter
    ) -> None:
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("down")):
            result = adapter.get_service_topology()
        assert result == {"services": [], "topology": {}}
