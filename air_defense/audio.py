"""自合成音效與有上限的播放匯流排；不修改戰鬥狀態。"""
from array import array
from math import sin, tau, exp
from pathlib import Path
from random import Random
import wave
from .config import ASSETS

SOUNDS = {
    'rifle':(145,.15,.6),'smg':(230,.08,.55),'shotgun':(58,.35,.85),'reload_started':(310,.3,.2),'reload_finished':(450,.12,.1),'bolt_cycled':(380,.13,.35),
    'aa':(110,.24,.45), 'sniper':(75,.30,.75), 'pistol':(180,.11,.50),
    'rpg':(48,.40,.80), 'multi':(140,.35,.55), 'lock_complete':(980,.18,.02),
    'missile_launch':(320,.26,.28), 'hit':(640,.08,.12), 'destroyed':(50,.48,.90),
    'explosion':(35,.65,.95), 'turret_fire':(210,.06,.45), 'player_hurt':(95,.16,.25),
    'alert':(720,.32,.02), 'success':(660,.50,.01), 'failure':(180,.65,.05), 'shop':(880,.15,.01),
}

def generate_sounds(root=ASSETS/'audio'):
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    for name,(frequency,duration,noise) in SOUNDS.items():
        path=root/(name+'.wav')
        if path.is_file(): continue
        rng=Random(name)
        data=array('h')
        for i in range(int(22050*duration)):
            t=i/22050
            envelope=min(1,t/.003)*exp(-5*t/duration)
            pitch=frequency*(1-.35*t/duration)
            signal=(1-noise)*sin(tau*pitch*t)+noise*rng.uniform(-1,1)
            data.append(int(16000*envelope*signal))
        with wave.open(str(path),'wb') as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(22050); out.writeframes(data.tobytes())

class AudioBus:
    def __init__(self, loader=None, limit=16, root=ASSETS/'audio'):
        self.limit=limit
        self.voices=[]
        self.master=0.7
        self.effects=0.8
        self.muted=False
        self.silent=loader is None
        self.dropped=0
        self.last_error=None
        self.cache={}
        if loader:
            try:
                from panda3d.core import Filename
                for key in SOUNDS:
                    path=Path(root)/(key+'.wav')
                    if path.is_file(): self.cache[key]=loader.loadSfx(Filename.fromOsSpecific(str(path)))
            except Exception as exc:
                self.silent=True
                self.last_error=str(exc)

    def tick(self):
        try:
            self.voices=[voice for voice in self.voices if voice.status()==voice.PLAYING]
        except Exception as exc:
            self.silent=True
            self.last_error=str(exc)
            self.stop()

    def play(self, name, pitch=1):
        self.tick()
        if self.silent or self.muted or self.master*self.effects<=0: return False
        if len(self.voices)>=self.limit:
            self.dropped+=1
            return False
        voice=self.cache.get(name)
        if voice is None: return False
        try:
            # 同音效合併成一個聲道；多種事件仍可同時播放。
            if voice in self.voices: return False
            voice.setVolume(self.master*self.effects)
            if hasattr(voice,'setPlayRate'):voice.setPlayRate(pitch)
            voice.play()
            self.voices.append(voice)
            return True
        except Exception as exc:
            self.silent=True
            self.last_error=str(exc)
            self.stop()
            return False

    def consume(self, events):
        for event in events:
            key=event['kind']
            if key=='weapon_fire':key=event.get('audio_key','pistol')
            wid=event.get('weapon_id','W01')
            self.play(key,.94+(int(wid[1:])%5)*.03 if key in ('aa','sniper','pistol','rpg','rifle','smg','shotgun') else 1)

    def stop(self):
        voices,self.voices=self.voices,[]
        for voice in voices:
            try: voice.stop()
            except Exception as exc:
                self.silent=True
                self.last_error=str(exc)
