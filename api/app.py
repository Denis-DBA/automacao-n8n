import math

import cudf
from fastapi import FastAPI
from pydantic import BaseModel, Field, FiniteFloat

app = FastAPI(title="API RAPIDS")

class Dados(BaseModel):
    valores: list[FiniteFloat] = Field(min_length=1, max_length=100000)

@app.get("/health")
def health():
    teste = cudf.Series([1, 2, 3]).sum()
    return {
        "status": "ok",
        "cudf": cudf.__version__,
        "gpu_test": int(teste)
    }

@app.post("/analisar")
def analisar(dados: Dados):
    serie = cudf.Series(dados.valores, dtype="float64")

    def numero(valor):
        resultado = float(valor)
        return resultado if math.isfinite(resultado) else None

    return {
        "processamento": "GPU com RAPIDS/cuDF",
        "quantidade": len(serie),
        "soma": numero(serie.sum()),
        "media": numero(serie.mean()),
        "minimo": numero(serie.min()),
        "maximo": numero(serie.max())
    }
