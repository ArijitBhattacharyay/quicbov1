import json
import os
import time

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "agent_memory.json")

class SelectorMemory:
    """Manages persistent memory of successful selectors per platform."""
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return {}

    def save(self):
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except: pass

    def get_selector(self, platform, action):
        return self.data.get(platform, {}).get(action)

    def learn(self, platform, action, selector):
        if platform not in self.data: self.data[platform] = {}
        self.data[platform][action] = selector
        self.save()

    def invalidate(self, platform, action):
        if platform in self.data and action in self.data[platform]:
            del self.data[platform][action]
            self.save()

# Global memory instance
memory = SelectorMemory()

async def analyze_and_perform(page, platform, action, value=None):
    """
    Intelligently analyzes the page and performs the requested action.
    Learns successful patterns to speed up future runs.
    """
    # 1. Try Memory First
    saved_sel = memory.get_selector(platform, action)
    if saved_sel:
        try:
            el = page.locator(saved_sel).first
            if await el.is_visible(timeout=2000):
                if action in ["search_input", "location_input"]:
                    await el.click(click_count=3); await page.keyboard.press("Backspace")
                    await el.type(value, delay=30)
                    return True
                elif action == "click":
                    await el.click(force=True)
                    return True
        except:
            print(f"[Intelligence] Memory failed for {platform}:{action}, invalidating...")
            memory.invalidate(platform, action)

    # 2. Heuristic Search
    print(f"[Intelligence] Probing website for {platform}:{action}...")
    # ... logic handled in live_agent for now ...
    return False
