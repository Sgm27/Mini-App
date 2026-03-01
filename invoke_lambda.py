"""
Invoke ds-jk-backend Lambda Function URL — test FastAPI endpoints.

Usage:
    python invoke_lambda.py
"""

import json
import requests

BASE = "https://qnvhqoutfyxa7oupbr6phwvrhi0wwuzi.lambda-url.ap-southeast-1.on.aws/"


def test(method, path, body=None):
    url = f"{BASE}{path}"
    print(f"\n{'='*60}")
    print(f"{method} {path}")
    print(f"{'='*60}")
    if method == "GET":
        r = requests.get(url)
    else:
        r = requests.post(url, json=body)
    print(f"Status: {r.status_code}")
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(r.text[:500])
    return r


# 1) Health check
test("GET", "/api/health")

# 2) List categories
test("GET", "/api/categories")

# 3) List products (first 5)
test("GET", "/api/products?limit=5")

# 4) Get single product
test("GET", "/api/products/1")

# 5) Search products
test("GET", "/api/products?search=áo")

# 6) Create an order
test("POST", "/api/orders", {
    "customer_name": "Test User",
    "customer_phone": "0901234567",
    "customer_address": "123 Lambda Street",
    "items": [
        {"product_id": 1, "quantity": 2},
        {"product_id": 3, "quantity": 1},
    ],
})

# 7) Get the order we just created
test("GET", "/api/orders/1")
