"""SkyWalking APM 适配器单元测试.

覆盖 SkyWalkingAdapter 的 GraphQL 执行、endpoint 统计处理、测试推荐、
异常分析、服务健康、性能趋势与推荐导出等逻辑。网络边界统一通过 mock
``_execute_graphql`` 或 ``requests.post`` 隔离，保证测试 hermetic。
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from jcia.adapters.ai.skywalking_adapter import (
    DEFAULT_OAP_SERVER,
    SkyWalkingAdapter,
)


@pytest.fixture()
def adapter() -> SkyWalkingAdapter:
    """返回默认配置的适配器实例."""
    return SkyWalkingAdapter()


class TestSkyWalkingAdapterInit:
    """初始化相关测试."""

    def test_default_config(self, adapter: SkyWalkingAdapter) -> None:
        """默认配置应指向本地 OAP 并拼接 graphql 端点."""
        assert adapter._oap_server == DEFAULT_OAP_SERVER
        assert adapter._graphql_endpoint == f"{DEFAULT_OAP_SERVER}/graphql"
        assert adapter._token is None
        assert adapter._timeout == 30

    def test_strips_trailing_slash(self) -> None:
        """OAP 地址末尾斜杠应被去除，避免双斜杠端点."""
        adapter = SkyWalkingAdapter(oap_server="http://oap:12800/")
        assert adapter._oap_server == "http://oap:12800"
        assert adapter._graphql_endpoint == "http://oap:12800/graphql"

    def test_custom_token_and_timeout(self) -> None:
        """自定义 token 与超时应被保存."""
        adapter = SkyWalkingAdapter(api_token="secret-token", timeout=5)
        assert adapter._token == "secret-token"
        assert adapter._timeout == 5


class TestExecuteGraphql:
    """_execute_graphql 网络边界测试."""

    def test_success_returns_data(self, adapter: SkyWalkingAdapter) -> None:
        """成功响应应返回 data 字段内容."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"services": []}}
        mock_response.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = adapter._execute_graphql("query {}", {})

        assert result == {"services": []}
        mock_post.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    def test_adds_token_header_when_configured(self) -> None:
        """配置 token 时请求头应包含 SW-TOKEN."""
        adapter = SkyWalkingAdapter(api_token="abc123")
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {}}
        mock_response.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_response) as mock_post:
            adapter._execute_graphql("query {}", {})

        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["SW-TOKEN"] == "abc123"
        assert kwargs["headers"]["Content-Type"] == "application/json"

    def test_no_token_header_by_default(self, adapter: SkyWalkingAdapter) -> None:
        """未配置 token 时请求头不应包含 SW-TOKEN."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {}}
        mock_response.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_response) as mock_post:
            adapter._execute_graphql("query {}", {})

        _, kwargs = mock_post.call_args
        assert "SW-TOKEN" not in kwargs["headers"]

    def test_graphql_errors_raise_runtime_error(self, adapter: SkyWalkingAdapter) -> None:
        """响应含 errors 时应抛出 RuntimeError 并拼接错误消息."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "errors": [{"message": "boom"}, {"message": "bang"}],
        }
        mock_response.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_response), pytest.raises(
            RuntimeError, match="boom; bang"
        ):
            adapter._execute_graphql("query {}", {})

    def test_request_exception_wrapped(self, adapter: SkyWalkingAdapter) -> None:
        """底层 RequestException 应被包装为 RuntimeError."""
        with patch(
            "requests.post", side_effect=requests.exceptions.ConnectionError("down")
        ), pytest.raises(RuntimeError, match="Failed to execute GraphQL query"):
            adapter._execute_graphql("query {}", {})


class TestFindRelatedEndpoints:
    """_find_related_endpoints 测试."""

    def test_extracts_endpoint_ids(self, adapter: SkyWalkingAdapter) -> None:
        """应从方法名提取关键词并返回 endpoint id 列表."""
        with patch.object(
            adapter,
            "_execute_graphql",
            return_value={"endpoints": [{"key": "ep1"}, {"key": "ep2"}]},
        ) as mock_gql:
            result = adapter._find_related_endpoints(["com.demo.Service.doWork"])

        assert result == ["ep1", "ep2"]
        # 校验关键词包含类名与方法名
        _, kwargs = mock_gql.call_args
        variables = kwargs.get("variables") or mock_gql.call_args[0][1]
        assert "Service" in variables["endpoints"]
        assert "doWork" in variables["endpoints"]

    def test_skips_methods_with_fewer_than_two_parts(self, adapter: SkyWalkingAdapter) -> None:
        """单段方法名不产生关键词，endpoints 为空."""
        with patch.object(adapter, "_execute_graphql", return_value={"endpoints": []}) as mock_gql:
            result = adapter._find_related_endpoints(["standalone"])

        assert result == []
        variables = mock_gql.call_args[0][1]
        assert variables["endpoints"] == []

    def test_exception_returns_empty(self, adapter: SkyWalkingAdapter) -> None:
        """GraphQL 异常时应返回空列表而非抛出."""
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("fail")):
            result = adapter._find_related_endpoints(["com.demo.Service.run"])

        assert result == []


class TestProcessEndpointStats:
    """_process_endpoint_stats 纯逻辑测试."""

    def test_maps_endpoint_names_and_metrics(self, adapter: SkyWalkingAdapter) -> None:
        """应将 endpoint id 映射为名称并透传指标."""
        stats_data = [
            {
                "endpointId": "ep1",
                "sla": 9900,
                "throughput": 50,
                "responseTime": {"avg": 100, "p95": 200, "p99": 300},
                "errorRate": {"value": 0.001},
            }
        ]
        with patch.object(
            adapter,
            "_execute_graphql",
            return_value={"endpoints": [{"key": "ep1", "label": "OrderService.create"}]},
        ):
            result = adapter._process_endpoint_stats(stats_data, ["ep1"])

        assert len(result) == 1
        stat = result[0]
        assert stat["endpoint"] == "OrderService.create"
        assert stat["endpoint_id"] == "ep1"
        assert stat["sla"] == 9900
        assert stat["throughput"] == 50
        assert stat["response_time_p95"] == 200
        assert stat["error_rate"] == 0.001
        assert stat["slow_calls"] == 0

    def test_slow_calls_estimated_when_p95_high(self, adapter: SkyWalkingAdapter) -> None:
        """p95 超过 1 秒阈值时按吞吐量估算慢调用次数."""
        stats_data = [
            {
                "endpointId": "ep1",
                "throughput": 200,
                "responseTime": {"avg": 900, "p95": 1500, "p99": 2000},
                "errorRate": {"value": 0.0},
            }
        ]
        with patch.object(adapter, "_execute_graphql", return_value={"endpoints": []}):
            result = adapter._process_endpoint_stats(stats_data, ["ep1"])

        # p95=1500 > 1000 → slow_calls = int(200 * 0.1) = 20
        assert result[0]["slow_calls"] == 20
        # endpoint_map 为空时回退使用 endpoint_id
        assert result[0]["endpoint"] == "ep1"

    def test_endpoint_map_exception_falls_back_to_id(self, adapter: SkyWalkingAdapter) -> None:
        """名称映射查询异常时回退使用 endpoint_id 作为名称."""
        stats_data = [
            {
                "endpointId": "ep9",
                "throughput": 0,
                "responseTime": {},
                "errorRate": {},
            }
        ]
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("fail")):
            result = adapter._process_endpoint_stats(stats_data, ["ep9"])

        assert result[0]["endpoint"] == "ep9"
        assert result[0]["response_time_p95"] == 0
        assert result[0]["error_rate"] == 0


class TestAnalyzeEndpointStats:
    """_analyze_endpoint_stats 编排测试."""

    def test_returns_processed_stats(self, adapter: SkyWalkingAdapter) -> None:
        """正常路径应返回处理后的统计列表."""
        with patch.object(
            adapter, "_execute_graphql", return_value={"stats": [{"endpointId": "ep1"}]}
        ), patch.object(
            adapter, "_process_endpoint_stats", return_value=[{"endpoint": "ep1"}]
        ) as mock_process:
            result = adapter._analyze_endpoint_stats(["ep1"], time_range=7)

        assert result == [{"endpoint": "ep1"}]
        mock_process.assert_called_once()

    def test_exception_returns_empty(self, adapter: SkyWalkingAdapter) -> None:
        """GraphQL 异常时返回空列表."""
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("fail")):
            result = adapter._analyze_endpoint_stats(["ep1"], time_range=7)

        assert result == []


class TestSuggestTestsForEndpoint:
    """_suggest_tests_for_endpoint 纯逻辑测试."""

    def test_generates_normal_and_error_tests(self, adapter: SkyWalkingAdapter) -> None:
        """endpoint 含类名与方法名时生成正常与异常流程建议."""
        stat = {"endpoint": "OrderService.create", "response_time_p95": 100, "throughput": 10}
        suggestions = adapter._suggest_tests_for_endpoint(stat)

        assert any("正常调用流程" in s for s in suggestions)
        assert any("异常情况处理" in s for s in suggestions)
        assert len(suggestions) == 2

    def test_adds_performance_test_when_slow(self, adapter: SkyWalkingAdapter) -> None:
        """p95 超过 500ms 时追加性能测试建议."""
        stat = {"endpoint": "single", "response_time_p95": 800, "throughput": 10}
        suggestions = adapter._suggest_tests_for_endpoint(stat)

        assert any("性能测试" in s for s in suggestions)

    def test_adds_concurrency_test_when_high_throughput(self, adapter: SkyWalkingAdapter) -> None:
        """吞吐量超过 100 时追加并发测试建议."""
        stat = {"endpoint": "single", "response_time_p95": 100, "throughput": 500}
        suggestions = adapter._suggest_tests_for_endpoint(stat)

        assert any("并发测试" in s for s in suggestions)


class TestRecommendTests:
    """recommend_tests 编排测试."""

    def test_no_endpoints_returns_empty(self, adapter: SkyWalkingAdapter) -> None:
        """未找到相关 endpoint 时直接返回空列表."""
        with patch.object(adapter, "_find_related_endpoints", return_value=[]):
            result = adapter.recommend_tests(["com.demo.Service.run"])

        assert result == []

    def test_high_error_rate_generates_recommendation(self, adapter: SkyWalkingAdapter) -> None:
        """错误率超过阈值时生成 HIGH 优先级推荐."""
        stats = [
            {
                "endpoint": "OrderService.create",
                "error_rate": 0.05,
                "slow_calls": 0,
                "sla": 9500,
                "throughput": 100,
                "response_time_p95": 200,
                "response_time_p99": 300,
            }
        ]
        with patch.object(adapter, "_find_related_endpoints", return_value=["ep1"]), patch.object(
            adapter, "_analyze_endpoint_stats", return_value=stats
        ):
            result = adapter.recommend_tests(["com.demo.OrderService.create"])

        assert len(result) == 1
        rec = result[0]
        assert rec["test_priority"] == "HIGH"
        assert rec["endpoint"] == "OrderService.create"
        assert rec["metrics"]["sla"] == 9500
        assert rec["suggested_tests"]

    def test_low_error_rate_and_few_slow_calls_skipped(self, adapter: SkyWalkingAdapter) -> None:
        """错误率与慢调用均低于阈值时不产生推荐."""
        stats = [
            {
                "endpoint": "ep",
                "error_rate": 0.001,
                "slow_calls": 2,
                "sla": 9999,
                "throughput": 10,
            }
        ]
        with patch.object(adapter, "_find_related_endpoints", return_value=["ep1"]), patch.object(
            adapter, "_analyze_endpoint_stats", return_value=stats
        ):
            result = adapter.recommend_tests(["com.demo.Service.run"])

        assert result == []

    def test_many_slow_calls_generates_recommendation(self, adapter: SkyWalkingAdapter) -> None:
        """慢调用超过 10 次时即使错误率低也生成推荐."""
        stats = [
            {
                "endpoint": "ep",
                "error_rate": 0.0,
                "slow_calls": 50,
                "sla": 9000,
                "throughput": 500,
            }
        ]
        with patch.object(adapter, "_find_related_endpoints", return_value=["ep1"]), patch.object(
            adapter, "_analyze_endpoint_stats", return_value=stats
        ):
            result = adapter.recommend_tests(["com.demo.Service.run"])

        assert len(result) == 1


class TestAnalyzeExceptions:
    """analyze_exceptions 与 _process_exception_logs 测试."""

    def test_returns_processed_exceptions(self, adapter: SkyWalkingAdapter) -> None:
        """正常路径应返回处理后的异常列表."""
        logs = [
            {
                "timestamp": 1000,
                "serviceId": "svc1",
                "endpointId": "ep1",
                "traceId": "trace1",
                "content": {
                    "exception": {
                        "exceptionType": "NullPointerException",
                        "message": "null ref",
                        "stackTrace": [
                            {"className": "com.demo.Foo", "methodName": "bar", "lineNumber": 42}
                        ],
                    }
                },
            }
        ]
        with patch.object(adapter, "_execute_graphql", return_value={"exceptions": {"logs": logs}}):
            result = adapter.analyze_exceptions("svc1")

        assert len(result) == 1
        exc = result[0]
        assert exc["exception_type"] == "NullPointerException"
        assert exc["message"] == "null ref"
        assert exc["trace_id"] == "trace1"
        assert "com.demo.Foo" in exc["stack_trace"]

    def test_exception_returns_empty(self, adapter: SkyWalkingAdapter) -> None:
        """GraphQL 异常时返回空列表."""
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("fail")):
            result = adapter.analyze_exceptions("svc1")

        assert result == []

    def test_process_exception_logs_handles_missing_fields(
        self, adapter: SkyWalkingAdapter
    ) -> None:
        """日志缺失字段时应使用默认值而不报错."""
        result = adapter._process_exception_logs([{"content": {}}])

        assert len(result) == 1
        assert result[0]["exception_type"] == ""
        assert result[0]["stack_trace"] == ""


class TestFormatStackTrace:
    """_format_stack_trace 纯逻辑测试."""

    def test_empty_returns_empty_string(self, adapter: SkyWalkingAdapter) -> None:
        """空堆栈返回空字符串."""
        assert adapter._format_stack_trace([]) == ""

    def test_formats_frames(self, adapter: SkyWalkingAdapter) -> None:
        """多帧堆栈应按行格式化."""
        frames = [
            {"className": "A", "methodName": "m1", "lineNumber": 1},
            {"className": "B", "methodName": "m2", "lineNumber": 2},
        ]
        result = adapter._format_stack_trace(frames)

        assert "at A.m1(Line 1" in result
        assert "at B.m2(Line 2" in result
        assert result.count("\n") == 1


class TestGetServiceHealth:
    """get_service_health 测试."""

    def test_filters_requested_services(self, adapter: SkyWalkingAdapter) -> None:
        """应仅返回请求的服务."""
        services = [
            {"label": "svc1", "key": "1"},
            {"label": "svc2", "key": "2"},
            {"label": "svc3", "key": "3"},
        ]
        with patch.object(adapter, "_execute_graphql", return_value={"services": services}):
            result = adapter.get_service_health(["svc1", "svc3"])

        labels = [s["label"] for s in result["services"]]
        assert labels == ["svc1", "svc3"]

    def test_exception_returns_empty_services(self, adapter: SkyWalkingAdapter) -> None:
        """GraphQL 异常时返回空服务列表."""
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("fail")):
            result = adapter.get_service_health(["svc1"])

        assert result == {"services": []}


class TestAnalyzePerformanceTrends:
    """analyze_performance_trends 测试."""

    def test_returns_metrics(self, adapter: SkyWalkingAdapter) -> None:
        """正常路径返回服务名、指标与时间范围."""
        with patch.object(
            adapter,
            "_execute_graphql",
            return_value={"linear": {"values": [{"id": "v1"}]}},
        ):
            result = adapter.analyze_performance_trends("svc1", time_range=15)

        assert result["service_name"] == "svc1"
        assert result["metrics"] == [{"id": "v1"}]
        assert result["time_range_days"] == 15

    def test_exception_returns_empty_metrics(self, adapter: SkyWalkingAdapter) -> None:
        """GraphQL 异常时返回空指标."""
        with patch.object(adapter, "_execute_graphql", side_effect=RuntimeError("fail")):
            result = adapter.analyze_performance_trends("svc1")

        assert result == {"service_name": "svc1", "metrics": []}


class TestExportTestRecommendations:
    """export_test_recommendations 文件导出测试."""

    def test_writes_json_file(self, adapter: SkyWalkingAdapter, tmp_path: Path) -> None:
        """应将推荐写入 JSON 文件并包含元数据."""
        output_file = tmp_path / "recommendations.json"
        recommendations: list[dict[str, Any]] = [
            {"endpoint": "svc.method", "test_priority": "HIGH"}
        ]

        adapter.export_test_recommendations(recommendations, output_file)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["total_recommendations"] == 1
        assert data["recommendations"] == recommendations
        assert "generated_at" in data

    def test_exports_empty_list(self, adapter: SkyWalkingAdapter, tmp_path: Path) -> None:
        """空推荐列表也应正常导出."""
        output_file = tmp_path / "empty.json"

        adapter.export_test_recommendations([], output_file)

        data = json.loads(output_file.read_text())
        assert data["total_recommendations"] == 0
        assert data["recommendations"] == []
