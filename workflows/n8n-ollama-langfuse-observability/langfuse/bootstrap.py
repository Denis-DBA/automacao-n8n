"""Validate an independently initialized project. Reads only this project's env."""
import argparse
import base64
import json
import os
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description="Confere acesso Langfuse sem exportar dados")
    parser.add_argument("--url", default="http://localhost:13000")
    args = parser.parse_args()
    public = os.environ["LANGFUSE_PUBLIC_KEY"]
    secret = os.environ["LANGFUSE_SECRET_KEY"]
    auth = base64.b64encode(f"{public}:{secret}".encode()).decode()
    req = Request(args.url.rstrip("/") + "/api/public/projects", headers={"Authorization": "Basic " + auth})
    with urlopen(req, timeout=15) as response:
        data = json.load(response)
        if not data.get("data"):
            raise SystemExit("Nenhum projeto acessível")
    print("Credenciais do projeto aceitas. Nenhum histórico foi exportado.")


if __name__ == "__main__":
    main()
