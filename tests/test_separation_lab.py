from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import unittest.mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / 'labs' / 'separation' / 'separate.py'
spec = importlib.util.spec_from_file_location('oss_separation_lab', MODULE_PATH)
separation = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(separation)


class SeparationLabTests(unittest.TestCase):
    def test_dry_run_writes_run_and_stage_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / 'song.flac'
            input_path.write_bytes(b'fake audio bytes')
            config_path = REPO_ROOT / 'labs' / 'separation' / 'configs' / 'demucs-htdemucs.json'

            run_dir = separation.run_lab(config_path, input_path, root / 'runs', dry_run=True)

            manifest = json.loads((run_dir / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['kind'], 'oss-separation-lab-run')
            self.assertEqual(manifest['status'], 'ok')
            self.assertTrue(manifest['dry_run'])
            self.assertEqual(len(manifest['stages']), 1)

            stage_path = run_dir / manifest['stages'][0]['path'] / 'stage.json'
            stage = json.loads(stage_path.read_text(encoding='utf-8'))
            self.assertEqual(stage['status'], 'dry-run')
            self.assertEqual(stage['returncode'], 0)
            self.assertIn('-m', stage['command'])
            self.assertIn('demucs', stage['command'])
            self.assertIn('htdemucs', stage['command'])

    def test_cascade_dry_run_resolves_previous_stage_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / 'song.flac'
            input_path.write_bytes(b'fake audio bytes')
            config_path = REPO_ROOT / 'labs' / 'separation' / 'configs' / 'demucs-vocal-then-instrumental.json'

            run_dir = separation.run_lab(config_path, input_path, root / 'runs', dry_run=True)

            manifest = json.loads((run_dir / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['status'], 'ok')
            self.assertEqual(len(manifest['stages']), 2)
            first, second = manifest['stages']
            self.assertEqual(first['id'], 'stage-01-vocal-instrumental')
            self.assertEqual(second['id'], 'stage-02-instrumental-stems')

            second_stage = json.loads((run_dir / second['path'] / 'stage.json').read_text(encoding='utf-8'))
            self.assertIn('--two-stems', json.loads((run_dir / first['path'] / 'stage.json').read_text(encoding='utf-8'))['command'])
            self.assertIn('stage-01-vocal-instrumental', second_stage['input'])
            self.assertIn('no_vocals.wav', second_stage['input'])

    def test_engine_python_uses_override(self):
        with unittest.mock.patch.dict('os.environ', {'OSS_LAB_PYTHON': '/custom/python'}):
            self.assertEqual(separation.engine_python(), '/custom/python')

    def test_auto_device_prefers_cuda_when_torch_reports_cuda(self):
        completed = unittest.mock.Mock(returncode=0, stdout='cuda\n')
        with unittest.mock.patch('subprocess.run', return_value=completed):
            self.assertEqual(separation.detect_torch_device('/custom/python'), 'cuda')

    def test_auto_device_falls_back_to_cpu_when_probe_fails(self):
        completed = unittest.mock.Mock(returncode=1, stdout='')
        with unittest.mock.patch('subprocess.run', return_value=completed):
            self.assertEqual(separation.detect_torch_device('/custom/python'), 'cpu')

    def test_lab_device_override_forces_cuda_without_probe(self):
        with unittest.mock.patch.dict('os.environ', {'OSS_LAB_DEVICE': 'cuda:0'}):
            with unittest.mock.patch('subprocess.run') as run:
                self.assertEqual(separation.detect_torch_device('/custom/python'), 'cuda:0')
                run.assert_not_called()

    def test_demucs_auto_device_is_written_to_command(self):
        with unittest.mock.patch('subprocess.run', return_value=unittest.mock.Mock(returncode=0, stdout='cuda\n')):
            command, device = separation.demucs_command(
                {'engine': 'demucs', 'model': 'htdemucs', 'device': 'auto'},
                Path('/tmp/song.flac'),
                Path('/tmp/run'),
            )
        self.assertEqual(device, 'cuda')
        self.assertIn('-d', command)
        self.assertIn('cuda', command)

    def test_missing_input_is_rejected_before_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = REPO_ROOT / 'labs' / 'separation' / 'configs' / 'demucs-htdemucs.json'

            with self.assertRaises(ValueError):
                separation.run_lab(config_path, root / 'missing.flac', root / 'runs', dry_run=True)

            self.assertFalse((root / 'runs').exists())

    def test_unsupported_engine_marks_manifest_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / 'song.flac'
            input_path.write_bytes(b'fake audio bytes')
            config_path = root / 'bad.json'
            config_path.write_text(json.dumps({
                'schema': 1,
                'name': 'bad-engine',
                'mode': 'test',
                'stages': [
                    {'id': 'stage-01-bad', 'engine': 'not-real', 'model': 'x'}
                ],
            }), encoding='utf-8')

            with self.assertRaises(ValueError):
                separation.run_lab(config_path, input_path, root / 'runs', dry_run=True)

            manifests = list((root / 'runs').glob('*/manifest.json'))
            self.assertEqual(len(manifests), 1)
            manifest = json.loads(manifests[0].read_text(encoding='utf-8'))
            self.assertEqual(manifest['status'], 'error')


if __name__ == '__main__':
    unittest.main()
