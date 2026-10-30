"""Real end-to-end checks. Requires scripts/start.sh to be running."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

import grpc

from client.api import api_pb2, api_pb2_grpc
from client.api.client import Certs, Client

ROOT = Path(__file__).resolve().parent.parent
RESULTS = []


def check(name, function):
    try:
        detail = function()
        RESULTS.append({"name": name, "status": "PASS", "detail": detail})
        print(f"PASS {name}: {detail}", flush=True)
    except Exception as exc:
        RESULTS.append({"name": name, "status": "FAIL", "detail": str(exc)})
        print(f"FAIL {name}: {exc}", flush=True)


def batch(address):
    client = Client(address, Certs.load(ROOT / "certs"))
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda _: client.roll_die(), range(100)))
    assert all(1 <= value <= 6 for value in values), values
    return {"requests": len(values), "minimum": min(values), "maximum": max(values), "unique": sorted(set(values))}


def reject_certificate(address, rogue=False):
    ca = (ROOT / "certs/ca.pem").read_bytes()
    if rogue:
        credentials = grpc.ssl_channel_credentials(ca, (ROOT / "certs/rogue-key.pem").read_bytes(), (ROOT / "certs/rogue.pem").read_bytes())
    else:
        credentials = grpc.ssl_channel_credentials(ca)
    try:
        with grpc.secure_channel(address, credentials) as channel:
            api_pb2_grpc.DiceServiceStub(channel).RollDie(api_pb2.RollDieRequest(), timeout=3)
    except grpc.RpcError as exc:
        return {"code": exc.code().name, "rejected": True}
    raise AssertionError("request unexpectedly accepted")


def http_routes(port):
    answers = {}
    for route in ("grpc", "nginx"):
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/{route}", timeout=8) as response:
            body = response.read().decode()
        assert re.search(r"Value: [1-6]", body), body
        answers[route] = body.strip()
    return answers


def form_roll():
    url = "http://127.0.0.1:8000/"
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    html = opener.open(url).read().decode()
    csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
    data = urllib.parse.urlencode({"csrfmiddlewaretoken": csrf}).encode()
    response = opener.open(urllib.request.Request(url, data=data, headers={"Referer": url})).read().decode()
    assert "Сервис временно недоступен" not in response
    assert len(re.findall(r"Значение: [1-6]", response)) == 2
    (ROOT / "evidence/form-result.html").write_text(response, encoding="utf-8")
    return "CSRF-protected POST returned two dice values"


def nginx_status():
    context = ssl.create_default_context(cafile=str(ROOT / "certs/ca.pem"))
    context.load_cert_chain(str(ROOT / "certs/client.pem"), str(ROOT / "certs/client-key.pem"))
    with urllib.request.urlopen("https://127.0.0.1:9448/nginx_status", context=context, timeout=5) as response:
        body = response.read().decode()
    assert "Active connections:" in body, body
    return body.strip()


def environment():
    commands = [["sh", "-c", ". /etc/os-release; printf '%s\\n' \"$PRETTY_NAME\""], ["go", "version"], ["python", "--version"], ["nginx", "-v"], ["protoc", "--version"], ["cfssl", "version"]]
    versions = []
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        versions.append(result.stdout.strip() or result.stderr.strip())
    return versions


def main():
    os.chdir(ROOT)
    (ROOT / "evidence").mkdir(exist_ok=True)
    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/", timeout=1)
            break
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    check("Ubuntu environment and tool versions", environment)
    check("100 concurrent direct mTLS RPCs", lambda: batch("127.0.0.1:8443"))
    check("100 concurrent nginx mTLS RPCs", lambda: batch("127.0.0.1:9448"))
    for label, address in (("direct", "127.0.0.1:8443"), ("nginx", "127.0.0.1:9448")):
        check(f"{label} rejects missing client certificate", lambda address=address: reject_certificate(address))
        check(f"{label} rejects untrusted client certificate", lambda address=address: reject_certificate(address, True))
    check("Django client on port 8000", lambda: http_routes(8000))
    check("second Django client on port 8001", lambda: http_routes(8001))
    check("Django comparison form", form_roll)
    check("authenticated local nginx status", nginx_status)
    output = {"passed": sum(r["status"] == "PASS" for r in RESULTS), "total": len(RESULTS), "checks": RESULTS}
    (ROOT / "evidence/integration.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": output["passed"], "total": output["total"]}), flush=True)
    raise SystemExit(0 if output["passed"] == output["total"] else 1)


if __name__ == "__main__":
    main()
