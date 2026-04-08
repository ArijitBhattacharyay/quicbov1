import httpx
import asyncio

async def test_search():
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("Testing search API for 'amul' at '110001'...")
            r = await client.get("http://127.0.0.1:8000/api/search?q=amul&pincode=110001")
            print(f"Status Code: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"Found {data.get('total')} products.")
            else:
                print(f"Error: {r.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
