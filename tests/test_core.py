import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import oss

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.patch = patch('oss.executable', side_effect=lambda name: '/bundle/bin/' + name)
        self.patch.start()
        self.addCleanup(self.patch.stop)

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

    def test_create_project_writes_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            project = oss.create_project('https://example.org/song', directory, {
                'title': 'Artist - Track (Official Video)',
                'webpage_url': 'https://example.org/song',
                'uploader': 'Third Party Channel',
                'duration': 123,
                'id': 'abc',
            })
            self.assertEqual(project, Path(directory) / 'Artist' / 'Track')
            metadata = (project / 'metadata.json').read_text(encoding='utf-8')
            self.assertIn('"artist_guess": "Artist"', metadata)
            self.assertIn('"track_guess": "Track"', metadata)

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

        with tempfile.TemporaryDirectory() as directory, patch('oss.default_downloads', return_value=Path(directory)), patch('oss.fetch_metadata', return_value={'title': 'Artist - Song'}), patch('oss.run', side_effect=fake_run):
            self.assertEqual(oss.main(['both', 'https://example.org/song']), 0)
        self.assertIn(str(Path(directory) / 'Artist' / 'Song'), calls[0])
        self.assertIn(str(Path(directory) / 'Artist' / 'Song'), calls[1])
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
            self.assertEqual(cmd[cmd.index('--cookies') + 1], str(cookies))

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
        with tempfile.TemporaryDirectory() as directory, patch('builtins.input', side_effect=lambda prompt='': next(answers)), patch('oss.default_downloads', return_value=Path(directory)), patch('oss.fetch_metadata', return_value={'title': 'Artist - Song'}), patch('oss.check_ytdlp_update'), patch('oss.run_all') as run:
            run.return_value = 0
            self.assertEqual(oss.menu(), 0)
            commands = run.call_args.args[0]
            self.assertEqual(commands[0][commands[0].index('--format') + 1], 'bestvideo+bestaudio/best[vcodec!=none][acodec!=none]')
            self.assertEqual(commands[1][commands[1].index('--audio-format') + 1], 'wav')

    def test_direct_url_shortcut(self):
        with patch('oss.run') as run:
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
                self.assertEqual(oss.load_config(config)['downloads_dir'], str(downloads))
                self.assertEqual(oss.load_config(config)['install_mode'], 'online')


    def test_global_config_flag_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'isolated.json'
            downloads = Path(directory) / 'Downloads'
            self.assertEqual(oss.main(['--config', str(config), 'configure', '--downloads-dir', str(downloads)]), 0)
            self.assertEqual(oss.load_config(config)['downloads_dir'], str(downloads))

    def test_config_env_dir_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            config_dir = Path(directory) / 'cfg'
            downloads = Path(directory) / 'Downloads'
            with patch.dict('os.environ', {'OSS_CONFIG_DIR': str(config_dir)}), patch.object(oss, '_ACTIVE_CONFIG_PATH', None):
                self.assertEqual(oss.configure(downloads), 0)
                self.assertEqual(oss.load_config(config_dir / 'config.json')['downloads_dir'], str(downloads))

    def test_command_uses_configured_downloads_dir(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'
            downloads = Path(directory) / 'Chosen'
            oss.save_config({'downloads_dir': downloads}, config)
            with patch.object(oss, 'CONFIG_PATH', config):
                cmd = oss.command('https://example.org/song')
                self.assertEqual(cmd[cmd.index('--paths') + 1], str(downloads))

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
