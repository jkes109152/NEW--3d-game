"""無音訊後端、低畫質及缺少可選圖樣的實際引擎驗證。"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
from air_defense.main import create_game
from air_defense.save_data import SlotRepository
from air_defense.models import cache_metrics
from tools.expansion_probe import play
from tools.engine_probe import screenshot,start


def run():
    output=ROOT/'artifacts'/'002-gameplay-expansion'/'fallback';output.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='糖果無聲低畫質-') as root:
        engine,c=create_game((1280,720),offscreen=True,silent=True,repository=SlotRepository(root))
        c.focus_checks=False;c.bridge.update=lambda:None;c.settings.quality='low';c.apply_settings();pending=[]
        try:
            c.select_slot(1);b=start(c)
            def draw(battle,events,tick):
                pending.extend(events)
                if tick%4==0:
                    c.scene.sync(battle,1/30,tuple(pending));c.audio.consume(tuple(pending));pending.clear()
                    c.ui.update_hud(battle);engine.step()
            record=play(b,observer=draw);assert record['phase']=='success',record
            c.state.settle();c.ui.show();screenshot(engine,output/'low-silent-success.png')
            assert c.audio.silent and not c.scene.shadows_enabled and not c.scene.sun._light.isActive()
            c.show_menu();c.customize('W17')
            c.shop_action('purchase_cosmetic',weapon_id='W17',cosmetic_kind='pattern',cosmetic_id='stars')
            # 成功所得 125 金幣支付 100 圖樣；只移除隔離資產提供者的可選紋理。
            with TemporaryDirectory(prefix='糖果缺可選素材-') as missing:
                from air_defense import models
                with patch.object(models,'ASSETS',Path(missing)):
                    c.custom_select('selected_pattern','stars');c.apply_custom()
                    screenshot(engine,output/'missing-optional-pattern.png')
            assert 'textures/stars.png' in cache_metrics()['optional_asset_fallbacks']
            report=dict(category='引擎繪製與公開輸入情境；非原生鍵鼠',resolution=[1280,720],quality='low',audio_backend='null',audio_silent=c.audio.silent,level=record,coins_after_optional_cosmetic=c.state.profile['coins'],fallbacks=cache_metrics()['optional_asset_fallbacks'],passed=True)
            (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in report.items() if k!='level'},ensure_ascii=False))
        finally:c.window_listener.ignoreAll();engine.destroy()


if __name__=='__main__':run()
