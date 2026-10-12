"""Exercise disposable Docker services over HTTP; creates synthetic accounts/leads."""

import argparse
import json
import re
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--frontend-url", required=True)
    args = parser.parse_args()
    passed = []

    def request(base, path, expected=200, method="GET", payload=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = json.dumps(payload).encode() if payload is not None else None
        req = Request(base.rstrip("/") + path, data=body, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=30)
        except HTTPError as exc:
            response = exc
        with response:
            status = response.status
            raw = response.read().decode()
        assert status == expected, f"{method} {path}: expected {expected}, got {status}: {raw[:400]}"
        return json.loads(raw) if raw.startswith(("{", "[")) else raw

    request(args.api_url, "/health")
    passed.append("API health")
    html = request(args.frontend_url, "/")
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    assert assets, "No built assets in frontend HTML"
    for asset in assets:
        request(args.frontend_url, asset)
    assert request(args.frontend_url, "/relatorios") == html
    passed.append("Nginx HTML, built assets and SPA fallback")
    request(args.frontend_url, "/api/scores", expected=401)
    passed.append("Anonymous data access denied via Nginx")

    tokens = []
    for index in range(2):
        email = f"docker-{uuid.uuid4().hex}@urbia.test"
        password = "Synthetic-docker-test-2026"
        account = request(args.frontend_url, "/api/auth/register", method="POST", payload={
            "name": f"Docker test {index}", "email": email,
            "password": password, "profile": "corretor",
        })
        assert account["is_admin"] is False
        login = request(args.frontend_url, "/api/auth/login", method="POST", payload={
            "email": email, "password": password,
        })
        token = login["access_token"]
        tokens.append(token)
        me = request(args.frontend_url, "/api/auth/me", token=token)
        assert me["email"] == email
    passed.append("Registration, login and persistent PostgreSQL accounts")
    scores = request(args.frontend_url, "/api/scores", token=tokens[0])
    assert isinstance(scores, list)
    passed.append("Scores query on initialized PostGIS")
    request(args.frontend_url, "/api/pipeline/refresh", expected=403, method="POST", token=tokens[0])
    passed.append("Pipeline execution restricted to administrators")
    lead = request(args.frontend_url, "/api/leads", method="POST", token=tokens[0], payload={
        "name": "Synthetic Docker lead", "budget": 250000,
    })
    own = request(args.frontend_url, "/api/leads", token=tokens[0])
    other = request(args.frontend_url, "/api/leads", token=tokens[1])
    assert any(row["id"] == lead["id"] for row in own)
    assert all(row["id"] != lead["id"] for row in other)
    request(args.frontend_url, f"/api/leads/{lead['id']}/status", expected=404,
            method="PATCH", token=tokens[1], payload={"status": "contatado"})
    passed.append("Lead creation and isolation between accounts")
    prediction = request(args.frontend_url, "/api/predict", method="POST", token=tokens[0], payload={
        "area_m2": 100, "property_type": "terreno",
    })
    assert prediction["model_status"] == "fallback_hedonic" and prediction["warning"]
    passed.append("Missing price model returns explicit fallback warning")
    legal = request(args.frontend_url, "/api/legal/assess?zone=ZM1&intended_use=residencial", token=tokens[0])
    assert isinstance(legal, dict)
    passed.append("Legal assessment endpoint")
    print(json.dumps({"checks_passed": len(passed), "checks": passed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
