import strawberry
from typing import List
from .resolvers import get_pedidos, get_inventario, PedidoType, InventarioType

@strawberry.type
class Query:
    @strawberry.field
    def pedidos(self) -> List[PedidoType]:
        return get_pedidos()
        
    @strawberry.field
    def inventario(self) -> List[InventarioType]:
        return get_inventario()

@strawberry.type
class Mutation:
    @strawberry.mutation
    def crear_pedido_sugerido(self, proveedor_id: str) -> bool:
        # Lógica para llamar al Analytics Engine u Orquestador
        return True

schema = strawberry.Schema(query=Query, mutation=Mutation)
