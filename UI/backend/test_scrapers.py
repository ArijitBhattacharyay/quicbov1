import asyncio
from live_agent import run_all_parallel

async def main():
    pincode = "700019"
    product = "brown bread"
    
    print(f"Starting parallel search for '{product}' at pincode '{pincode}' across all 4 platforms...")
    print("This may take a few moments as headless browsers navigate and scrape data...\n")
    
    reports = await run_all_parallel(pincode, product)
    
    print("="*60)
    print("SCRAPE RESULTS")
    print("="*60)
    
    for report in reports:
        print(f"\nPlatform: {report.platform.upper()}")
        if report.error:
            print(f"  [!] Error during scraping: {report.error}")
        else:
            print(f"  Reported Location: {report.location.strip() if report.location else 'Unknown'}")
            print(f"  Platform Delivery Est: {report.delivery_time}")
            
            # Filter for available products
            available_products = [p for p in report.products if p.available]
            print(f"  Found {len(available_products)} available products (out of {len(report.products)} total scraped).")
            
            # Print top 5 available products
            if available_products:
                print("  Top Available Products:")
                for i, p in enumerate(available_products[:5], 1):
                    # Safely handle potential empty attributes
                    weight = p.weight if p.weight != "—" else 'weight unknown'
                    print(f"    {i}. {p.name} ({weight}) - ₹{p.price} [Delivers in ~{p.delivery_time} mins]")
            else:
                print("  No available products found.")

if __name__ == "__main__":
    asyncio.run(main())
