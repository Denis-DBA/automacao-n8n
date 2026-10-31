"""A real clean Ollama returned data:null and crashed the installer after up."""
import importlib.util
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]


def test_first_install_without_models_and_without_download_consent(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('setup_empty_install',ROOT/'scripts/setup.py')
    setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
    shutil.copy(ROOT/'.env.example',tmp_path/'.env.example')
    shutil.copytree(ROOT/'workflows',tmp_path/'workflows')
    monkeypatch.setattr(setup,'ROOT',tmp_path)
    monkeypatch.setattr(setup.shutil,'which',lambda _:True)
    calls=[];monkeypatch.setattr(setup,'run',lambda *args,**kw:calls.append(args))
    monkeypatch.setattr(setup.subprocess,'check_output',lambda *args,**kw:'')
    monkeypatch.setattr(setup,'request_json',lambda url,*args:{'status':'ok'} if url.endswith('/health') else {'object':'list','data':None})
    class Socket:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def bind(self,*args):pass
    monkeypatch.setattr(setup.socket,'socket',Socket)
    answers=iter(['A','','','','','','','','s','N'])
    monkeypatch.setattr('builtins.input',lambda _:next(answers))
    monkeypatch.setattr(sys,'argv',['setup.py'])
    setup.main()
    assert any('up' in cmd for cmd in calls)
    assert not any('pull' in cmd for cmd in calls)
