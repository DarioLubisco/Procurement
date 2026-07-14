import httpx
import asyncio

async def test_chat():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:8000/api/orquestador/chat",
                json={"agent": "agente_it", "message": "Hola prueba"},
                timeout=10
            )
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_chat())
