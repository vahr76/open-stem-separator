from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / 'labs' / 'separation' / 'tools' / 'measure_run.py'
spec = importlib.util.spec_from_file_location('oss_measure_run', MODULE_PATH)
measure_run = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(measure_run)


@unittest.skipIf(shutil.which('ffmpeg') is None or shutil.which('ffprobe') is None, 'ffmpeg/ffprobe required')
class MeasureRunTests(unittest.TestCase):
    def test_measure_perfect_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.wav'
            bass = root / 'run' / 'stage' / 'stems' / 'model' / 'song' / 'bass.wav'
            bass.parent.mkdir(parents=True)
            subprocess.run([
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-f', 'lavfi', '-i', 'sine=frequency=220:duration=1',
                '-ar', '44100', '-ac', '2', str(source),
            ], check=True)
            shutil.copy(source, bass)
            (root / 'run' / 'manifest.json').write_text(json.dumps({
                'config': {'name': 'unit'},
                'input': {'path': str(source)},
                'stages': [{
                    'id': 'stage',
                    'path': 'stage',
                    'outputs': [{'path': 'stems/model/song/bass.wav'}],
                }],
            }), encoding='utf-8')

            measurement = measure_run.measure_run(root / 'run')

            self.assertEqual(measurement['final_sum_output_count'], 1)
            self.assertLess(measurement['reconstruction_residual']['rms'], 1e-6)
            self.assertEqual(measurement['outputs'][0]['length_delta_frames'], 0)


if __name__ == '__main__':
    unittest.main()
