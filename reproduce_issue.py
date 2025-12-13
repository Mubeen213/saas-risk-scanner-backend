from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("Attempting to fetch /health...")
try:
    response = client.get("/health")
    print(f"/health status: {response.status_code}")
    print(f"/health content: {response.json()}")
except Exception as e:
    print(f"CRASH on /health: {e}")

print("Attempting to fetch /docs...")
try:
    response = client.get("/docs")
    print(f"/docs status: {response.status_code}")
    # Don't print content as it is HTML
except Exception as e:
    print(f"CRASH on /docs: {e}")
