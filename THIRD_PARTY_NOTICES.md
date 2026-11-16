# 第三方声明

本仓库的部分代码移植自下列开源项目。它们的许可要求在副本中保留原版权声明与许可声明，全文附在下面，
并且也写在对应目录的 `__init__.py` 文档字符串里（随包分发）。

| 原项目 | 许可 | 移植到 |
|---|---|---|
| [Hands-On Delight](https://github.com/Pocky-l/handson-delight) | MIT，Copyright (c) 2026 Pocky | `bp/arrisFarmersDelightScripts/Shared/Rules/HandsOn/`、`tests/test_handson_*.py` |
| [Diegesis](https://github.com/Pocky-l/diegesis) | MIT，Copyright (c) 2026 Pocky | `diegesisBp/arrisDiegesisScripts/Shared/`（Protocol.py 除外）、`tests/dgkit.py`、`tests/dgfixtures.py` 与内核的 `tests/test_diegesis_*.py` |

除了代码，下面这些随包分发的素材和照着写的着色器也来自这两个项目（同一份 MIT 许可）：

| 来自 | 是什么 | 在哪 |
|---|---|---|
| Diegesis | 粒子的序列帧（水花、蒸汽、气泡、破泡、水面上的泡）、汤面的纹理 `liquid.png`、碎料的六张图案 `bits/*.png` | `diegesisRp/textures/diegesis/`、`rp/textures/entity/cooking_pot_broth.png`（`tools/gen_pot_broth.py` 拼的） |
| Diegesis | 汤面和汤里碎料的画法（`LiquidRenderer` / `LiquidSim` / `LiquidPieces` 的 Java 代码改写成着色器） | `rp/shaders/glsl/arris_pot_broth_vertex.glsl`、`arris_pot_broth_fragment.glsl` |
| Hands-On Delight | 食谱书的模型（`recipe_book.bbmodel` 的方块和贴图坐标）与贴图（`recipe_book.png`、`recipe_book_paper.png`） | `diegesisRp/textures/handson/`、`diegesisRp/models/entity/`（`tools/gen_book_assets.py` 生成几何和贴图集） |
| Hands-On Delight | 厨锅的声音（搅、落水、冒泡、盛） | `rp/sounds/handson/pot/`；其中 `body.ogg`（汤的底噪）是 Joseph Sardin 的录音，CC0，出自 [BigSoundBank](https://bigsoundbank.com)（HoD 的 README 里这样注明） |
| Hands-On Delight | 厨锅镂空锅身的方块和贴图坐标（`models/block/cooking_pot/body.json`）、场景文件里的机位和节点位置 | `rp/models/entity/cooking_pot.geo.json`、`bp/arrisFarmersDelightScripts/Compat/Diegesis/PotView.py` 等 |

食谱书的翻页箭头不是 Mojang 的图：JE 用原版书本界面的箭头，这里照同样的形状自己画（`tools/book_textures.py`）。

两者的许可原文相同：

```text
MIT License

Copyright (c) 2026 Pocky

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 团队自有库（拷入）

| 库 | 来源 | 拷到 |
|---|---|---|
| dolorContainer（容器界面库） | 团队自有，上游 `github.com/Dofes/dolorContainer`，拷入时的提交 `26c61b3`；上游仓库目前没有 LICENSE 文件 | `bp/arrisFarmersDelightScripts/dolorContainer/`、`dolorLayouts.py`（布局编译产物）、`rp/ui/dolor_*.json`、`tests/test_dolor_vendor.py` 等 |

库文件由上游的 `tools/vendor.py` 原样拷入（`dolor.lock` 记录每个文件的哈希），本仓库不改动它们。
