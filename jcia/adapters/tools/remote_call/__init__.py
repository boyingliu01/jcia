"""Remote call adapters for detecting cross-service communication.

This package provides adapters for detecting and analyzing remote calls
in Java microservices, including RPC (Dubbo, Feign, gRPC, REST) and
message queue (RabbitMQ, Kafka, RocketMQ) interactions.
"""

from jcia.adapters.tools.remote_call.composite_adapter import CompositeRemoteCallAdapter
from jcia.adapters.tools.remote_call.dubbo_adapter import DubboRemoteCallAdapter
from jcia.adapters.tools.remote_call.feign_adapter import FeignRemoteCallAdapter
from jcia.adapters.tools.remote_call.http_adapter import HttpRemoteCallAdapter
from jcia.adapters.tools.remote_call.mq_adapter import MessageQueueRemoteCallAdapter

__all__ = [
    "CompositeRemoteCallAdapter",
    "DubboRemoteCallAdapter",
    "FeignRemoteCallAdapter",
    "HttpRemoteCallAdapter",
    "MessageQueueRemoteCallAdapter",
]