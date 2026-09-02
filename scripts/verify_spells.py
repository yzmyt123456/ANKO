"""用 TestClient 验证 /api/rules/spells 返回的 school 字段。"""

import sys

sys.path.insert(0, ".")
from fastapi.testclient import TestClient

from anko.app import create_app

client = TestClient(create_app())
r = client.get("/api/rules/spells?limit=500")
print("status:", r.status_code)
data = r.json()
print("count:", len(data))
schools = sorted({d["school"] for d in data if d.get("school")})
print("schools:", schools)
null_school = [d["name"] for d in data if not d.get("school")]
print("school 为空的条数:", len(null_school), null_school[:5])
