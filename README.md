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
| **厨锅 `arris:cooking_pot`** | 6 格食材 + 容器槽 + 产出槽 + 进度条动画 + 热源判定 + 实时 molang 同步；拆下来锅里煮好的菜跟着厨锅物品走、放回去还在；厨锅界面用 dolorContainer（服务端权威，食谱书带搜索与"添加食材"），同时支持经典/携带版档案；28 道菜（蘑菇煲、兔肉煲、牛肉炖、蔬菜汤、番茄酱、饺子、意面等）；配料照 JE 按标签认，别的模组登记进同名标签的番茄、米、生肉等也能下锅 |
| **煎锅 `arris:skillet`** | 坐置烹饪；自动切换 1-5 层食物展示实体；照 JE 是铁档武器（耐久 250，打人分轻重击音效）；潜行才放成方块、放下后记着那把煎锅的耐久与附魔，火焰附加缩短煎的时间；也能手持烹饪（煎锅放副手、原料拿主手，热源旁按住右键）；含水不能煎 |
| **炉灶 `arris:stove`** | 6 槽同时烘焙；每槽独立计时；能烤原版肉类和农夫乐事的切片，别的模组的东西只要有原版营火配方也能烤（煎锅同样） |
| **砧板 `arris:cutting_board`** | 刀 → 肉切片 / 切菜 / 切派；斧头 → 剥树皮（所有原版 + Nether 原木）；别的模组的刀挂上 `common:knife` 标签也能切 |
| **堆肥桶扩展** | 卷心菜叶、稻米、番茄、洋葱等 Arris 物品可堆肥，带概率；原版堆肥桶照原版的规则收它们（空桶放第一件必成，到 7 层就不再收） |
| **农作物系统** | 卷心菜、番茄、洋葱、水稻、棕/红蘑菇丛；野生作物种植规则、骨粉催熟、肥沃耕地自动浇水、水稻水田系统、藤蔓类番茄（拆掉绳上的番茄藤后绳子留下）；用带时运的工具收作物会多掉作物和种子 |
| **盘装食物** | 烤鸡、填馅南瓜、蜜汁火腿、牧羊人派、寿司卷、闪亮沙拉（会发光、冒闪光）等多阶段吃食方块；苹果派、巧克力派、甜浆果芝士派和原版南瓜派能放成方块一口口吃、用刀切片 |
| **绳网/安全网** | `arris:rope` 攀爬 + 敲钟响铃 + 防耕地踩坏，潜行空手右键卷回最下面一节，拿着绳子点绳子接到这根绳子最下面（潜行时往点的那一面接）；`arris:safety_net` 接住不摔伤并弹起来（潜行照常摔）；绳栅栏和绳栅栏门 |
| **篮子与榻榻米** | 竹篮 / 木篮把落进来和落在上面一格的掉落物吸进去（红石信号锁住）；榻榻米方块、长榻榻米垫（两格）、短榻榻米垫 |
| **合成** | 配方照 JE（奶桶奶瓶、熟羊肉熟羊排可以混着放）；原料剩下的容器照 JE 还：空了的那格放回空桶 / 玻璃瓶 / 碗，面团配方的水桶原样留下 |
| **背刺魔咒** | 小刀的专属魔咒（最高 III）：从背后打中目标伤害 ×1.4 / 1.6 / 1.8 |
| **食物效果** | `arris:nourishment`（滋养：带着它跑跳不掉饥饿值、也不掉饱和度，受了伤时照常花饱和度回血；菜肴和蘑菇煲、甜菜汤、兔肉煲给，时长照 JE 分 30 秒 / 1 / 3 / 5 分钟）、`arris:comfort`（舒适：照 JE 1.3.4，没有生命恢复、饱和度用完时每 4 秒回 1 点血；JE 1.3.2 起弃用，没有食物再给，只能用指令拿到）；牛奶瓶随机清除一个效果；热可可随机清除一个有害效果；西瓜汁回 2 点生命；西瓜冰棒灭火；兔肉煲另给跳跃提升 II 10 秒 |
| **展示实体** | `arris:item_display` / `arris:corpse_display` 用于厨锅槽 / 煎锅 / 砧板 / 炉灶的可视化；免疫伤害/传送/药水 |
| **烂番茄抛射物** | `arris:rotten_tomato` 可投掷，扔出去和砸中都有声音 |
| **联动接口（给别的模组作者）** | 农夫乐事加载完时广播 ready 事件，交出接口对象 `ext`：登记、查询、删除厨锅 / 砧板 / 煎烤配方，配料能写标签。见 [docs/EXTENSION-API.md](docs/EXTENSION-API.md) |
| **配方 JSON** | 不写代码也能加配方：在自己的行为包里放 `farmersdelight_recipes/` 目录，写法照 JE 农夫乐事的配方 JSON。见 [docs/RECIPE-JSON.md](docs/RECIPE-JSON.md) |
| **标签（netease_tags）** | 农夫乐事登记了一套 `common:` 标签（番茄、米、生肉、刀……）和 JE 农夫乐事自己的 `farmersdelight:` 标签（热源、菜的分类……），名字照 JE；别的模组把自己的东西登记进同名标签，双方就互认（网易 3.10 起）。见 [docs/TAGS.md](docs/TAGS.md) |
| **旧联动接口** | `compFactory.CreateModAttr("arris")` 交出的 3 个函数照常可用，供别的模组往配方、刀、热源等表里追加；新功能只加在新接口里。见 [linkage.md](linkage.md) |
| **JEI 联动** | 可选 — 若安装外部 Arris JEI 子 MOD，则自动注册厨锅 / 砧板 / 煎锅 / 炉灶 4 类配方视图；联动着沉浸式交互前置、砧板站点开着时另有第 5 类「砧板摆盘」 |
| **机械动力联动** | 可选 — 若一并安装机械动力（arrisCreate），农夫乐事的作物和食材能进它的石磨、搅拌、灌注配方；土豆加农炮认农夫乐事的七种弹药（卷心菜、番茄、洋葱、烂番茄、南瓜片、整个的派、派和蛋糕的切片） |
| **亲手做菜（沉浸式交互前置联动）** | 可选 — 若一并安装「沉浸式交互前置」（单独的作品，独立工程 arrisDiegesis / `ArrisTeam/netease-diegesis`，不在本仓库），厨锅 / 砧板 / 煎锅 / 炉灶右键进入贴近的操作视角：亲手下料、搅拌、切菜、颠锅、翻面（移植自 Hands-On Delight）；没装前置时这部分不运行，四个方块照农夫乐事原样使用 |
| **生物 AI 扩展** | 自定义马饲料 `arris:horse_feed`（加速 + 跳跃增益）、狗粮 `arris:dog_food`（加速 + 力量 + 抗性）；鸡、猪、兔子认农夫乐事的作物，拿着能引过来、能繁殖、能喂小崽（鸡：卷心菜种子、番茄种子、稻米；猪：卷心菜、番茄；兔子：卷心菜、卷心菜叶）；驯服的狼吃农夫乐事的肉（回血、繁殖），鹦鹉能用卷心菜种子、番茄种子、稻米驯服 |
| **工具类** | 燧石刀、金刀、铁刀、钻石刀、下界合金刀 |

---

## 项目结构

```
arrisFarmersDelight/
├── bp/                                      # 行为包
│   ├── arrisFarmersDelightScripts/          # Python 2.7 脚本根目录（结构说明见 docs/ARCHITECTURE.md）
│   │   ├── modMain.py                       # 入口：登记服务端、客户端与联动入口
│   │   ├── Shared/                          # 双端共用、不依赖引擎：Data/ 数据表、Rules/ 纯规则、Menus/ dolor 界面模型
│   │   ├── Api/                             # 对外联动接口：ExtensionApi/（新接口，docs/EXTENSION-API.md）、LegacyModAttr（旧的 3 个函数，linkage.md）
│   │   ├── Server/                          # 服务端：ModServer 入口 + EventRegistry + 各玩法模块 + Helpers/
│   │   ├── Client/                          # 客户端：ModClient 入口、客户端端点、CookingPotUi、Ui/（指南书、旧厨锅界面）
│   │   ├── Compat/                          # 联动：Jei/、Create/、Diegesis/（亲手做菜的站点）；对方未安装时不做任何事
│   │   ├── dolorContainer/                  # 容器界面库（dolorContainer 工程的 tools/vendor.py 拷入，请勿修改），dolorLayouts.py 是布局编译产物
│   │   └── QuModLibs/                       # 框架（arrisCreate kit 的加固精简版，请勿修改）
│   ├── netease_blocks/                      # 146 个自定义方块 JSON
│   ├── netease_items_beh/                   # 105 个物品行为 JSON
│   ├── netease_tags/                        # 标签：一个标签一个文件（tools/gen_tags.py 生成，词表见 docs/TAGS.md）
│   ├── recipes/                             # 137 个配方 JSON（工作台、熔炉 / 营火、锻造台）
│   ├── netease_enchants/                    # 自定义魔咒：背刺（资源包里也有一份）
│   ├── netease_tab/                         # 创造栏分类
│   ├── netease_features/ netease_feature_rules/  # 世界生成（野生作物、蘑菇群落等）
│   ├── loot_tables/ entities/ netease_effects/    # 掉落表、实体定义、自定义药水效果
│   └── manifest.json
├── rp/                                      # 资源包
│   ├── models/ textures/ animations/        # 模型、贴图、动画
│   ├── entity/ render_controllers/ animation_controllers/  # 实体客户端定义
│   ├── ui/                                  # 自定义 UI：引导书、JEI 视图、旧厨锅界面；dolor_*.json 是 dolorContainer 与厨锅布局的拷入 / 编译产物
│   ├── particles/ sounds/ fonts/            # 特效 / 音效 / 字体
│   └── manifest.json
├── docs/                                    # ARCHITECTURE.md（内部结构）；给别的模组作者看的 EXTENSION-API.md、RECIPE-JSON.md、TAGS.md、
│                                            # COMPATIBILITY.md（兼容承诺）、API-CHANGELOG.md（接口变更记录）
├── linkage.md                               # 旧联动接口（CreateModAttr("arris") 的 3 个函数）
├── layouts/ dolor.json dolor.lock           # dolorContainer 的布局源文件、配置与拷入记录（docs/ARCHITECTURE.md「厨锅界面」）
├── img/                                     # README 配图
├── tools/                                   # 开发工具：生成数据表 / 标签 / 覆盖原版文件的脚本、发版工具，跑测试的 run_tests.py
├── tests/                                   # 离线测试，不用开游戏（py -3 tools/run_tests.py）
└── README.md
```

---

## 技术亮点

- **纯 Python 2.7** — 跟随网易脚本运行时，UTF-8 BOM-free + `# -*- coding: utf-8 -*-`，中文注释与游戏文本直接嵌入
- **服务端 / 客户端严格分离** — RPC 通信通过 QuMod 的 `@Listen` / `@AllowCall` / `Call` 完成
- **tick 错峰优化** — 厨锅 `PosHash(pos) + tickCount) % STRIDE` 坐标加盐，N 个厨锅均摊到 STRIDE 个 tick，瞬时负载降到 1/STRIDE；煎锅 / 炉灶 相位错开
- **厨锅配方逐格配对** — 照 JE 的 `RecipeMatcher`：锅里每件东西分给一个收它的格（标签格问引擎的标签），同一锅料的答案记下来，加一条配方不用整张表重建
- **声音广播 + 客户端维度过滤** — 服务端 1 次广播代替 N 次 `CreateDimension` + 点对点 Call
- **安全 RPC** — 关键 `@AllowCall` 入口走 `@InjectHttpPlayerId` 注入真实 playerId，服务端白名单校验客户端输入

---

## 效果图

![效果图](img/img111.png)
![效果图](img/img222.png)
![效果图](img/img333.png)

---
