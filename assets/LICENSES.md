# 資產來源與授權

本專案的程序化模型、材質配色與本地合成 WAV 音效為此次開發自製，不依賴私人模型或遠端服務。

| 資產 | 來源 | 授權／版本 |
|---|---|---|
| 程序化飛機、人物、武器、城市、道路與掩體 | `air_defense/scene.py`、`air_defense/models.py`、`air_defense/visual_catalog.py` | 本專案自製 |
| 合成射擊、命中、警報與介面音效 | `air_defense/audio.py` | 本專案自製 |
| 糖果頂點色／乘法陰影材質 | `air_defense/materials.py`，使用 Ursina／Panda3D 公開著色介面 | 本專案自製 |
| 圓點、條紋、星星重複圖樣 | `assets/textures/dots.png`、`stripes.png`、`stars.png`，Pillow 離線繪製 | 本專案自製，隨包提供 |
| 步槍、衝鋒槍、霰彈槍、換彈與上膛音效 | `assets/audio/`；波形由 `air_defense/audio.py` 以固定亂數種子合成，22,050 Hz 單聲道 PCM | 本專案自製，無錄製或取樣他人素材 |
| Noto Sans CJK TC Regular 繁體中文字型 | [Noto CJK 官方專案](https://github.com/notofonts/noto-cjk)；檔案位於 `assets/fonts/NotoSansCJKtc-Regular.otf` | 版本 2.004；SIL Open Font License 1.1，隨附於 `assets/fonts/OFL.txt` |

字型原始下載位置：[NotoSansCJKtc-Regular.otf](https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf)。
