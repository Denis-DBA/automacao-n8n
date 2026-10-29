"""Descoberta independente do diretorio de execucao."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / "workflows"
FILES = sorted(WORKFLOWS.rglob("*.json"))


@pytest.fixture(params=FILES, ids=lambda path: path.relative_to(ROOT).as_posix())
def workflow_path(request):
    return request.param
