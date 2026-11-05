import sys
sys.path.insert(0, "src")
from fastapi.testclient import TestClient
from kutomoto.server.app import create_app

app = create_app()
client = TestClient(app, raise_server_exceptions=False)

test_vectors = [
    "C%3A%2F",
    "C:/",
    "D%3A%2F",
    "D:/",
    "C:%5C",
    "..%2F..%2Fwin.ini",
    "../../win.ini",
    "..%2f..%2fwindows%2fsystem32%2fcalc.exe",
    "sub/path/traversal",
    "CON",
    "NUL",
    "AUX",
    "PRN",
    "*",
    "*sensitive*",
    "?test",
    "[a-z]*",
    "{evil}",
    "A" * 257,
    "A" * 4096,
]

for v in test_vectors:
    url = f"/api/execute/audit/{v}"
    res = client.get(url)
    ct = res.headers.get("content-type", "")
    assert res.status_code == 404, f"Vector {v} returned {res.status_code} instead of 404! Body: {res.text[:200]}"
    assert "application/json" in ct, f"Vector {v} did not return JSON: {ct}"
    data = res.json()
    assert data.get("type") == "https://90studio.com/errors/404", f"Vector {v} wrong type: {data.get('type')}"
    assert data.get("status") == 404, f"Vector {v} wrong status in body: {data.get('status')}"
    assert data.get("copyright") == "Copyrights reserved to 90Studio", f"Vector {v} missing copyright: {data}"
    print(f"Vector {v!r:42} -> 404 JSON OK, copyright confirmed")

print("\nALL ADVERSARIAL PATH VECTORS CLEANLY REJECTED WITH 404 PROBLEM DETAILS!")
