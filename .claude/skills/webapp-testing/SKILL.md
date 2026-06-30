---
name: webapp-testing
description: "Test local web applications using Playwright. Use when testing the Dore OS dashboard, verifying UI behavior, or debugging frontend issues."
version: 1.0
---

# Webapp Testing for Dore OS

## Dashboard Tests
```bash
# Smoke test
curl -s http://localhost:8700/ | grep "DORE/OS"

# API health
curl -s http://localhost:8700/api/artists | python3 -m json.tool | head
curl -s http://localhost:8700/api/lint

# Full verification
python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8700/')
assert r.status == 200
data = json.loads(urllib.request.urlopen('http://localhost:8700/api/artists').read())
assert len(data) >= 3
print('Dashboard OK')
"
```

## Playwright Tests (optional)
```python
# test_dashboard.py
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('http://localhost:8700')
    assert 'DORE/OS' in page.title()
    assert page.locator('.stat').count() == 4
    browser.close()
```
