import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Host"))
import dolos_control as host
import spiel_fenster as display
import steam_aktion as steam


class ConsoleSessionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.enterContext(patch.dict(os.environ, LOCALAPPDATA=str(self.root), APPDATA=str(self.root)))
        steam.control_root().mkdir(parents=True)
        self.enterContext(patch.object(host, "DATA", steam.control_root()))

    def test_folder_restore_and_failed_start_keep_all_four_profiles_separate(self):
        app = "123"
        folder = self.root / "Game" / "SaveGames"
        folder.mkdir(parents=True)
        host.write("save-folders.json", {app: str(folder)})
        save = folder / "slot"
        save.write_text("original")
        with patch.object(steam, "running", return_value=False):
            for slot in (1, 2, 3):
                steam.switch_saves(app, slot)
                self.assertFalse(save.exists())
                save.write_text(str(slot))
                now = time.time()
                steam.restore_idle({app: now - 20})
                self.assertEqual(save.read_text(), str(slot))
                with patch.object(steam.time, "time", return_value=now + 20):
                    steam.restore_idle({app: now})
                self.assertEqual(save.read_text(), "original")
                self.assertEqual((steam.profile_path(app, slot) / "slot").read_text(), str(slot))
            with patch.object(subprocess, "Popen", side_effect=OSError), self.assertRaises(OSError):
                steam.launch_game(self.root, app, 1)
            self.assertEqual(save.read_text(), "original")
            self.assertEqual((steam.profile_path(app, 1) / "slot").read_text(), "1")

    def test_acc_console_mode_restores_only_the_input_setting(self):
        config = self.root / "Assetto Corsa Competizione/Config/controls.json"
        config.parent.mkdir(parents=True)
        config.write_text('{"carControllerMode": 0, "steering": 82}')
        with patch.object(display, "documents_folder", return_value=self.root), patch.object(host, "running") as running:
            running.return_value = False
            host.acc_gamepad(prepare=True)
            self.assertEqual(json.loads(config.read_text())["carControllerMode"], 1)
            running.return_value = True
            host.acc_gamepad()
            config.write_text('{"carControllerMode": 1, "steering": 97}')
            running.return_value = False
            host.acc_gamepad()
            self.assertEqual(json.loads(config.read_text()), {"carControllerMode": 0, "steering": 97})
            self.assertFalse((host.DATA / "acc-gamepad.json").exists())

    def test_abort_before_window_asks_steam_once_and_reserves_pending_launch(self):
        last = dict(id="123", request="first", time=time.time())
        with patch.object(display, "close_game", return_value=False), patch.object(host, "running", return_value=False), \
                patch.object(host, "steam_path", return_value=self.root), patch.object(subprocess, "Popen") as stop:
            host.end_managed_game(last)
            host.end_managed_game(last)
            stop.assert_called_once_with([str(self.root / "steam.exe"), "+app_stop", "123", "0"],
                                         creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertTrue(host.launch_pending(last))
            self.assertTrue(host.read("last-launch.json", {})["ending"])
            with patch.object(host.time, "time", return_value=last["time"] + 46):
                self.assertFalse(host.launch_pending(last))

    def test_finished_session_cannot_stop_a_later_desktop_launch(self):
        last = dict(id="123", request="first", time=time.time()-60, observed=True, ending=True)
        with patch.object(host, "running") as running, patch.object(display, "game_window", return_value=None), \
                patch.object(host, "end_managed_game") as stop:
            running.return_value = False
            host.watch_managed_game(last)
            with patch.object(host.time, "time", return_value=last["goneSince"]+5):
                host.watch_managed_game(last)
            self.assertTrue(last["closed"])
            running.return_value = True
            host.watch_managed_game(last)
            stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
