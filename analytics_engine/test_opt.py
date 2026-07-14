import os
import sys
import json
import traceback
from dotenv import load_dotenv

load_dotenv("/home/synapse/source/Pedidos/.env", override=True)
sys.path.append("/home/synapse/source/Pedidos")

from analytics_engine.core.optimizer import run_optimization

def test_run():
    # Simulamos el request que haría el comprador desde el Frontend
    request_data = {
        "criterios_agrupamiento": {
            "principio_activo": "AMOXICILINA"
        },
        "dias_cobertura": 21
    }

    print("Iniciando optimización para AMOXICILINA...")
    try:
        resultado = run_optimization(request_data)
        
        print("\n=== RESULTADO DE OPTIMIZACIÓN ===")
        print(f"ID Pedido: {resultado['pedido_id']}")
        print(f"Grupo: {resultado['grupo']}")
        print(f"Días: {resultado['dias_cobertura']}")
        print(f"Monto Estimado: ${resultado['monto_estimado_usd']:.2f}")
        print(f"Monto Máximo: ${resultado['monto_maximo_usd']:.2f}")
        print(f"Monto Total Sugerido: ${resultado['monto_total_pedido_usd']:.2f}")
        print(f"Sobrestock (oportunidad): ${resultado['monto_sobrestock_oportunidad_usd']:.2f}")
        print(f"Ahorro estimado vs Histórico: {resultado['ahorro_vs_media_min_historico_pct']}%")
        
        print("\n=== LÍNEAS DE PEDIDO ===")
        for linea in resultado['lineas']:
            print(f"- {linea['descripcion']} (Prov: {linea['proveedor']})")
            print(f"  Cant: {linea['cantidad']} | Precio: ${linea['precio_unitario']:.2f} | Total: ${linea['costo_total']:.2f}")
            print(f"  Amplificador: {linea['amplificador_aplicado']}x | Desvío: {linea['desvio_precio_pct']}%")
            print(f"  Justificación: {linea['justificacion']}")
            print("")
            
    except Exception as e:
        print(f"Error en la prueba de integración: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_run()
