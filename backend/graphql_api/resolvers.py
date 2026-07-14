import strawberry
from typing import List

@strawberry.type
class PedidoType:
    id: str
    estado: str
    total: float

@strawberry.type
class InventarioType:
    producto_id: str
    nombre: str
    stock_actual: int

def get_pedidos() -> List[PedidoType]:
    # Aquí iría la consulta real a la BD
    return [
        PedidoType(id="PED-001", estado="Pendiente", total=150.50),
        PedidoType(id="PED-002", estado="Aprobado", total=1020.00)
    ]

def get_inventario() -> List[InventarioType]:
    # Aquí iría la consulta real a la BD
    return [
        InventarioType(producto_id="PROD-01", nombre="Aspirina", stock_actual=50),
        InventarioType(producto_id="PROD-02", nombre="Ibuprofeno", stock_actual=20)
    ]
