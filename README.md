# arrisFarmersDelight <img src="img/farmers_delight.png" width="32px">

### 棱花 Arris · 网易版农夫乐事

> 将 Java 版经典模组 **Farmer's Delight**（农夫乐事）移植到 **网易版我的世界（Minecraft Bedrock / Netease Edition）** 的开源 AddOn。
>
> - 基于 **QuModLibs** 框架开发（原先使用 QyMod，已于 2026-04 迁移至 QuMod）
> - 直接导入 **MC Studio**（网易我的世界开发者工具）即可使用
> - 代码已开源供开发者学习参考

## 许可 / 联系

- 开源协议：[LICENSE](LICENSE)
- 项目作者： **棱花 Arris - lovely_小柒丫**

## 主要特性

### 模块一览

| 模块 | 功能 |
|---|---|
| **厨锅 `arris:cooking_pot`** | 6 格食材 + 容器槽 + 产出槽 + 进度条动画 + 热源判定 + 实时 molang 同步；厨锅界面用 dolorContainer（服务端权威，食谱书带搜索与"添加食材"），同时支持经典/携带版档案；支持 30+ 配方（蘑菇煲、兔肉煲、牛肉炖、蔬菜汤、番茄酱、饺子、意面、火腿、蛋糕等） |
| **煎锅 `arris:skillet`** | 坐置烹饪；自动切换 1-5 层食物展示实体；攻击时播放特殊音效 |
| **炉灶 `arris:stove`** | 6 槽同时烘焙；每槽独立计时；支持原版肉类 + 自定义切片 |
| **砧板 `arris:cutting_board`** | 刀 → 肉切片 / 切菜 / 切派；斧头 → 剥树皮（所有原版 + Nether 原木） |
| **堆肥桶扩展** | 白菜叶、稻米、番茄、洋葱等 Arris 物品可堆肥，带概率 |
| **农作物系统** | 白菜、番茄、洋葱、水稻、棕/红蘑菇丛；野生作物种植规则、骨粉催熟、肥沃耕地自动浇水、水稻水田系统、藤蔓类番茄 |
| **盘装食物** | 烤鸡、填馅南瓜、蜜汁火腿、牧羊人派、寿司卷等多阶段吃食方块 |
| **绳网/安全网** | `arris:rope` 攀爬 + 敲钟响铃 + 防耕地踩坏；`arris:safety_net` 削减坠落伤害 |
| **食物效果** | `arris:nourishment`（滋养：冻结饥饿消耗；菜肴和蘑菇煲、甜菜汤、兔肉煲给，时长照 JE 分 30 秒 / 1 / 3 / 5 分钟）、`arris:comfort`（舒适：阻挡所有负面效果；JE 1.3.2 起弃用，没有食物再给，效果和处理保留）；牛奶瓶随机清除一个效果；热可可随机清除一个有害效果；西瓜汁回 2 点生命；西瓜冰棒灭火；兔肉煲另给跳跃提升 II 10 秒 |
| **展示实体** | `arris:item_display` / `arris:corpse_display` 用于厨锅槽 / 煎锅 / 砧板 / 炉灶的可视化；免疫伤害/传送/药水 |
| **烂番茄抛射物** | `arris:rotten_tomato` 可投掷 |
| **小 MOD 内部联动** | `arris` 命名空间下通过 `compFactory.CreateModAttr("arris")` 暴露的 3 个扩展接口，供其他 Arris 子 MOD 追加堆肥/配方/切片规则 |
| **JEI 联动** | 可选 — 若安装外部 Arris JEI 子 MOD，则自动注册厨锅 / 砧板 / 煎锅 / 炉灶 4 类配方视图 |
| **生物 AI 扩展** | 自定义马饲料 `arris:horse_feed`（加速 + 跳跃增益）、狗粮 `arris:dog_food`（加速 + 力量 + 抗性） |
| **工具类** | 燧石刀、金刀、铁刀、钻石刀、下界合金刀 |

---

## 项目结构

```
arrisFarmersDelight/
├── bp/                                      # 行为包 (UUID 0bbb87d8-…)
│   ├── arrisFarmersDelightScripts/          # Python 2.7 脚本根目录（结构说明见 docs/ARCHITECTURE.md）
│   │   ├── modMain.py                       # 入口：登记服务端、客户端与联动入口
│   │   ├── Shared/                          # 双端共用、不依赖引擎：Data/ 数据表、Rules/ 纯规则、Menus/ dolor 界面模型
│   │   ├── Api/                             # 对外联动接口（linkage.md）
│   │   ├── Server/                          # 服务端：ModServer 入口 + EventRegistry + 各玩法模块 + Helpers/
│   │   ├── Client/                          # 客户端：ModClient 入口、客户端端点、CookingPotUi、Ui/（指南书、旧厨锅界面）
│   │   ├── Compat/                          # 联动：Jei/、Create/（对方未安装时不做任何事）
│   │   ├── dolorContainer/                  # 容器界面库（tools/vendor.py 拷入，请勿修改），dolorLayouts.py 是布局编译产物
│   │   └── QuModLibs/                       # 框架（arrisCreate kit 的加固精简版，请勿修改）
│   ├── netease_blocks/                      # 89 个自定义方块 JSON
│   ├── netease_items_beh/                   # 98 个物品行为 JSON
│   ├── recipes/                             # 165 个合成配方 JSON
│   ├── netease_tab/                         # 创造栏分类
│   ├── netease_features/ netease_feature_rules/  # 世界生成（野生作物、蘑菇群落等）
│   ├── loot_tables/ entities/ netease_effects/    # 掉落表、实体定义、自定义药水效果
│   └── manifest.json
├── rp/                                      # 资源包 (UUID 497a11b2-…)
│   ├── models/ textures/ animations/        # 模型、贴图、动画
│   ├── entity/ render_controllers/ animation_controllers/  # 实体客户端定义
│   ├── ui/                                  # 自定义 UI：引导书、JEI 视图、旧厨锅界面；dolor_*.json 是 dolorContainer 与厨锅布局的拷入 / 编译产物
│   ├── particles/ sounds/ fonts/            # 特效 / 音效 / 字体
│   └── manifest.json
├── layouts/ dolor.json dolor.lock           # dolorContainer 的布局源文件、配置与拷入记录（docs/ARCHITECTURE.md「厨锅界面」）
├── img/                                     # README 配图
├── CLAUDE.md                                # 项目开发指南（面向 AI / 新贡献者）
├── .planning/OPTIMIZATION_PLAN.md           # 性能优化计划存档
└── README.md
```

---

## 技术亮点

- **纯 Python 2.7** — 跟随网易脚本运行时，UTF-8 BOM-free + `# -*- coding: utf-8 -*-`，中文注释与游戏文本直接嵌入
- **服务端 / 客户端严格分离** — RPC 通信通过 QuMod 的 `@Listen` / `@AllowCall` / `Call` 完成
- **tick 错峰优化** — 厨锅 `PosHash(pos) + tickCount) % STRIDE` 坐标加盐，N 个厨锅均摊到 STRIDE 个 tick，瞬时负载降到 1/STRIDE；煎锅 / 炉灶 相位错开
- **厨锅配方 O(1) 查找** — `tuple(sorted(inputs))` 作为键的倒排索引，替代原始 O(recipes × variants × Counter) 扫描
- **声音广播 + 客户端维度过滤** — 服务端 1 次广播代替 N 次 `CreateDimension` + 点对点 Call
- **安全 RPC** — 关键 `@AllowCall` 入口走 `@InjectHttpPlayerId` 注入真实 playerId，服务端白名单校验客户端输入

---

## 效果图

![效果图](img/img111.png)
![效果图](img/img222.png)
![效果图](img/img333.png)

---
