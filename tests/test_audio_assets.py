import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
import wave
from air_defense.audio import AudioBus, SOUNDS, generate_sounds
from air_defense.scene import AssetRegistry

class Voice:
    PLAYING=1
    def __init__(self): self.playing=False
    def status(self): return int(self.playing)
    def play(self): self.playing=True
    def stop(self): self.playing=False
    def setVolume(self,v): self.volume=v

class AudioAssetsTests(unittest.TestCase):
    def test_voice_limit_mute_and_silent_fallback(self):
        bus=AudioBus(limit=2); bus.silent=False; bus.cache={key:Voice() for key in ('a','b','c')}
        self.assertTrue(bus.play('a')); self.assertTrue(bus.play('b'))
        self.assertFalse(bus.play('c')); self.assertEqual(len(bus.voices),2)
        bus.stop(); self.assertEqual(bus.voices,[])
        bus.muted=True; self.assertFalse(bus.play('a'))
        self.assertFalse(AudioBus().play('hit'))

    def test_wav_signatures_distinct_and_asset_fallback_isolated(self):
        with TemporaryDirectory() as root:
            generate_sounds(root)
            self.assertEqual(len(list(Path(root).glob('*.wav'))),len(SOUNDS))
            for path in Path(root).glob('*.wav'):
                with wave.open(str(path),'rb') as wav: self.assertGreater(wav.getnframes(),100)
            self.assertNotEqual((Path(root)/'pistol.wav').read_bytes(),(Path(root)/'sniper.wav').read_bytes())
            registry=AssetRegistry(root); self.assertEqual(registry.resolve('missing.obj','procedural'),'procedural')
            a=registry.material((1,0,0)); b=registry.material((1,0,0)); a['color']=(0,0,0)
            self.assertEqual(b['color'],(1,0,0))
