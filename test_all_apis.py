"""
Comprehensive API test script for DevTrack AI platform.
Tests all major endpoints and reports results.
"""
import httpx
import json
import sys

import random
import string

BASE = "http://localhost:8000"
PASS = "TestPass123!"
# Randomize email to allow multiple runs
suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
EMAIL = f"testrunner_{suffix}@devtrack.ai"

results = []

def test(name, method, url, expected_status=None, **kwargs):
    """Run a test and record result."""
    try:
        r = getattr(httpx, method)(url, timeout=10, **kwargs)
        status = r.status_code
        try:
            body = r.json()
        except:
            body = r.text[:200]
        
        ok = True
        if expected_status and status != expected_status:
            ok = False
        if status >= 500:
            ok = False
            
        symbol = "PASS" if ok else "FAIL"
        results.append((name, symbol, status, str(body)[:120]))
        print(f"  [{symbol}] {name}: {status}")
        return r
    except Exception as e:
        results.append((name, "ERROR", 0, str(e)[:120]))
        print(f"  [ERROR] {name}: {e}")
        return None

print("=" * 60)
print("DevTrack AI - Comprehensive API Test Suite")
print("=" * 60)

# 1. Health Check
print("\n--- Health & Root ---")
test("Health Check", "get", f"{BASE}/api/health", 200)
test("Root Page", "get", f"{BASE}/", 200)

# 2. Auth - Register
print("\n--- Authentication ---")
r = test("Register", "post", f"{BASE}/api/v1/auth/register", 200, json={
    "full_name": "API Tester",
    "email": EMAIL,
    "password": PASS,
    "phone": "+961999888",
    "business_name": "API Test Biz",
    "business_type": "restaurant"
})

TOKEN = None
BIZ_ID = None
if r and r.status_code == 200:
    data = r.json()
    TOKEN = data.get("access_token")
    user = data.get("user", {})
    BIZ_ID = user.get("business_id")
elif r and r.status_code == 400:
    # Already registered, try login
    print("  (Already registered, logging in...)")

# 3. Auth - Login
r = test("Login", "post", f"{BASE}/api/v1/auth/login", 200, json={
    "email": EMAIL,
    "password": PASS
})
if r and r.status_code == 200:
    data = r.json()
    TOKEN = data.get("access_token")
    user = data.get("user", {})
    BIZ_ID = user.get("business_id")

if not TOKEN:
    print("\n*** FATAL: Could not get auth token. Stopping. ***")
    sys.exit(1)

headers = {"Authorization": f"Bearer {TOKEN}"}
print(f"  Token obtained, Business ID: {BIZ_ID}")

# 4. Auth - Get Profile
test("Get Profile", "get", f"{BASE}/api/v1/auth/me", 200, headers=headers)

# 5. Business
print("\n--- Business ---")
test("Get Business", "get", f"{BASE}/api/v1/business/", 200, headers=headers)
test("Get Business Settings", "get", f"{BASE}/api/v1/business/settings", headers=headers)
test("Get Modules", "get", f"{BASE}/api/v1/business/modules", headers=headers)

# 6. Customers
print("\n--- Customers ---")
r = test("Create Customer", "post", f"{BASE}/api/v1/customers/", json={
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+961111222"
}, headers=headers)

CUSTOMER_ID = None
if r and r.status_code in (200, 201):
    try:
        CUSTOMER_ID = r.json().get("id")
    except:
        pass

test("List Customers", "get", f"{BASE}/api/v1/customers/", 200, headers=headers)

if CUSTOMER_ID:
    test("Get Customer", "get", f"{BASE}/api/v1/customers/{CUSTOMER_ID}", headers=headers)

# 7. Products
print("\n--- Products ---")
r = test("Create Category", "post", f"{BASE}/api/v1/categories/", json={
    "name": "Main Course",
    "description": "Primary dishes"
}, headers=headers)

CAT_ID = None
if r and r.status_code in (200, 201):
    try:
        CAT_ID = r.json().get("id")
    except:
        pass

test("List Categories", "get", f"{BASE}/api/v1/categories/", headers=headers)

r = test("Create Product", "post", f"{BASE}/api/v1/products/", json={
    "name": "Shawarma Plate",
    "description": "Chicken shawarma with garlic sauce",
    "price": 12.99,
    "category_id": CAT_ID
}, headers=headers)

PRODUCT_ID = None
if r and r.status_code in (200, 201):
    try:
        PRODUCT_ID = r.json().get("id")
    except:
        pass

test("List Products", "get", f"{BASE}/api/v1/products/", 200, headers=headers)

# 8. Orders
print("\n--- Orders ---")
order_payload = {
    "customer_id": CUSTOMER_ID,
    "items": [{"product_id": PRODUCT_ID, "name": "Shawarma Plate", "quantity": 2, "unit_price": 12.99}] if PRODUCT_ID else [],
    "status": "pending"
}
r = test("Create Order", "post", f"{BASE}/api/v1/orders/", json=order_payload, headers=headers)

ORDER_ID = None
if r and r.status_code in (200, 201):
    try:
        ORDER_ID = r.json().get("id")
    except:
        pass

test("List Orders", "get", f"{BASE}/api/v1/orders/", 200, headers=headers)

if ORDER_ID:
    test("Get Order", "get", f"{BASE}/api/v1/orders/{ORDER_ID}", headers=headers)

# 9. Bookings
print("\n--- Bookings ---")
r = test("Create Booking", "post", f"{BASE}/api/v1/bookings/", json={
    "customer_id": CUSTOMER_ID,
    "start_time": "2026-04-01T19:00:00",
    "party_size": 4,
    "notes": "Window seat please"
}, headers=headers)

BOOKING_ID = None
if r and r.status_code in (200, 201):
    try:
        BOOKING_ID = r.json().get("id")
    except:
        pass

test("List Bookings", "get", f"{BASE}/api/v1/bookings/", 200, headers=headers)

# 10. Services
print("\n--- Services ---")
r = test("Create Service", "post", f"{BASE}/api/v1/services/", json={
    "name": "Catering",
    "description": "Event catering service",
    "price": 500.00,
    "duration_minutes": 180
}, headers=headers)

test("List Services", "get", f"{BASE}/api/v1/services/", headers=headers)

# 11. Conversations
print("\n--- Conversations ---")
test("List Conversations", "get", f"{BASE}/api/v1/conversations/", 200, headers=headers)

# 12. Workflows / Automation
print("\n--- Workflows ---")
test("List Workflows", "get", f"{BASE}/api/v1/workflows/", headers=headers)

# 13. Analytics
print("\n--- Analytics ---")
test("Analytics Summary", "get", f"{BASE}/api/v1/analytics/summary", headers=headers)
test("Analytics Insights", "get", f"{BASE}/api/v1/analytics/insights", headers=headers)

# 14. Documents
print("\n--- Documents ---")
test("List Documents", "get", f"{BASE}/api/v1/documents/", headers=headers)

# 15. Chat (Public Widget)
print("\n--- Public Chat ---")
test("Chat Message", "post", f"{BASE}/api/v1/chat/message", json={
    "message": "Hello, what are your hours?",
    "business_slug": "api-test-biz",
    "channel": "web"
}, headers=headers)

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
passed = sum(1 for r in results if r[1] == "PASS")
failed = sum(1 for r in results if r[1] == "FAIL")
errors = sum(1 for r in results if r[1] == "ERROR")
print(f"  PASSED: {passed}")
print(f"  FAILED: {failed}")
print(f"  ERRORS: {errors}")
print(f"  TOTAL:  {len(results)}")

if failed > 0 or errors > 0:
    print("\n--- Failed/Error Tests ---")
    for name, status, code, body in results:
        if status in ("FAIL", "ERROR"):
            print(f"  [{status}] {name}: HTTP {code} - {body}")

print("\nDone.")
