from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / 'labs' / 'separation' / 'tools' / 'compare_runs.py'
spec = importlib.util.spec_from_file_location('oss_compare_runs', MODULE_PATH)
compare_runs = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(compare_runs)


@unittest.skipIf(shutil.which('ffmpeg') is None or shutil.which('ffprobe') is None, 'ffmpeg/ffprobe required')
class CompareRunsTests(unittest.TestCase):
    def make_run(self, root: Path, name: str, source: Path) -> Path:
        run = root / name
        stage = run / 'stage'
        stems = stage / 'stems' / 'model' / 'song'
        stems.mkdir(parents=True)
        shutil.copy(source, stems / 'bass.wav')
        (run / 'manifest.json').write_text(json.dumps({
            'config': {'name': name},
            'input': {'path': str(source)},
            'stages': [{
                'id': 'stage',
                'path': 'stage',
                'outputs': [{'path': 'stems/model/song/bass.wav'}],
            }],
        }), encoding='utf-8')
        return run

    def test_compare_runs_writes_report_audio_and_reaper_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.wav'
            subprocess.run([
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-f', 'lavfi', '-i', 'sine=frequency=220:duration=1',
                '-ar', '44100', '-ac', '2', str(source),
            ], check=True)
            run_a = self.make_run(root, 'run-a', source)
            run_b = self.make_run(root, 'run-b', source)

            out = compare_runs.compare_runs([run_a, run_b], root / 'compare', ['a', 'b'])

            self.assertTrue((out / 'COMPARISON.md').is_file())
            self.assertTrue((out / 'comparison.rpp').is_file())
            self.assertTrue((out / '01-a-reconstruction.wav').is_file())
            self.assertTrue((out / '02-b-reconstruction.wav').is_file())
            summary = json.loads((out / 'comparison.json').read_text(encoding='utf-8'))
            self.assertEqual(len(summary['runs']), 2)


if __name__ == '__main__':
    unittest.main()
