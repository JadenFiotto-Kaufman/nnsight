from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Tuple

from ...tracing import protocols
from ...tracing.Graph import Graph
from ..backends import LocalMixin
from .Collector import Collection

if TYPE_CHECKING:
    from ...tracing.Node import Node
    from ...tracing.Proxy import Proxy
    from ...intervention import InterventionProxy
    from .Accumulator import Accumulator

@protocols.register_protocol
class SumProtocol(protocols.Protocol):

    name = "iter_sum"

    @classmethod
    def add(cls, graph: Graph, value_node: "Node") -> "InterventionProxy":

        # Check  if value node's Graph is exited? Otherwise that should be an error

        return graph.create(
            target=cls.name, proxy_value=value_node.proxy_value, args=[value_node]
        )

    @classmethod
    def execute(cls, node: "Node"):

        value_node: "Node" = node.args[0]

        if not node.done():

            node._value = value_node.value

        else:

            node._value += value_node.value

        node.reset()
        
        if protocols.BridgeProtocol.get_bridge(node.graph).release:
            
            node.set_value(node._value)


@protocols.register_protocol
class IteratorItemProtocol(protocols.Protocol):

    name = "iter_item"
    attachment_name = "nnsight_iter_idx"

    @classmethod
    def add(cls, graph: Graph) -> "Proxy":

        if not cls.attachment_name in graph.attachments:

            graph.attachments[cls.attachment_name] = 0

        else:

            graph.attachments[cls.attachment_name] += 1

        return (
            graph.create(target=cls.name, proxy_value=None),
            graph.attachments[cls.attachment_name],
        )

    @classmethod
    def set(cls, graph: Graph, value: Any, iter_idx: int) -> None:

        graph.nodes[f"{cls.name}_{iter_idx}"].set_value(value)


class Iterator(Collection):

    def __init__(self, data: Iterable, *args, iter_idx: int = None, **kwargs) -> None:

        super().__init__(*args, **kwargs)

        self.data = data
        self.iter_idx = iter_idx

    def __enter__(self) -> Tuple[int, Iterator]:

        super().__enter__()

        iter_item_proxy, self.iter_idx = IteratorItemProtocol.add(
            self.accumulator.graph
        )

        return iter_item_proxy, self

    ### BACKENDS ########

    def local_backend_execute(self) -> None:

        self.accumulator.graph.compile()

        self.accumulator.bridge.release = False

        last_idx = len(self.data) - 1

        for idx, item in enumerate(self.data):
            
            last_iter = idx == last_idx

            if last_iter:

                self.accumulator.bridge.release = True

            IteratorItemProtocol.set(self.accumulator.graph, item, self.iter_idx)

            self.iterator_backend_execute(last_iter=last_iter)
