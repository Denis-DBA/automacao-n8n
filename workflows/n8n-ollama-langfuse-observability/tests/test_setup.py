import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('mode',['A','B'])
def test_configure_and_rerun_preserve_env(tmp_path,monkeypatch,mode):
    spec=importlib.util.spec_from_file_location('setup_under_test',ROOT/'scripts/setup.py')
    setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
    shutil.copy(ROOT/'.env.example',tmp_path/'.env.example')
    shutil.copytree(ROOT/'workflows',tmp_path/'workflows')
    monkeypatch.setattr(setup,'ROOT',tmp_path)
    monkeypatch.setattr(setup.shutil,'which',lambda _:True)
    calls=[]
    monkeypatch.setattr(setup,'run',lambda *args,**kwargs:calls.append(args))
    answers=iter([mode]+['']*20)
    monkeypatch.setattr('builtins.input',lambda _:next(answers))
    monkeypatch.setattr(sys,'argv',['setup.py','--configure-only'])
    setup.main()
    initial=(tmp_path/'.env').read_bytes()
    env=setup.load_env(tmp_path/'.env')
    assert len(env['PROXY_API_KEY'])>=32 and env['PROXY_API_KEY']!=env['TOKEN_QUERY_API_KEY']
    assert env['INSTALL_MODE']==('full' if mode=='A' else 'existing')
    files=list((tmp_path/'generated').glob('*.json'))
    assert len(files)==2
    for file in files:
        data=json.loads(file.read_text())
        assert not any('credentials' in n for n in data['nodes'])
    setup.main()
    assert (tmp_path/'.env').read_bytes()==initial
    assert not any('up' in c or 'pull' in c for c in calls)


def test_endpoint_rejects_embedded_credentials():
    spec=importlib.util.spec_from_file_location('setup_validate_url',ROOT/'scripts/setup.py')
    setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
    # Synthetic invalid URL used to prove embedded credentials are rejected.
    for value in ['file:///tmp/config','http://user:synthetic@example.invalid','http://example.invalid?token=synthetic']:  # pragma: allowlist secret
        with pytest.raises(ValueError):setup.valid_url(value)
