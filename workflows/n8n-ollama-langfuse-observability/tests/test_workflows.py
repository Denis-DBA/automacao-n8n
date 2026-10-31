import importlib.util
from pathlib import Path


def test_public_artifacts():
    path=Path(__file__).resolve().parents[1]/'scripts/validate.py'
    spec=importlib.util.spec_from_file_location('validator',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.main()
