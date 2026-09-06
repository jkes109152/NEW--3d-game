import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from air_defense.ui import Settings

class SettingsTests(unittest.TestCase):
    def test_persistent_preferences_and_session_only_aim_mode(self):
        with TemporaryDirectory() as root:
            s=Settings(sensitivity=1.7,master_volume=.2,effects_volume=.4,quality='high',fullscreen=True,
                       reduced_motion=True,resolution=(1920,1080),aim_mode='legacy')
            s.save(root); loaded=Settings.load(root)
            self.assertEqual(loaded.aim_mode,'modern')
            for key in ('sensitivity','master_volume','effects_volume','quality','fullscreen','reduced_motion','resolution'):
                self.assertEqual(getattr(s,key),getattr(loaded,key))

    def test_invalid_json_and_values_fall_back(self):
        with TemporaryDirectory() as root:
            path=Path(root)/'settings.json'
            for raw in ('invalid','[]','{"sensitivity":-1,"master_volume":true,"quality":"ultra","fullscreen":1,"resolution":[1,2]}'):
                path.write_text(raw,encoding='utf-8')
                self.assertEqual(Settings.load(root),Settings())
