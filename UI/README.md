# Quicbo — Price Comparison App

Compare grocery prices across **Blinkit, Zepto, Swiggy Instamart & BigBasket** in real-time.

---

## 🚀 How to Run

### 1. Backend (FastAPI)
```powershell
cd c:\quicbo\backend
pip install -r requirements.txt
python -m playwright install chromium
uvicorn main:app --reload --port 8000
```

### 2. Frontend (React/Vite)
```powershell
cd c:\quicbo\frontend
npm install
npm run dev
```

Open: http://localhost:5173

---

## 📁 Project Structure

```
quicbo/
├── backend/
│   ├── main.py                  ← FastAPI app (API routes, CORS)
│   ├── requirements.txt
│   ├── scraper/
│   │   ├── base.py              ← Abstract scraper class
│   │   ├── blinkit.py           ← Blinkit Playwright scraper
│   │   ├── zepto.py             ← Zepto Playwright scraper
│   │   ├── instamart.py         ← Swiggy Instamart scraper
│   │   ├── bigbasket.py         ← BigBasket scraper
│   │   └── manager.py           ← Parallel asyncio.gather orchestrator
│   ├── normalizer/
│   │   ├── matcher.py           ← Fuzzy product grouping (rapidfuzz)
│   │   └── models.py            ← Pydantic data models
│   ├── cache/
│   │   └── store.py             ← In-memory TTL cache (10 min)
│   └── api/
│       └── pincode.py           ← api.postalpincode.in resolver
│
└── frontend/
    ├── index.html
    └── src/
        ├── App.jsx              ← Root app + cart state + page routing
        ├── main.jsx
        ├── index.css            ← Global styles (matches UI design)
        ├── api.js               ← Axios client
        ├── platforms.js         ← Platform constants (colors, labels)
        ├── hooks/
        │   └── useSearch.js     ← Search state management hook
        ├── components/
        │   ├── Navbar.jsx       ← Logo, location, search, profile
        │   ├── PincodeModal.jsx ← Pincode entry + live lookup
        │   ├── ProductCard.jsx  ← Product image, best offer, compare
        │   ├── ProductGrid.jsx  ← 4-column responsive grid
        │   ├── CompareDropdown.jsx  ← Platform price accordion
        │   └── LoadingSkeleton.jsx  ← Shimmer loading cards
        └── pages/
            ├── HomePage.jsx     ← Search flow, hero, results
            └── CartPage.jsx     ← Cart draft + redirect to platforms
```

---

## ⚙️ How It Works

1. **User sets pincode** → resolved via `api.postalpincode.in`
2. **User searches a product** → backend runs all 4 scrapers **in parallel** via `asyncio.gather`
3. **Results normalized** → fuzzy matching groups same product from different platforms
4. **Best offer computed** → lowest price / fastest delivery highlighted
5. **Cached 10 minutes** → repeated searches return instantly
6. **UI shows** → product cards with Best Offer + Compare Others dropdown

---

## 🔧 Performance Notes

- All 4 scrapers run concurrently — total time = slowest scraper, not sum
- TTL cache prevents redundant scraping for same query+pincode
- Skeleton UI shown immediately while scraping
- React lazy rendering for product cards
