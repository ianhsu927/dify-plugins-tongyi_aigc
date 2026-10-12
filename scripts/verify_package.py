"""Inspect a CLI-built archive and load its extracted SDK registration offline."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
import yaml

package = Path(sys.argv[1]).resolve()
with zipfile.ZipFile(package) as archive:
    names = set(archive.namelist())
    for name in names:
        path = Path(name)
        assert not path.is_absolute() and '..' not in path.parts, name
        assert not any(p in {'.git', '.github', '.venv', '__pycache__', 'tests', 'scripts', 'docs'} for p in path.parts), name
        assert not path.name.startswith('.env'), name
        assert path.suffix not in {'.pyc', '.difypkg', '.pem', '.key'}, name
    manifest = yaml.safe_load(archive.read('manifest.yaml'))
    assert manifest['version'] == '0.0.5'
    required = {'main.py', 'requirements.txt', manifest['privacy'], '_assets/'+manifest['icon']}
    for provider_path in manifest['plugins']['tools']:
        required.add(provider_path)
        provider = yaml.safe_load(archive.read(provider_path))
        required.add(provider['extra']['python']['source'])
        for tool_path in provider['tools']:
            required.add(tool_path)
            required.add(yaml.safe_load(archive.read(tool_path))['extra']['python']['source'])
    assert required <= names, required - names
    with tempfile.TemporaryDirectory() as directory:
        archive.extractall(directory)
        environment = dict(os.environ)
        environment.pop('PYTHONPATH', None)
        subprocess.run([sys.executable, '-c',
            'from dify_plugin.config.config import DifyPluginEnv; '
            'from dify_plugin.core.plugin_registration import PluginRegistration; '
            'r=PluginRegistration(DifyPluginEnv()); '
            'assert len(r.tools_mapping["tongyi_aigc"][2]) == 19; '
            'print("Extracted package: 19 SDK tool registrations OK")'],
            cwd=directory, env=environment, check=True)
print(f'Package structure OK: {len(names)} files; {package.name}')
