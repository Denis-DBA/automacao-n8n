"""Shared interactive setup, stdlib only. Never reads another project's .env."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, cwd=ROOT, **kwargs)


def ask(label, default):
    return input(f"{label} [{default}]: ").strip() or default


def valid_url(value):
    u = urlparse(value)
    if u.scheme not in {"http", "https"} or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError("Use URL HTTP(S) sem credenciais, query ou fragmento")
    return value.rstrip("/")


def load_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            values[k] = v
    return values


def request_json(url, key=None):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"} if key else {})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


def prepare_workflows(values):
    generated = ROOT / "generated"
    generated.mkdir(exist_ok=True)
    for src in (ROOT / "workflows").glob("*.json"):
        data = json.loads(src.read_text(encoding="utf-8"))
        for node in data["nodes"]:
            if node["name"] == "Configuração da Demonstração":
                config = {"model": values["OLLAMA_MODEL"], "evaluation_model": values["OLLAMA_MODEL"],
                          "proxy_url": "http://token-proxy:8003" if values["INSTALL_MODE"] == "full" else f"http://host.docker.internal:{values['PROXY_PORT']}",
                          "langfuse_url": "http://langfuse-web:3000" if values["INSTALL_MODE"] == "full" else values["LANGFUSE_BASE_URL"],
                          "evaluate": True, "capture_content": False}
                node["parameters"]["jsCode"] = "const chat=$input.first().json; return [{json:{...chat,config:" + json.dumps(config,ensure_ascii=False) + "}}];"
            if node["name"] == "Configurar Monitoramento":
                node["parameters"]["jsCode"] = node["parameters"]["jsCode"].replace("http://n8n:5678", "http://n8n:5678" if values["INSTALL_MODE"] == "full" else values["N8N_BASE_URL"])
        (generated / src.name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12 ou superior é necessário")
    parser = argparse.ArgumentParser(description="Instalação isolada do laboratório de observabilidade")
    parser.add_argument("--configure-only", action="store_true", help="Gera configuração; não inicia serviços")
    args = parser.parse_args()
    if not shutil.which("docker"):
        raise RuntimeError("Instale Docker Desktop ou Engine e o plugin Compose; nenhum programa será instalado automaticamente")
    run("docker", "info", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run("docker", "compose", "version")
    target = ROOT / ".env"
    if target.exists():
        print(".env existente preservado. Serão reutilizadas somente configurações deste projeto.")
        values = load_env(target)
    else:
        values = load_env(ROOT / ".env.example")
        mode = ask("Modo: A=completo / B=infraestrutura existente", "B").upper()
        if mode not in {"A", "B"}:
            raise ValueError("Selecione A ou B")
        values["INSTALL_MODE"] = "full" if mode == "A" else "existing"
        values["COMPOSE_PROJECT_NAME"] = ask("Nome Docker exclusivo (não use projeto existente)", values["COMPOSE_PROJECT_NAME"])
        if not __import__('re').fullmatch(r'[a-z0-9][a-z0-9_-]{2,50}', values["COMPOSE_PROJECT_NAME"]):
            raise ValueError("Nome Docker inválido")
        if mode == "B":
            for k in ["OLLAMA_URL", "N8N_BASE_URL", "LANGFUSE_BASE_URL"]:
                values[k] = valid_url(ask(k + " (endereço alcançável a partir dos containers)", values[k]))
        else:
            values["OLLAMA_URL"] = "http://ollama:11434"
            values["LANGFUSE_INIT_USER_EMAIL"] = ask("Login inicial Langfuse", "admin@example.invalid")
        values["OLLAMA_MODEL"] = ask("Modelo local (não será baixado sem consentimento)", values["OLLAMA_MODEL"])
        for k in ["PROXY_PORT"] + (["N8N_PORT", "LANGFUSE_PORT", "S3_PORT"] if mode == "A" else []):
            values[k] = str(int(ask(k, values[k])))
        for key in values:
            if not values[key]:
                values[key] = secrets.token_hex(32)
        values["LANGFUSE_INIT_PROJECT_PUBLIC_KEY"] = "pk-lf-" + secrets.token_hex(16)
        # Public prefix plus a fresh cryptographic value, never a stored credential.
        values["LANGFUSE_INIT_PROJECT_SECRET_KEY"] = "sk-lf-" + secrets.token_hex(32)  # pragma: allowlist secret
        if any(any(c in v for c in '\n\r$#\"\'') for v in values.values()):
            raise ValueError("Configuração contém caracteres incompatíveis com o formato .env simples")
        # Exclusive creation prevents races or accidental overwrites.
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write("".join(f"{k}={v}\n" for k, v in values.items()))
        print(".env criado com segredos novos. Consulte-o localmente; não o publique. No Windows, restrinja a ACL ao seu usuário.")
    prepare_workflows(values)
    cmd = ["docker", "compose", "--env-file", ".env"]
    if values["INSTALL_MODE"] == "full":
        cmd += ["--profile", "full"]
    run(*cmd, "config", "--quiet")
    if args.configure_only:
        print("Configuração pronta em generated/. Nenhum serviço iniciado.")
        return
    existing = subprocess.check_output(cmd + ["ps", "-q", "--all"], cwd=ROOT, text=True).strip()
    if existing:
        print("Este projeto Docker já possui containers. Configuração preservada; use compose ps e os testes. Nenhum serviço reiniciado.")
        return
    keys = ["PROXY_PORT"] + (["N8N_PORT", "LANGFUSE_PORT", "S3_PORT"] if values["INSTALL_MODE"] == "full" else [])
    for key in keys:
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", int(values[key])))
            except OSError:
                raise RuntimeError(f"Porta {values[key]} ocupada; ajuste {key} no .env deste projeto") from None
    print("Serão criados somente serviços e volumes do projeto " + values["COMPOSE_PROJECT_NAME"])
    if ask("Autorizar download de imagens e criação destes serviços? s/N", "N").lower() != "s":
        print("Configuração preservada; inicialização cancelada.")
        return
    run(*cmd, "up", "-d", "--build", "--wait", "--wait-timeout", "600")
    url = "http://127.0.0.1:" + values["PROXY_PORT"]
    request_json(url + "/health")
    try:
        models = request_json(url + "/v1/models", values["PROXY_API_KEY"])
        # An empty Ollama installation can return {"data": null}.
        names = [m["id"] for m in (models.get("data") or [])]
        print("Modelo configurado disponível:", values["OLLAMA_MODEL"] in names)
    except (OSError, ValueError):
        print("Ollama não alcançável pelo proxy. Confira OLLAMA_URL e a rede.")
    if values["INSTALL_MODE"] == "full":
        if ask("Autorizar download do modelo selecionado (pode ocupar vários GB)? s/N", "N").lower() == "s":
            run(*cmd, "exec", "-T", "ollama", "ollama", "pull", values["OLLAMA_MODEL"])
        print("n8n: http://localhost:" + values["N8N_PORT"])
        print("Langfuse: http://localhost:" + values["LANGFUSE_PORT"])
        print("Verifique Langfuse /api/public/health no navegador; worker pode levar alguns minutos para ficar pronto.")
    print("Proxy: " + url)
    print("Importe, configure e publique primeiro generated/monitoramento-langfuse-ollama.json; depois importe o principal.")
    print("Configure credenciais, selecione o subworkflow publicado e habilite Chamar Monitoramento; então publique o principal.")
    print("Leia docs/credenciais.md e docs/testes.md. A captura de conteúdo exige opt-in explícito no nó de configuração.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError):
        print("Instalação interrompida. Confira Docker, URLs, portas e configurações locais; nenhum volume foi removido.", file=sys.stderr)
        sys.exit(1)
