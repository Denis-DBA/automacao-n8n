"""Scan explicit Git-index candidates only. Never scan private env/runtime files."""
import json
import argparse
from pathlib import Path
import subprocess

from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description='Audit explicit Git-index candidates, never private environments')
    parser.add_argument('--all-project',action='store_true',help='Examine all indexed project files plus repository README/.gitignore')
    args=parser.parse_args()
    repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip())
    command=['git','ls-files','--cached','-z','--',ROOT.relative_to(repo).as_posix(),'.gitignore','README.md'] if args.all_project else ['git','diff','--cached','--name-only','--diff-filter=ACMR','-z']
    files=subprocess.check_output(command,cwd=repo).decode().split('\0')
    candidates=[repo/name for name in files if name]
    if not candidates:raise SystemExit('Nenhum arquivo staged para auditar')
    # Refuse stale index contents: the scanner must examine the publication version.
    subprocess.run(['git','diff','--exit-code','--quiet','--',*[str(f.relative_to(repo)) for f in candidates]],cwd=repo,check=True)
    for file in candidates:
        if file.name.startswith('.env') and file.name!='.env.example':raise SystemExit('Ambiente privado no índice; publicação bloqueada')
        if file.suffix in {'.jsonl','.db','.sqlite','.log','.bak'} or '.backup' in file.name:
            raise SystemExit('Arquivo privado/runtime no índice; publicação bloqueada')
    collection=SecretsCollection()
    with default_settings():
        for file in candidates:collection.scan_file(str(file))
    findings=collection.json()
    total=sum(len(items) for items in findings.values())
    print(f'Arquivos staged examinados: {len(candidates)}; achados detect-secrets: {total}')
    for name,items in findings.items():
        for item in items:print(f'{Path(name).relative_to(repo)}:{item["line_number"]}: {item["type"]}')
    if total:raise SystemExit(1)


if __name__=='__main__':main()
