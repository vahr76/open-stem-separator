import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import oss

def same_path(left, right):
    return Path(left).resolve() == Path(right).resolve()

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.patch = patch('oss.executable', side_effect=lambda name: '/bundle/bin/' + name)
        self.patch.start()
        self.addCleanup(self.patch.stop)


    def test_external_env_cleans_pyinstaller_variables(self):
        with patch.dict(oss.os.environ, {
            'LD_LIBRARY_PATH': '/tmp/pyinstaller',
            'LD_LIBRARY_PATH_ORIG': '/usr/lib',
            'PYTHONHOME': '/bad/python',
            'PYTHONPATH': '/bad/path',
            'PYI_TEST': '1',
            '_PYI_SPLASH_IPC': '2',
            'KEEP_ME': 'ok',
        }, clear=True):
            env = oss.external_env()
        self.assertEqual(env['LD_LIBRARY_PATH'], '/usr/lib')
        self.assertEqual(env['KEEP_ME'], 'ok')
        self.assertNotIn('PYTHONHOME', env)
        self.assertNotIn('PYTHONPATH', env)
        self.assertNotIn('PYI_TEST', env)
        self.assertNotIn('_PYI_SPLASH_IPC', env)

    def test_external_env_removes_pyinstaller_ld_without_original(self):
        with patch.dict(oss.os.environ, {'LD_LIBRARY_PATH': '/tmp/pyinstaller'}, clear=True), patch('oss.sys.frozen', True, create=True):
            env = oss.external_env()
        self.assertNotIn('LD_LIBRARY_PATH', env)

    def test_original_preserves_source(self):
        cmd = oss.command('https://example.org/song')
        self.assertEqual(cmd[cmd.index('--format') + 1], 'bestaudio')
        self.assertNotIn('--extract-audio', cmd)
        self.assertIn('--no-playlist', cmd)

    def test_mp3_uses_320k(self):
        cmd = oss.command('https://example.org/song', 'mp3')
        self.assertEqual(cmd[cmd.index('--audio-format') + 1], 'mp3')
        self.assertEqual(cmd[cmd.index('--audio-quality') + 1], '320K')

    def test_shell_characters_are_literal_argument(self):
        url = 'https://example.org/?a=$(touch%20bad)&b=1'
        self.assertEqual(oss.command(url)[-2:], ['--', url])

    def test_markdown_url_is_normalized(self):
        url = '[https://example.org/song](https://example.org/song)'
        self.assertEqual(oss.command(url)[-1], 'https://example.org/song')

    def test_guess_artist_track_from_title(self):
        guess = oss.guess_artist_track({'title': 'Iron Butterfly - In A Gadda Da Vida (Official Video)'})
        self.assertEqual(guess['artist'], 'Iron_Butterfly')
        self.assertEqual(guess['track'], 'In_A_Gadda_Da_Vida')
        self.assertEqual(guess['source'], 'title')

    def test_guess_reversed_lyrics_title(self):
        guess = oss.guess_artist_track({'title': "You've Got to Hide Your Love Away - The Beatles Lyrics Sub. Espanol"})
        self.assertEqual(guess['artist'], 'The_Beatles')
        self.assertEqual(guess['track'], 'Youve_Got_to_Hide_Your_Love_Away')

    def test_unsorted_fallback_keeps_marker(self):
        guess = oss.guess_artist_track({'title': 'No clear separator'})
        self.assertEqual(guess['artist'], '_unsorted')

    def test_create_project_writes_metadata_and_project_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            project = oss.create_project('https://example.org/song', directory, {
                'title': 'Artist - Track (Official Video)',
                'webpage_url': 'https://example.org/song',
                'uploader': 'Third Party Channel',
                'duration': 123,
                'id': 'abc',
            })
            self.assertTrue(same_path(project, Path(directory) / 'Artist' / 'Track'))
            metadata = json.loads((project / 'metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['artist_guess'], 'Artist')
            self.assertEqual(metadata['track_guess'], 'Track')
            manifest = json.loads((project / 'project.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['schema'], 1)
            self.assertEqual(manifest['kind'], 'song-project')
            self.assertEqual(manifest['source']['url'], 'https://example.org/song')
            self.assertEqual(manifest['source']['extractor'], 'yt-dlp')
            self.assertEqual(manifest['source']['id'], 'abc')
            self.assertEqual(manifest['identity']['artist'], 'Artist')
            self.assertEqual(manifest['identity']['track'], 'Track')
            self.assertEqual(manifest['media'], [])
            self.assertEqual(manifest['stems'], [])

    def test_create_project_preserves_existing_manifest_lists(self):
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory) / 'Artist' / 'Track'
            project_dir.mkdir(parents=True)
            existing = {
                'created_at': '2026-01-01T00:00:00+00:00',
                'media': [{'path': 'old.flac'}],
                'stems': [{'name': 'bass'}],
                'analysis': {'tempo': 'analysis/detected/tempo.json'},
                'lyrics': {'synced': 'lyrics/detected.lrc'},
                'exports': [{'path': 'exports/mix.wav'}],
                'notes': ['keep me'],
            }
            (project_dir / 'project.json').write_text(json.dumps(existing), encoding='utf-8')
            project = oss.create_project('https://example.org/song', directory, {
                'title': 'Artist - Track',
                'webpage_url': 'https://example.org/song',
                'id': 'abc',
            })
            manifest = json.loads((project / 'project.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['created_at'], existing['created_at'])
            self.assertEqual(manifest['media'], existing['media'])
            self.assertEqual(manifest['stems'], existing['stems'])
            self.assertEqual(manifest['analysis'], existing['analysis'])
            self.assertEqual(manifest['lyrics'], existing['lyrics'])
            self.assertEqual(manifest['exports'], existing['exports'])
            self.assertEqual(manifest['notes'], existing['notes'])
            self.assertIn('updated_at', manifest)


    def test_register_project_media_records_downloaded_files(self):
        with tempfile.TemporaryDirectory() as directory:
            project = oss.create_project('https://example.org/song', directory, {
                'title': 'Artist - Track',
                'webpage_url': 'https://example.org/song',
                'id': 'abc',
            })
            media_file = project / 'Artist_-_Track.flac'
            media_file.write_bytes(b'audio')
            self.assertTrue(oss.register_project_media(project, 'flac', 'shortcut'))
            manifest = json.loads((project / 'project.json').read_text(encoding='utf-8'))
            self.assertEqual(len(manifest['media']), 1)
            self.assertEqual(manifest['media'][0]['path'], 'Artist_-_Track.flac')
            self.assertEqual(manifest['media'][0]['kind'], 'audio')
            self.assertEqual(manifest['media'][0]['profile'], 'flac')
            self.assertEqual(manifest['media'][0]['role'], 'shortcut')
            self.assertEqual(manifest['media'][0]['size'], 5)

    def test_register_project_media_deduplicates_and_ignores_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            project = oss.create_project('https://example.org/song', directory, {'title': 'Artist - Track'})
            (project / 'metadata.json').write_text('{}', encoding='utf-8')
            (project / 'project.json.part').write_text('partial', encoding='utf-8')
            media_file = project / 'video.mkv'
            media_file.write_bytes(b'video')
            self.assertTrue(oss.register_project_media(project, 'video', 'both-video'))
            self.assertFalse(oss.register_project_media(project, 'video', 'both-video'))
            manifest = json.loads((project / 'project.json').read_text(encoding='utf-8'))
            self.assertEqual(len(manifest['media']), 1)
            self.assertEqual(manifest['media'][0]['path'], 'video.mkv')
            self.assertEqual(manifest['media'][0]['kind'], 'video')

    def test_invalid_urls(self):
        for url in ('file:///tmp/song', '--exec=bad', 'https://', 'https://u:p@example.org'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                oss.command(url)

    def test_missing_conversion_dependency(self):
        with patch('oss.executable', side_effect=lambda n: '/bin/yt-dlp' if n == 'yt-dlp' else None):
            with self.assertRaisesRegex(ValueError, 'ffmpeg'):
                oss.command('https://example.org', 'wav')
            self.assertTrue(oss.command('https://example.org', formats=True))

    def test_video_profile_is_complete_video(self):
        cmd = oss.command('https://example.org/song', 'video')
        self.assertEqual(cmd[cmd.index('--format') + 1], 'bestvideo+bestaudio/best[vcodec!=none][acodec!=none]')

    def test_both_shortcut_runs_video_and_audio(self):
        calls = []

        def fake_run(args):
            calls.append(args)
            return 0

        with tempfile.TemporaryDirectory() as directory, patch('oss.default_downloads', return_value=Path(directory)), patch('oss.fetch_metadata', return_value={'title': 'Artist - Song'}), patch('oss.run', side_effect=fake_run), patch('oss.history_path', return_value=Path(directory) / 'history.jsonl'):
            self.assertEqual(oss.main(['both', 'https://example.org/song']), 0)
        self.assertTrue(any(same_path(value, Path(directory) / 'Artist' / 'Song') for value in calls[0]))
        self.assertTrue(any(same_path(value, Path(directory) / 'Artist' / 'Song') for value in calls[1]))
        self.assertEqual(calls[0][calls[0].index('--format') + 1], 'bestvideo+bestaudio/best[vcodec!=none][acodec!=none]')
        self.assertEqual(calls[1][calls[1].index('--format') + 1], 'bestaudio')
        self.assertEqual(calls[0][calls[0].index('--output') + 1], '%(title).160B - video.%(ext)s')
        self.assertEqual(calls[1][calls[1].index('--output') + 1], '%(title).160B - audio.%(ext)s')

    def test_filenames_are_restricted(self):
        cmd = oss.command('https://example.org/song')
        self.assertIn('--restrict-filenames', cmd)

    def test_output_template_has_no_video_id(self):
        cmd = oss.command('https://example.org/song')
        self.assertEqual(cmd[cmd.index('--output') + 1], '%(title).160B.%(ext)s')

    def test_labeled_output_template_has_no_video_id(self):
        cmd = oss.command('https://example.org/song', label='audio')
        self.assertEqual(cmd[cmd.index('--output') + 1], '%(title).160B - audio.%(ext)s')

    def test_playlist_opt_in(self):
        self.assertIn('--yes-playlist', oss.command('https://example.org', playlist=True))

    def test_thumbnails_are_disabled_by_default(self):
        cmd = oss.command('https://example.org/song')
        self.assertIn('--no-write-thumbnail', cmd)
        self.assertIn('--no-embed-thumbnail', cmd)

    def test_thumbnail_modes(self):
        self.assertIn('--write-thumbnail', oss.command('https://example.org/song', thumbnail_mode='write'))
        self.assertIn('--embed-thumbnail', oss.command('https://example.org/song', thumbnail_mode='embed'))

    def test_cookie_file(self):
        with tempfile.TemporaryDirectory() as directory:
            cookies = Path(directory) / 'cookies.txt'
            cookies.write_text('# Netscape HTTP Cookie File\n', encoding='utf-8')
            cmd = oss.command('https://example.org/song', cookies_file=cookies)
            self.assertTrue(same_path(cmd[cmd.index('--cookies') + 1], cookies))

    def test_cookie_file_must_exist(self):
        with self.assertRaisesRegex(ValueError, 'cookies'):
            oss.command('https://example.org/song', cookies_file='/missing/cookies.txt')

    def test_browser_cookies(self):
        cmd = oss.command('https://example.org/song', cookies_from_browser='firefox')
        self.assertEqual(cmd[cmd.index('--cookies-from-browser') + 1], 'firefox')

    def test_cookie_sources_are_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            cookies = Path(directory) / 'cookies.txt'
            cookies.write_text('# Netscape HTTP Cookie File\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'archivo de cookies'):
                oss.command('https://example.org/song', cookies_file=cookies, cookies_from_browser='firefox')

    def test_cookie_retry_happens_automatically(self):
        first = type('Result', (), {'returncode': 1, 'stdout': '', 'stderr': 'Sign in to confirm you are not a bot'})()
        second = type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()
        calls = []

        def fake_run(args):
            calls.append(args)
            return first if len(calls) == 1 else second

        with patch('oss.run_process', side_effect=fake_run), patch('oss.detected_browsers', return_value=['firefox']):
            self.assertEqual(oss.run(['yt-dlp', '--paths', tempfile.gettempdir(), '--', 'https://example.org']), 0)
        self.assertNotIn('--cookies-from-browser', calls[0])
        self.assertEqual(calls[1][calls[1].index('--cookies-from-browser') + 1], 'firefox')

    def test_cookie_retry_is_not_used_when_cookies_are_explicit(self):
        result = type('Result', (), {'returncode': 1, 'stdout': '', 'stderr': 'cookies required'})()
        with patch('oss.run_process', return_value=result) as run_process, patch('oss.detected_browsers', return_value=['firefox']):
            self.assertEqual(oss.run(['yt-dlp', '--cookies-from-browser', 'chrome', '--paths', tempfile.gettempdir(), '--', 'https://example.org']), 1)
        self.assertEqual(run_process.call_count, 1)

    def test_cookie_retry_tries_next_detected_browser(self):
        first = type('Result', (), {'returncode': 1, 'stdout': '', 'stderr': 'cookies required'})()
        second = type('Result', (), {'returncode': 1, 'stdout': '', 'stderr': 'could not copy chrome cookie database'})()
        third = type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()
        calls = []

        def fake_run(args):
            calls.append(args)
            return (first, second, third)[len(calls) - 1]

        with patch('oss.run_process', side_effect=fake_run), patch('oss.detected_browsers', return_value=['chrome', 'firefox']):
            self.assertEqual(oss.run(['yt-dlp', '--paths', tempfile.gettempdir(), '--', 'https://example.org']), 0)
        self.assertEqual(calls[1][calls[1].index('--cookies-from-browser') + 1], 'chrome')
        self.assertEqual(calls[2][calls[2].index('--cookies-from-browser') + 1], 'firefox')

    def test_menu_download_asks_only_url_and_format(self):
        answers = iter(('https://example.org/song', '1', '3'))
        with tempfile.TemporaryDirectory() as directory, patch('builtins.input', side_effect=lambda prompt='': next(answers)), patch('oss.default_downloads', return_value=Path(directory)), patch('oss.fetch_metadata', return_value={'title': 'Artist - Song'}), patch('oss.check_ytdlp_update'), patch('oss.run') as run:
            run.return_value = 0
            self.assertEqual(oss.menu(), 0)
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[cmd.index('--format') + 1], 'bestaudio/best')
            self.assertEqual(cmd[cmd.index('--audio-format') + 1], 'flac')

    def test_menu_defaults_to_download_and_original(self):
        answers = iter(('https://example.org/song', '', ''))
        with tempfile.TemporaryDirectory() as directory, patch('builtins.input', side_effect=lambda prompt='': next(answers)), patch('oss.default_downloads', return_value=Path(directory)), patch('oss.fetch_metadata', return_value={'title': 'Artist - Song'}), patch('oss.check_ytdlp_update'), patch('oss.run') as run:
            run.return_value = 0
            self.assertEqual(oss.menu(), 0)
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[cmd.index('--format') + 1], 'bestaudio')

    def test_menu_both_mp4(self):
        answers = iter(('https://example.org/song', '3', '2'))
        with tempfile.TemporaryDirectory() as directory, patch('builtins.input', side_effect=lambda prompt='': next(answers)), patch('oss.default_downloads', return_value=Path(directory)), patch('oss.fetch_metadata', return_value={'title': 'Artist - Song'}), patch('oss.check_ytdlp_update'), patch('oss.run') as run, patch('oss.history_path', return_value=Path(directory) / 'history.jsonl'):
            run.return_value = 0
            self.assertEqual(oss.menu(), 0)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(commands[0][commands[0].index('--format') + 1], 'bestvideo+bestaudio/best[vcodec!=none][acodec!=none]')
            self.assertEqual(commands[1][commands[1].index('--audio-format') + 1], 'wav')

    def test_direct_url_shortcut(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.run') as run, patch('oss.history_path', return_value=Path(directory) / 'history.jsonl'):
            run.return_value = 0
            self.assertEqual(oss.main(['https://example.org/song']), 0)
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[cmd.index('--format') + 1], 'bestaudio')

    def test_profile_shortcut(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.default_downloads', return_value=Path(directory)), patch('oss.fetch_metadata', return_value={'title': 'Artist - Song'}), patch('oss.run') as run:
            run.return_value = 0
            self.assertEqual(oss.main(['flac', 'https://example.org/song']), 0)
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[cmd.index('--audio-format') + 1], 'flac')

    def test_engine_failure_propagates(self):
        with patch('oss.subprocess.run') as run:
            run.return_value.returncode = 7
            run.return_value.stdout = ''
            run.return_value.stderr = ''
            self.assertEqual(oss.run(['engine']), 7)

    def test_output_write_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'Nueva carpeta'
            oss.prepare_output(['engine', '--paths', str(target)])
            self.assertTrue(target.is_dir())
            self.assertEqual(list(target.iterdir()), [])

    def test_configure_saves_downloads_dir(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'
            downloads = Path(directory) / 'Downloads'
            with patch.object(oss, 'CONFIG_PATH', config):
                self.assertEqual(oss.configure(downloads, 'online'), 0)
                self.assertTrue(same_path(oss.load_config(config)['downloads_dir'], downloads))
                self.assertEqual(oss.load_config(config)['install_mode'], 'online')


    def test_global_config_flag_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'isolated.json'
            downloads = Path(directory) / 'Downloads'
            self.assertEqual(oss.main(['--config', str(config), 'configure', '--downloads-dir', str(downloads)]), 0)
            self.assertTrue(same_path(oss.load_config(config)['downloads_dir'], downloads))

    def test_config_env_dir_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            config_dir = Path(directory) / 'cfg'
            downloads = Path(directory) / 'Downloads'
            with patch.dict('os.environ', {'OSS_CONFIG_DIR': str(config_dir)}), patch.object(oss, '_ACTIVE_CONFIG_PATH', None):
                self.assertEqual(oss.configure(downloads), 0)
                self.assertTrue(same_path(oss.load_config(config_dir / 'config.json')['downloads_dir'], downloads))

    def test_command_uses_configured_downloads_dir(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'
            downloads = Path(directory) / 'Chosen'
            oss.save_config({'downloads_dir': downloads}, config)
            with patch.object(oss, 'CONFIG_PATH', config):
                cmd = oss.command('https://example.org/song')
                self.assertTrue(same_path(cmd[cmd.index('--paths') + 1], downloads))


    def test_history_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'history.jsonl'
            oss.append_history({'url': 'https://example.org/song', 'profile': 'flac', 'status': 'ok'}, history)
            rows = oss.read_history(path=history)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['profile'], 'flac')
            self.assertEqual(rows[0]['status'], 'ok')
            self.assertIn('timestamp', rows[0])

    def test_shortcut_records_history(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.default_downloads', return_value=Path(directory) / 'downloads'), patch('oss.fetch_metadata', return_value={'title': 'Artist - Song'}), patch('oss.run', return_value=0), patch('oss.history_path', return_value=Path(directory) / 'history.jsonl'):
            self.assertEqual(oss.main(['flac', 'https://example.org/song']), 0)
            rows = oss.read_history(path=Path(directory) / 'history.jsonl')
            self.assertEqual(rows[-1]['profile'], 'flac')
            self.assertEqual(rows[-1]['status'], 'ok')
            self.assertEqual(rows[-1]['artist'], 'Artist')
            self.assertEqual(rows[-1]['track'], 'Song')

    def test_history_command_prints_table(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.history_path', return_value=Path(directory) / 'history.jsonl'), patch('builtins.print') as printer:
            oss.append_history({'url': 'https://example.org/song', 'profile': 'mp3', 'status': 'ok', 'artist': 'Artist', 'track': 'Song'})
            self.assertEqual(oss.main(['history', '--limit', '1']), 0)
            output = '\n'.join(call.args[0] for call in printer.call_args_list)
            self.assertIn('Fecha', output)
            self.assertIn('Artist', output)
            self.assertIn('Song', output)

    def test_history_command_json_output(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.history_path', return_value=Path(directory) / 'history.jsonl'), patch('builtins.print') as printer:
            oss.append_history({'url': 'https://example.org/song', 'profile': 'mp3', 'status': 'ok'})
            self.assertEqual(oss.main(['history', '--limit', '1', '--json']), 0)
            self.assertIn('"profile": "mp3"', printer.call_args.args[0])


    def test_config_command_prints_paths(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.CONFIG_PATH', Path(directory) / 'config.json'), patch('builtins.print') as printer:
            self.assertEqual(oss.main(['config']), 0)
            output = '\n'.join(call.args[0] for call in printer.call_args_list)
            self.assertIn('Config:', output)
            self.assertIn('Descargas:', output)
            self.assertIn('Historial:', output)

    def test_last_command_prints_last_history_entry(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.history_path', return_value=Path(directory) / 'history.jsonl'), patch('builtins.print') as printer:
            oss.append_history({'url': 'https://example.org/song', 'profile': 'flac', 'status': 'ok', 'artist': 'Artist', 'track': 'Song', 'project_dir': str(Path(directory) / 'Artist' / 'Song')})
            self.assertEqual(oss.main(['last']), 0)
            output = '\n'.join(call.args[0] for call in printer.call_args_list)
            self.assertIn('Última descarga:', output)
            self.assertIn('Artist', output)
            self.assertIn('Song', output)


    def test_project_command_prints_last_project_summary(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.history_path', return_value=Path(directory) / 'history.jsonl'), patch('builtins.print') as printer:
            project = oss.create_project('https://example.org/song', directory, {'title': 'Artist - Track', 'webpage_url': 'https://example.org/song'})
            media_file = project / 'track.flac'
            media_file.write_bytes(b'audio')
            oss.register_project_media(project, 'flac', 'shortcut')
            oss.append_history({'url': 'https://example.org/song', 'profile': 'flac', 'status': 'ok', 'project_dir': str(project)})
            self.assertEqual(oss.main(['project']), 0)
            output = '\n'.join(call.args[0] for call in printer.call_args_list)
            self.assertIn('Proyecto OSS:', output)
            self.assertIn('Artist', output)
            self.assertIn('Track', output)
            self.assertIn('Media: 1', output)
            self.assertIn('track.flac', output)

    def test_project_command_accepts_path(self):
        with tempfile.TemporaryDirectory() as directory, patch('builtins.print') as printer:
            project = oss.create_project('https://example.org/song', directory, {'title': 'Artist - Track'})
            self.assertEqual(oss.main(['project', str(project)]), 0)
            output = '\n'.join(call.args[0] for call in printer.call_args_list)
            self.assertIn(str(project), output)
            self.assertIn('Media: 0', output)

    def test_project_command_requires_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'project.json'):
                oss.print_project(directory)

    def test_open_downloads_uses_default_downloads(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.default_downloads', return_value=Path(directory)), patch('oss.open_path') as open_path:
            open_path.return_value = 0
            self.assertEqual(oss.main(['open', 'downloads']), 0)
            self.assertTrue(same_path(open_path.call_args.args[0], directory))

    def test_open_last_uses_history_project_dir(self):
        with tempfile.TemporaryDirectory() as directory, patch('oss.history_path', return_value=Path(directory) / 'history.jsonl'), patch('oss.open_path') as open_path:
            project = Path(directory) / 'Artist' / 'Song'
            oss.append_history({'url': 'https://example.org/song', 'profile': 'flac', 'status': 'ok', 'project_dir': str(project)})
            open_path.return_value = 0
            self.assertEqual(oss.main(['open']), 0)
            self.assertTrue(same_path(open_path.call_args.args[0], project))

    def test_unwritable_output(self):
        with patch('oss.tempfile.TemporaryFile', side_effect=PermissionError('denied')):
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, 'Elegí otra carpeta'):
                    oss.prepare_output(['engine', '--paths', directory])

    def test_cancel(self):
        with patch('oss.run', side_effect=KeyboardInterrupt):
            self.assertEqual(oss.main(['download', 'https://example.org']), 130)

if __name__ == '__main__':
    unittest.main()
