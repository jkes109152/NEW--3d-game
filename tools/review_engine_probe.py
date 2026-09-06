"""不操作使用者桌面的原生引擎回歸檢查。"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from tempfile import TemporaryDirectory
from air_defense.main import create_game
from air_defense.save_data import SlotRepository
from tools.engine_probe import start


def assert_effective_shader(root,expected):
    from panda3d.core import ShaderAttrib
    for node in root.findAllMatches('**/+GeomNode'):
        for index in range(node.node().getNumGeoms()):
            state=node.getNetState().compose(node.node().getGeomState(index))
            shader=state.getAttrib(ShaderAttrib)
            assert shader and shader.getShader()==expected, f'既有模型仍保留舊畫質著色器：{node}，隱藏={node.isHidden()}，{state}'


def run():
    from panda3d.core import Filename
    output=ROOT/'artifacts'/'002-gameplay-expansion'/'review'; output.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='air-defense-review-') as profile_root:
        engine,c=create_game(offscreen=True,repository=SlotRepository(profile_root),silent=True)
        c.bridge.update=lambda:None; c.focus_checks=False
        try:
            c.select_slot(1); start(c); c.pause(); c.open_settings()
            for quality in ('low','high','medium'):
                c.settings.quality=quality; c.apply_settings()
                for root in (c.scene.root,c.scene.dynamic,c.scene.weapon):
                    assert_effective_shader(root,c.scene.shader._shader)
                c.ui.show('battle'); c.ui.update_hud(c.state.battle)
                for _ in range(4): engine.step()
                assert engine.win.saveScreenshot(Filename.fromOsSpecific(str(output/f'quality-{quality}.png')))
            before=c.scene.sun._light.getLens().getFilmSize()
            c.settings.master_volume=.3; c.apply_settings()
            assert c.scene.sun._light.getLens().getFilmSize()==before, '調整音量不應重設陰影範圍'
            c.leave_battle()
            for _ in range(4): engine.step()
            baseline=c.metrics()
            for _ in range(10):
                start(c); c.state.battle.player.aiming=True
                b=c.state.battle
                b.lock.update(3,tuple(b.aircraft),set(b.aircraft),True,False,3)
                c.ui.update_hud(b)
                b.lock.clear(); c.ui.update_hud(b)
                c.leave_battle()
                for _ in range(4): engine.step()
            after=c.metrics()
            for key in ('visuals','effects','engine_entities','engine_tasks','input_handlers','lock_markers','active_missiles'):
                assert after[key]==baseline[key],f'清理差異：{key}'
            print('三種畫質、音量調整與十次鎖定／戰鬥清理均通過。')
        finally:
            c.window_listener.ignoreAll(); engine.destroy()

if __name__=='__main__': run()
