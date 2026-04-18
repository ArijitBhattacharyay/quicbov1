import asyncio
import live_agent

async def main():
    print("Starting browsers...")
    await live_agent.startup()
    print("Prewarming...")
    await live_agent.prewarm_location("110001")
    print("Searching...")
    results = await live_agent.run_all_parallel("110001", "Amul Milk")
    for r in results:
        print(f"Platform: {r.platform}, Results: {len(r.products)}")
        for p in r.products[:2]:
            print(f"  - {p.name}: {p.price}")
    await live_agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
