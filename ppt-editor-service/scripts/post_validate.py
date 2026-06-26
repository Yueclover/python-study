import sys
import httpx

path = sys.argv[1]
url = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8001/validate"
html = open(path, encoding="utf-8").read()

r = httpx.post(url, json={"html": html}, timeout=180)
print("HTTP", r.status_code)
print(r.text)
