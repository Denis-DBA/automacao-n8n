"""Smoke tests dos exports; nao importam nem executam workflows no n8n."""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.static


def test_workflows_present():
    directory = Path(__file__).resolve().parents[2] / "workflows"
    assert directory.is_dir(), "Diretorio workflows ausente"
    assert any(directory.rglob("*.json")), "Nenhum export JSON encontrado"


def test_export_has_required_structure(workflow_path):
    try:
        workflow = json.loads(workflow_path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as error:
        pytest.fail(f"Export JSON invalido: {error}")
    assert isinstance(workflow, dict), "Export deve ser um objeto"
    assert isinstance(workflow.get("name"), str) and workflow["name"].strip()
    assert isinstance(workflow.get("nodes"), list) and workflow["nodes"]
    assert isinstance(workflow.get("connections"), dict)


def test_nodes_have_valid_unique_identity(workflow_path):
    workflow = json.loads(workflow_path.read_text(encoding="utf-8-sig"))
    nodes = workflow["nodes"]
    assert isinstance(nodes, list) and nodes
    for node in nodes:
        assert isinstance(node, dict)
        for field in ("id", "name", "type"):
            assert isinstance(node.get(field), str) and node[field].strip(), field
        assert isinstance(node.get("parameters"), dict), node["name"]
        position = node.get("position")
        assert isinstance(position, list) and len(position) == 2, node["name"]
        assert all(type(value) in (int, float) for value in position), node["name"]
        assert type(node.get("typeVersion")) in (int, float), node["name"]
        assert node["typeVersion"] > 0, node["name"]
    for field in ("id", "name"):
        values = [node[field] for node in nodes]
        assert len(values) == len(set(values)), f"Nos com {field} duplicado"
