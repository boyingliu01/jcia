"""
验证脚本：测试 RemoteCall 实体类的所有功能。

使用方法：
    python test_remote_call_entities.py

如果所有测试都通过，将显示 "所有测试通过！"。
"""

from jcia.core.entities.remote_call import (
    RemoteCallType,
    RemoteEndpoint,
    RemoteCallInfo,
    RemoteCallChain,
)


def test_remote_call_type():
    """测试 RemoteCallType 枚举。"""
    print("测试 RemoteCallType...")

    # 测试值
    assert RemoteCallType.DUBBO.value == "dubbo"
    assert RemoteCallType.FEIGN.value == "feign"
    assert RemoteCallType.GRPC.value == "grpc"
    assert RemoteCallType.REST.value == "rest"
    assert RemoteCallType.MQ_RABBITMQ.value == "rabbitmq"
    assert RemoteCallType.MQ_KAFKA.value == "kafka"
    assert RemoteCallType.MQ_ROCKETMQ.value == "rocketmq"

    # 测试数量
    assert len(RemoteCallType) == 7

    # 测试 is_rpc
    assert RemoteCallType.DUBBO.is_rpc() is True
    assert RemoteCallType.FEIGN.is_rpc() is True
    assert RemoteCallType.MQ_KAFKA.is_rpc() is False

    # 测试 is_message_queue
    assert RemoteCallType.MQ_RABBITMQ.is_message_queue() is True
    assert RemoteCallType.DUBBO.is_message_queue() is False

    print("  ✓ RemoteCallType 测试通过")


def test_remote_endpoint():
    """测试 RemoteEndpoint 类。"""
    print("测试 RemoteEndpoint...")

    # 测试完整字段创建
    endpoint = RemoteEndpoint(
        service_name="user-service",
        interface="com.example.UserService",
        method="getUserById",
        url="http://user-service/api/users/{id}",
        version="1.0.0",
        group="production",
    )
    assert endpoint.service_name == "user-service"
    assert endpoint.interface == "com.example.UserService"
    assert endpoint.method == "getUserById"
    assert endpoint.is_complete() is True

    # 测试最小字段创建
    minimal = RemoteEndpoint(service_name="order-service")
    assert minimal.service_name == "order-service"
    assert minimal.interface is None
    assert minimal.is_complete() is False

    # 测试默认值
    default = RemoteEndpoint()
    assert default.service_name is None
    assert default.interface is None

    # 测试 full_identifier
    ep1 = RemoteEndpoint(
        service_name="svc", interface="Iface", method="method"
    )
    assert ep1.full_identifier == "svc:Iface.method"

    ep2 = RemoteEndpoint(interface="Iface", method="method")
    assert ep2.full_identifier == "Iface.method"

    ep3 = RemoteEndpoint(service_name="svc", method="method")
    assert ep3.full_identifier == "svc.method"

    ep4 = RemoteEndpoint()
    assert ep4.full_identifier == ""

    print("  ✓ RemoteEndpoint 测试通过")


def test_remote_call_info():
    """测试 RemoteCallInfo 类。"""
    print("测试 RemoteCallInfo...")

    endpoint = RemoteEndpoint(
        service_name="user-service",
        method="getUser",
    )

    # 测试完整字段创建
    call_info = RemoteCallInfo(
        call_type=RemoteCallType.DUBBO,
        endpoint=endpoint,
        caller_class="com.example.OrderController",
        caller_method="createOrder",
        confidence=0.95,
        source_line=42,
        source_file="OrderController.java",
        annotation="@DubboReference",
        metadata={"timeout": 5000},
    )
    assert call_info.call_type == RemoteCallType.DUBBO
    assert call_info.endpoint.service_name == "user-service"
    assert call_info.caller_class == "com.example.OrderController"
    assert call_info.confidence == 0.95
    assert call_info.is_high_confidence() is True

    # 测试默认值
    default_call = RemoteCallInfo(
        call_type=RemoteCallType.FEIGN,
        endpoint=endpoint,
        caller_class="Test",
    )
    assert default_call.confidence == 0.8
    assert default_call.source_line == 0
    assert default_call.is_high_confidence() is False

    # 测试置信度边界
    high = RemoteCallInfo(
        call_type=RemoteCallType.DUBBO, endpoint=endpoint, caller_class="A", confidence=0.9
    )
    assert high.is_high_confidence() is True

    low = RemoteCallInfo(
        call_type=RemoteCallType.DUBBO, endpoint=endpoint, caller_class="A", confidence=0.89
    )
    assert low.is_high_confidence() is False

    # 测试 full_call_signature
    call = RemoteCallInfo(
        call_type=RemoteCallType.DUBBO,
        endpoint=endpoint,
        caller_class="OrderService",
        caller_method="processOrder",
    )
    expected = "OrderService.processOrder -> user-service.getUser"
    assert call.full_call_signature == expected

    # 测试 __test__ = False
    assert call.__test__ is False

    print("  ✓ RemoteCallInfo 测试通过")


def test_remote_call_chain():
    """测试 RemoteCallChain 类。"""
    print("测试 RemoteCallChain...")

    endpoint1 = RemoteEndpoint(service_name="svc1", method="method1")
    endpoint2 = RemoteEndpoint(service_name="svc2", method="method2")

    call1 = RemoteCallInfo(
        call_type=RemoteCallType.DUBBO,
        endpoint=endpoint1,
        caller_class="A",
        caller_method="a",
    )
    call2 = RemoteCallInfo(
        call_type=RemoteCallType.FEIGN,
        endpoint=endpoint2,
        caller_class="B",
        caller_method="b",
    )

    chain = RemoteCallChain(
        calls=[call1, call2],
        source_method="com.example.Start.method",
        target_service="svc2",
    )

    assert len(chain.calls) == 2
    assert chain.source_method == "com.example.Start.method"
    assert chain.target_service == "svc2"
    assert chain.hop_count() == 2

    # 测试默认值
    default_chain = RemoteCallChain(calls=[], source_method="start")
    assert default_chain.calls == []
    assert default_chain.target_service is None
    assert default_chain.total_confidence == 0.0

    # 测试 get_unique_services
    endpoint3 = RemoteEndpoint(service_name="svc1")  # Duplicate
    call3 = RemoteCallInfo(
        call_type=RemoteCallType.REST, endpoint=endpoint3, caller_class="C"
    )
    chain2 = RemoteCallChain(
        calls=[call1, call2, call3], source_method="start"
    )
    unique = chain2.get_unique_services()
    assert unique == {"svc1", "svc2"}

    # 测试 calculate_total_confidence
    endpoint_a = RemoteEndpoint(service_name="a")
    endpoint_b = RemoteEndpoint(service_name="b")
    call_a = RemoteCallInfo(
        call_type=RemoteCallType.DUBBO,
        endpoint=endpoint_a,
        caller_class="A",
        confidence=0.9,
    )
    call_b = RemoteCallInfo(
        call_type=RemoteCallType.FEIGN,
        endpoint=endpoint_b,
        caller_class="B",
        confidence=0.8,
    )
    chain3 = RemoteCallChain(calls=[call_a, call_b], source_method="start")
    total_conf = chain3.calculate_total_confidence()
    assert pytest.approx(total_conf, rel=1e-9) == 0.85

    # 测试空链
    empty_chain = RemoteCallChain(calls=[], source_method="start")
    assert empty_chain.calculate_total_confidence() == 0.0
    assert empty_chain.hop_count() == 0

    # 测试 __test__ = False
    assert chain.__test__ is False

    print("  ✓ RemoteCallChain 测试通过")


def run_all_tests():
    """运行所有测试。"""
    print("=" * 60)
    print("开始测试 Remote Call 实体类")
    print("=" * 60)
    print()

    try:
        test_remote_call_type()
        test_remote_endpoint()
        test_remote_call_info()
        test_remote_call_chain()

        print()
        print("=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n💥 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    success = run_all_tests()
    sys.exit(0 if success else 1)
