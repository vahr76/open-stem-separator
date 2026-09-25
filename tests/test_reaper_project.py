from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / 'labs' / 'separation' / 'tools' / 'reaper_project.py'
spec = importlib.util.spec_from_file_location('oss_reaper_project', MODULE_PATH)
reaper_project = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(reaper_project)


class ReaperProjectTests(unittest.TestCase):
    def test_writes_tracks_from_manifest_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / 'run'
            stage = run / 'stage-01-demucs-htdemucs'
            stems = stage / 'stems' / 'htdemucs' / 'song'
            stems.mkdir(parents=True)
            for name in ['bass.wav', 'drums.wav']:
                (stems / name).write_bytes(b'wav')
            (run / 'manifest.json').write_text(json.dumps({
                'config': {'name': 'unit'},
                'stages': [{
                    'id': 'stage-01-demucs-htdemucs',
                    'path': 'stage-01-demucs-htdemucs',
                    'outputs': [
                        {'path': 'stems/htdemucs/song/bass.wav'},
                        {'path': 'stems/htdemucs/song/drums.wav'},
                    ],
                }],
            }), encoding='utf-8')

            output = reaper_project.write_reaper_project(run, root / 'out.rpp')

            text = output.read_text(encoding='utf-8')
            self.assertIn('<REAPER_PROJECT', text)
            self.assertIn('stage-01-demucs-htdemucs · bass', text)
            self.assertIn('stage-01-demucs-htdemucs · drums', text)
            self.assertIn('bass.wav', text)
            self.assertIn('SOURCE WAVE', text)


if __name__ == '__main__':
    unittest.main()
