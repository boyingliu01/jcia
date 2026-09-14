"""Tests for GrpcRemoteCallAdapter 与 ServiceRegistry（issue #16 重新实现）."""

from pathlib import Path

from jcia.adapters.tools.remote_call.grpc_adapter import GrpcRemoteCallAdapter
from jcia.adapters.tools.service_registry.mock_registry import MockServiceRegistry
from jcia.core.entities.remote_call import RemoteCallType
from jcia.core.interfaces.service_registry import ServiceInfo


class TestGrpcRemoteCallAdapter:
    """Tests for GrpcRemoteCallAdapter."""

    def test_adapter_initialization(self) -> None:
        """Verify adapter initializes correctly."""
        adapter = GrpcRemoteCallAdapter()
        assert adapter.supports_cross_service is True
        assert adapter.supported_call_types == [RemoteCallType.GRPC]

    def test_detect_grpc_new_blocking_stub(self, tmp_path: Path) -> None:
        """newBlockingStub 模式应被检测为 gRPC 调用."""
        adapter = GrpcRemoteCallAdapter()
        test_file = tmp_path / "OrderClient.java"
        test_file.write_text(
            """
        ManagedChannel channel = ManagedChannelBuilder.forAddress("host", 9090).build();
        GreeterGrpc.GreeterBlockingStub stub = GreeterGrpc.newBlockingStub(channel);
        """
        )

        calls = adapter.detect_remote_calls(str(test_file))
        assert len(calls) >= 1
        assert all(c.call_type == RemoteCallType.GRPC for c in calls)

    def test_detect_from_directory(self, tmp_path: Path) -> None:
        """目录扫描应聚合多个文件的 gRPC 调用."""
        (tmp_path / "A.java").write_text("GreeterGrpc.newStub(channel);")
        (tmp_path / "B.java").write_text("HelloGrpc.HelloStub s = HelloGrpc.newBlockingStub(c);")
        (tmp_path / "C.txt").write_text("GreeterGrpc.newStub(channel);")

        adapter = GrpcRemoteCallAdapter()
        calls = adapter.detect_from_directory(tmp_path)
        assert len(calls) >= 2

    def test_nonexistent_file_returns_empty(self) -> None:
        """不存在的文件应返回空列表而非抛异常."""
        adapter = GrpcRemoteCallAdapter()
        assert adapter.detect_remote_calls("no_such_file.java") == []

    def test_service_registry_optional_injection(self) -> None:
        """service_registry 为可选注入（跨服务链路分析扩展点）."""
        registry = MockServiceRegistry()
        adapter = GrpcRemoteCallAdapter(service_registry=registry)
        assert adapter._registry is registry


class TestServiceInfo:
    """Tests for ServiceInfo entity-like value object."""

    def test_to_endpoint_with_host_port(self) -> None:
        """host+port 应生成 http URL endpoint."""
        info = ServiceInfo(name="order-service", version="1.0.0", host="h1", port=8080)
        endpoint = info.to_endpoint()
        assert endpoint.service_name == "order-service"
        assert endpoint.url == "http://h1:8080"
        assert endpoint.version == "1.0.0"

    def test_metadata_default_empty_dict(self) -> None:
        """metadata 缺省应为空 dict 而非 None."""
        info = ServiceInfo(name="svc")
        assert info.metadata == {}


class TestMockServiceRegistry:
    """Tests for MockServiceRegistry."""

    def test_register_and_resolve(self) -> None:
        """注册后可解析，未注册返回 None."""
        registry = MockServiceRegistry()
        registry.register_service(ServiceInfo(name="svc-a", version="2.1", host="h", port=1))

        assert registry.resolve_service("svc-a") is not None
        assert registry.resolve_service("missing") is None
        assert registry.get_service_version("svc-a") == "2.1"
        assert registry.get_service_version("missing") is None

    def test_list_services(self) -> None:
        """list_services 返回全部注册服务."""
        registry = MockServiceRegistry()
        registry.register_service(ServiceInfo(name="s1"))
        registry.register_service(ServiceInfo(name="s2"))
        assert {s.name for s in registry.list_services()} == {"s1", "s2"}
