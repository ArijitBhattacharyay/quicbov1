import asyncio
from live_agent import run_all_parallel, prewarm_location, startup, shutdown
import time

async def main():
    await startup()
    print("Prewarming...")
    await prewarm_location("110021")
    
    print("\nSearching...")
    start_time = time.time()
    results = await run_all_parallel("110021", "coffee")
    end_time = time.time()
    
    print(f"\nTime taken: {end_time - start_time:.2f}s")
    for r in results:
        print(f"Platform: {r.platform}, Products found: {len(r.products)}")
        if r.error:
            print(f"  Error: {r.error}")

    await shutdown()

if __name__ == "__main__":
    asyncio.run(main())
