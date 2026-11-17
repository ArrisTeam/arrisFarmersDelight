# 第三方声明

本仓库的部分代码移植自下列开源项目。它们的许可要求在副本中保留原版权声明与许可声明，全文附在下面，
并且也写在对应目录的 `__init__.py` 文档字符串里（随包分发）。

| 原项目 | 许可 | 移植到 |
|---|---|---|
| [Hands-On Delight](https://github.com/Pocky-l/handson-delight) | MIT，Copyright (c) 2026 Pocky | `bp/arrisFarmersDelightScripts/Shared/Rules/HandsOn/`、`tests/test_handson_*.py` |
| [Diegesis](https://github.com/Pocky-l/diegesis) | MIT，Copyright (c) 2026 Pocky | 汤面的着色器（见下表）。Diegesis 内核本身的移植在另一个作品「场景交互 · 前置」里，不在本仓库，它的声明随那个包走 |

除了代码，下面这些随包分发的素材和照着写的着色器也来自这两个项目（同一份 MIT 许可）：

| 来自 | 是什么 | 在哪 |
|---|---|---|
| Diegesis | 汤面的纹理 `liquid.png`、碎料的六张图案 `bits/*.png` | `rp/textures/entity/cooking_pot_broth.png`（`tools/gen_pot_broth.py` 拼的） |
| Diegesis | 汤面和汤里碎料的画法（`LiquidRenderer` / `LiquidSim` / `LiquidPieces` 的 Java 代码改写成着色器） | `rp/shaders/glsl/arris_pot_broth_vertex.glsl`、`arris_pot_broth_fragment.glsl` |
| Hands-On Delight | 厨锅的声音（搅、落水、冒泡、盛） | `rp/sounds/handson/pot/`；其中 `body.ogg`（汤的底噪）是 Joseph Sardin 的录音，CC0，出自 [BigSoundBank](https://bigsoundbank.com)（HoD 的 README 里这样注明） |
| Hands-On Delight | 厨锅镂空锅身的方块和贴图坐标（`models/block/cooking_pot/body.json`）、场景文件里的机位和节点位置 | `rp/models/entity/cooking_pot.geo.json`、`bp/arrisFarmersDelightScripts/Compat/Diegesis/PotView.py` 等 |
| Hands-On Delight | 煎锅的油膜贴图（`block/oil_film.png`）和热浪粒子贴图（`particle/heat.png`） | `rp/textures/handson/` |

砧板刀口虚线的贴图 `rp/textures/particle/arris_board_mark.png` 是 Java 版原版的 `assets/minecraft/textures/block/white_concrete.png`（Mojang 的素材）：HoD 的虚线贴的就是它，
原样拷来。经典厨锅冒的气泡 `rp/textures/particle/arris_bubble_pop.png`（五张 16 x 16 叠成一张）是 Java 版原版的 `assets/minecraft/textures/particle/bubble_pop_0.png` 到
`bubble_pop_4.png`（Mojang 的素材）：FD 的锅放的就是原版的 `BUBBLE_POP`，原样拷来。本包只在网易版《我的世界》（正版代理）里分发使用。

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

砧板、煎锅、炉灶三个站点的场景数据（机位、碰撞盒、各件的大小和位置）取自 Hands-On Delight 的 `scenes/cutting_board.json / skillet.json /
stove.json`，写在 `Shared/Rules/HandsOn/BoardScene.py / PanLayout.py / StoveLayout.py` 和各站点的表现里，协议同上（MIT）。

## 团队自有库（拷入）

| 库 | 来源 | 拷到 |
|---|---|---|
| dolorContainer（容器界面库） | 团队自有，上游 `github.com/Dofes/dolorContainer`，拷入时的提交 `26c61b3`；上游仓库目前没有 LICENSE 文件 | `bp/arrisFarmersDelightScripts/dolorContainer/`、`dolorLayouts.py`（布局编译产物）、`rp/ui/dolor_*.json`、`tests/test_dolor_vendor.py` 等 |

库文件由上游的 `tools/vendor.py` 原样拷入（`dolor.lock` 记录每个文件的哈希），本仓库不改动它们。
