
import asyncio
import json
import logging
import os
import re
import secrets
import time
import uuid
from contextlib import asynccontextmanager, aclosing
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

# =========================================================
# 1. CONFIGURAÇÕES
# =========================================================

@asynccontextmanager
async def lifespan(app):
    await validate_config()
    yield

app = FastAPI(title="Ollama Token Proxy", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://host.docker.internal:11434"
).rstrip("/")

TOKEN_DIR = Path(
    os.getenv("TOKEN_DATA_DIR", "/data")
)

TOKEN_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)

TOKEN_FILE = TOKEN_DIR / "token_usage.jsonl"
PROXY_API_KEY = os.getenv("PROXY_API_KEY", "")
MAX_BODY = int(os.getenv("MAX_BODY_BYTES", "1048576"))
MAX_LINE = int(os.getenv("MAX_LINE_BYTES", "4194304"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "4"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "180"))
RETENTION_DAYS = int(os.getenv("TOKEN_RETENTION_DAYS", "7"))
MAX_STORAGE = int(os.getenv("TOKEN_MAX_STORAGE_BYTES", "67108864"))
active = 0
ALLOWED_GET = {"api/tags", "v1/models"}

def authorized(received, expected):
    return len(expected) >= 32 and secrets.compare_digest(received.encode(), expected.encode())

async def validate_config():
    if min(len(PROXY_API_KEY), len(TOKEN_QUERY_API_KEY)) < 32 or PROXY_API_KEY == TOKEN_QUERY_API_KEY:
        raise RuntimeError("Configure distinct proxy/query keys with at least 32 characters")
    if RETENTION_DAYS < 1 or MAX_STORAGE < 4096 or MAX_CONCURRENT < 1:
        raise RuntimeError("Invalid resource limits")


TOKEN_QUERY_API_KEY = os.getenv(
    "TOKEN_QUERY_API_KEY", ""
)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("ollama-token-proxy")

write_lock = asyncio.Lock()

HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}

TOKEN_PATHS = {
    "api/chat",
    "api/generate",
    "v1/chat/completions",
    "v1/completions",
}

CORRELATION_PATTERN = re.compile(
    r"^[0-9]{1,24}-[0-9]{1,8}$"
)

# =========================================================
# 2. FUNÇÕES AUXILIARES
# =========================================================

def inteiro_valido(valor):
    return (
        isinstance(valor, int)
        and not isinstance(valor, bool)
        and 0 <= valor <= 2**53 - 1
    )


def obter_correlation_id(body, path):
    """
    Extrai correlation_id do JSON recebido.

    Remove o campo antes de encaminhar ao Ollama.
    """

    if path not in TOKEN_PATHS:
        return body, None, None

    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return body, None, None

    if not isinstance(payload, dict):
        return body, None, None

    model = payload.get("model")

    if not isinstance(model, str):
        model = None

    correlation_id = payload.pop(
        "correlation_id", None
    )

    if correlation_id is None:
        return body, None, model

    if (
        not isinstance(correlation_id, str)
        or not CORRELATION_PATTERN.fullmatch(
            correlation_id
        )
    ):
        logger.warning(
            "CORRELATION_ID_INVALIDO"
        )
        correlation_id = None

    cleaned_body = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")

    return cleaned_body, correlation_id, model


def extrair_tokens(
    payload,
    request_id,
    correlation_id,
    model
):
    """
    Compatível com API nativa e API OpenAI.
    """

    if not isinstance(payload, dict):
        return None

    entrada = payload.get(
        "prompt_eval_count"
    )

    saida = payload.get(
        "eval_count"
    )

    origem = "ollama_native_actual"

    if not (
        inteiro_valido(entrada)
        and inteiro_valido(saida)
    ):

        usage = payload.get("usage") or {}

        if not isinstance(usage, dict):
            return None

        entrada = usage.get(
            "prompt_tokens"
        )

        saida = usage.get(
            "completion_tokens"
        )

        origem = "ollama_openai_usage"

    if not (
        inteiro_valido(entrada)
        and inteiro_valido(saida)
    ):
        return None

    return {
        "event": "ollama_token_usage",
        "request_id": request_id,
        "correlation_id": correlation_id,
        "timestamp": int(time.time()),
        "model": (payload.get("model") if isinstance(payload.get("model"), str) else model),
        "input_tokens": entrada,
        "output_tokens": saida,
        "total_tokens": entrada + saida,
        "source": origem,
        "status": "real",
    }


def escrever_registro(registro):
    now = time.time()
    files = sorted(TOKEN_DIR.glob("token_usage-*.jsonl"))
    for file in files:
        if now - file.stat().st_mtime > RETENTION_DAYS * 86400:
            file.unlink()
    encoded = (json.dumps(registro, ensure_ascii=False) + "\n").encode()
    files = sorted(TOKEN_DIR.glob("token_usage-*.jsonl"))
    size = sum(f.stat().st_size for f in files)
    for file in files:
        if size + len(encoded) <= MAX_STORAGE:
            break
        size -= file.stat().st_size
        file.unlink()
    target = TOKEN_DIR / time.strftime("token_usage-%Y-%m-%d.jsonl", time.gmtime())
    fd = os.open(target, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "ab") as stream:
        stream.write(encoded)


def consultar_registros(correlation_id):
    registros, seen = [], set()
    cutoff = time.time() - RETENTION_DAYS * 86400
    for file in sorted(TOKEN_DIR.glob("token_usage-*.jsonl")):
        with file.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(r, dict) or r.get("correlation_id") != correlation_id:
                    continue
                rid = r.get("request_id")
                if not isinstance(rid, str) or not rid or rid in seen or r.get("timestamp", 0) < cutoff:
                    continue
                if r.get("status") == "real":
                    if not all(inteiro_valido(r.get(k)) for k in ("input_tokens", "output_tokens", "total_tokens")):
                        continue
                    if r["total_tokens"] != r["input_tokens"] + r["output_tokens"]:
                        continue
                seen.add(rid)
                registros.append(r)
    return registros

# =========================================================
# 3. REGISTRO DOS TOKENS
# =========================================================

async def registrar(
    payload,
    request_id,
    correlation_id,
    model,
    estado
):

    if estado["registrado"]:
        return

    registro = extrair_tokens(
        payload,
        request_id,
        correlation_id,
        model
    )

    if registro is None:
        return

    estado["usage"] = registro
    estado["registrado"] = True

    logger.info(
        "TOKEN_USAGE %s",
        json.dumps(
            registro,
            ensure_ascii=False
        )
    )


async def processar_json(
    texto,
    request_id,
    correlation_id,
    model,
    estado
):

    try:
        payload = json.loads(texto)
    except (ValueError, UnicodeDecodeError):
        return

    await registrar(
        payload,
        request_id,
        correlation_id,
        model,
        estado
    )


# =========================================================
# 4. HEALTH CHECK
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "proxy": "ollama-token-proxy",
        "storage": "jsonl",
        "correlation": "extra_body",
        "token_query": "enabled"
        if TOKEN_QUERY_API_KEY
        else "not_configured",
        "api": [
            "ollama-native",
            "openai-compatible"
        ]
    }


# =========================================================
# 5. CONSULTA DE TOKENS REAIS
# =========================================================

@app.get("/token-usage")
async def token_usage(
    request: Request,
    correlation_id: str = ""
):
    """
    Exemplo:

    GET /token-usage?correlation_id=2672-0

    Cabeçalho obrigatório:

    X-Token-Query-Key: chave_configurada
    """

    if not authorized(request.headers.get("x-token-query-key", ""), TOKEN_QUERY_API_KEY):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if not CORRELATION_PATTERN.fullmatch(correlation_id):
        return JSONResponse(status_code=400, content={"error": "Invalid correlation_id"})
    async with write_lock:
        records = await asyncio.to_thread(consultar_registros, correlation_id)
    real = [r for r in records if r.get("status") == "real"]
    complete = bool(records) and len(real) == len(records)
    by_model = {}
    for r in real:
        m = by_model.setdefault(r["model"], {"input_tokens": 0, "output_tokens": 0, "requests": 0})
        m["input_tokens"] += r["input_tokens"]
        m["output_tokens"] += r["output_tokens"]
        m["requests"] += 1
    return {"correlation_id": correlation_id, "found": bool(records),
            "status": "real" if complete else "unavailable",
            "input_tokens": sum(r["input_tokens"] for r in real) if complete else None,
            "output_tokens": sum(r["output_tokens"] for r in real) if complete else None,
            "total_tokens": sum(r["total_tokens"] for r in real) if complete else None,
            "requests": len(records), "by_model": by_model,
            "unavailable_requests": len(records)-len(real), "records": records}

# =========================================================
# 6. PROXY OLLAMA / OPENAI
# =========================================================

@app.api_route(
    "/{path:path}",
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS"
    ],
)
async def proxy_ollama(
    path: str,
    request: Request
):

    if not authorized(request.headers.get("authorization", "").removeprefix("Bearer "), PROXY_API_KEY):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if not ((request.method == "POST" and path in TOKEN_PATHS) or (request.method == "GET" and path in ALLOWED_GET)):
        return JSONResponse(status_code=403, content={"error": "Endpoint not allowed"})
    if request.url.query:
        return JSONResponse(status_code=400, content={"error": "Query parameters not supported"})
    request_id = uuid.uuid4().hex

    url = f"{OLLAMA_URL}/{path}"

    if request.url.query:
        url += f"?{request.url.query}"

    original_body = bytearray()
    async for chunk in request.stream():
        original_body.extend(chunk)
        if len(original_body) > MAX_BODY:
            return JSONResponse(status_code=413, content={"error": "Request too large"})
    original_body = bytes(original_body)

    body, correlation_id, model = (
        obter_correlation_id(
            original_body,
            path
        )
    )

    if path in TOKEN_PATHS:
        if not correlation_id:
            return JSONResponse(status_code=400, content={"error": "Valid correlation_id required"})
        if not isinstance(model, str) or not model or len(model) > 200:
            return JSONResponse(status_code=400, content={"error": "Valid model required"})
        payload = json.loads(body)
        if path.startswith("v1/") and payload.get("stream", True):
            payload["stream_options"] = {"include_usage": True}
        body = json.dumps(payload).encode()

        logger.info(
            "REQUEST_TRACKING %s",
            json.dumps({
                "request_id": request_id,
                "correlation_id": correlation_id,
                "model": model,
                "path": path,
            }, ensure_ascii=False)
        )

    # Deliberately do not forward Authorization, cookies or query keys.
    headers = {"content-type": "application/json", "accept-encoding": "identity"}

    client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=30,
            read=REQUEST_TIMEOUT,
            write=120,
            pool=30
        ), trust_env=False, follow_redirects=False
    )

    try:

        upstream_request = client.build_request(
            request.method,
            url,
            content=body,
            headers=headers
        )

        upstream = await client.send(
            upstream_request,
            stream=True
        )

    except httpx.HTTPError:

        await client.aclose()

        logger.warning("Falha ao conectar ao Ollama")

        if path in TOKEN_PATHS:
            async with write_lock:
                await asyncio.to_thread(escrever_registro, {
                    "event": "ollama_token_usage", "request_id": request_id,
                    "correlation_id": correlation_id, "model": model,
                    "timestamp": int(time.time()), "status": "unavailable",
                    "input_tokens": None, "output_tokens": None, "total_tokens": None,
                    "source": "upstream_unavailable"})

        return Response(
            content=json.dumps({
                "error": "Ollama indisponível"
            }),
            status_code=502,
            media_type="application/json"
        )

    estado = {
        "registrado": False, "usage": None, "complete": False
    }

    async def gerar_interno():

        buffer = b""

        try:

            async for bloco in upstream.aiter_bytes():

                # Encaminha a resposta original ao n8n.
                yield bloco

                if path not in TOKEN_PATHS:
                    continue

                buffer += bloco

                # Processa NDJSON e SSE.
                while b"\n" in buffer:

                    linha, buffer = buffer.split(
                        b"\n", 1
                    )

                    if len(linha) > MAX_LINE:
                        raise ValueError("Upstream line limit")
                    texto = linha.decode(
                        "utf-8",
                        errors="replace"
                    ).strip()

                    if texto.startswith("data:"):
                        texto = texto[5:].strip()

                    if texto and texto != "[DONE]":

                        await processar_json(
                            texto,
                            request_id,
                            correlation_id,
                            model,
                            estado
                        )

                if len(buffer) > MAX_LINE:
                    raise ValueError("Upstream buffer limit")

            # JSON sem quebra de linha.
            if path in TOKEN_PATHS and buffer:

                texto = buffer.decode(
                    "utf-8",
                    errors="replace"
                ).strip()

                if texto.startswith("data:"):
                    texto = texto[5:].strip()

                if texto and texto != "[DONE]":

                    await processar_json(
                        texto,
                        request_id,
                        correlation_id,
                        model,
                        estado
                    )

            estado["complete"] = upstream.is_success
        finally:
            async def finish():
                try:
                    record = estado["usage"] if estado["complete"] else None
                    if path in TOKEN_PATHS:
                        if record is None:
                            record = {"event": "ollama_token_usage", "request_id": request_id,
                                      "correlation_id": correlation_id, "model": model,
                                      "timestamp": int(time.time()), "status": "unavailable",
                                      "input_tokens": None, "output_tokens": None, "total_tokens": None,
                                      "source": "missing_or_incomplete_usage"}
                        async with write_lock:
                            await asyncio.to_thread(escrever_registro, record)
                finally:
                    await upstream.aclose()
                    await client.aclose()
            task = asyncio.create_task(finish())
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                await task

    async def gerar():
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with aclosing(gerar_interno()) as stream:
                async for chunk in stream:
                    yield chunk

    response_headers = {"content-type": upstream.headers.get("content-type", "application/json"),
                        "cache-control": "no-store"}

    return StreamingResponse(
        gerar(),
        status_code=upstream.status_code,
        headers=response_headers
    )


class Admission:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        global active
        if scope["type"] != "http" or scope.get("path") == "/health":
            return await self.app(scope, receive, send)
        if active >= MAX_CONCURRENT:
            return await JSONResponse(status_code=429, content={"error": "Capacity reached"})(scope, receive, send)
        active += 1
        try:
            await self.app(scope, receive, send)
        finally:
            active -= 1

app.add_middleware(Admission)
