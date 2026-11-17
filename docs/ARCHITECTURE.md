# 农夫乐事脚本架构

行为包脚本根：`bp/arrisFarmersDelightScripts/`（Python 2.7，网易 ModSDK + QuModLibs）。

```
modMain.py              入口：dolorContainer 两端服务 + MOD.Server("Server.ModServer") / MOD.Client("Client.ModClient") + 各联动入口
QuModLibs/              框架（arrisCreate kit 的加固精简版），只读，不改
dolorContainer/         容器界面库：团队自有，由 dolorContainer 仓库的 tools/vendor.py 原样拷入（dolor.lock 记哈希），只读，不改
dolorLayouts.py         布局的绑定表：vendor 时从仓库根 layouts/*.json 编译生成，不手改
Shared/                 双端共用；不导入引擎、QuModLibs、Server、Client —— 离线可测
  Data/                 纯数据表：Cooking  Cutting  CookingPotRecipes  Farming  Food  Blocks  Effects  Mobs  MobLoot  Slicing  ChestLoot  GuideBook
                        Dishes（砧板摆盘的菜谱，tools/gen_dishes.py 从合成配方生成）
                        Remainders（原料用掉后剩下的容器：JE 的合成剩余物 + 厨锅的特例表）
                        CraftReturns（无序合成配方补还的剩余物，tools/gen_crafts.py 从合成配方生成）
                        FoodColors  BrothColors（按贴图算的颜色：切菜碎屑、汤色、碎料色、倒进锅里的液体色，tools/gen_food_colors.py / gen_broth_colors.py 生成）
                        BiomeWater（各群系的水色，tools/gen_biome_water.py 按原版资源包每个群系的 water_appearance 生成；厨锅里的清水取它）
                        PotSunk（下锅就沉的料：倒的、打的、化的）  PotPieceTraits（配料切成碎料时算谷物 / 意面 / 肉，还是煮完拣出来）
                        HandsOnConfig（HoD 的配置表：四个站点的开关、工作台合成、搅拌、食谱书、三种烹饪倍率，缺省同 JE；整合包作者改它，不经联动契约；读法在 Rules/HandsOnOptions）
  Rules/                纯规则：CookingPot（配方匹配 / 出料结算） CropGrowth（催熟阶段表） Placement（朝向 / 放置位置；`directionOfAux` 是读方块 aux 的唯一一处） Ticks（错峰 / 概率）
                        CookingPotBook（厨锅食谱书：容器格号、搜索、详情格、补食材的计划）
                        CuttingStation（切菜板站点：FD 配方 -> 刀口计划、工具判定、整批产物）
                        PotStation（厨锅站点：槽位声明、什么能放、什么用得上、盛这道菜的容器）  PotLayout（按哪道菜摆料、照书放料的计划）
                        PotLookState（厨锅"看上去是什么样"的广播怎么读）  PotModelMath（方块朝向、勺子骨骼的位移和欧拉角）
                        PotPiecesLook（汤里的碎料交给着色器的数：配料槽、出现 / 缩走的钟）  PotItem（拆下来的锅带着菜）
                        PotWater（厨锅里清水的颜色：锅所在区块里 5x5 列的群系水色取平均，群系名由客户端 Compat/Diegesis/PotBiome 问来）
                        PanStation（煎锅站点：能煎什么、蛋只煎一面、一面多久、徽章与提示文字）  PanLookState（煎锅"看上去是什么样"的广播怎么读）
                        GrillStation（炉灶站点：能放什么、一面多久、这一下右键开不开）  StoveCover（炉灶上面盖没盖东西：锅、煎锅、砧板、别的方块）
                        GrillBlocks（灶方块 = 点着的 `StoveList` + 熄着的孪生方块 `arris:stove_extinguish`：isLit / isGrill / twinOf、前置包登记站点用的活容器 `GRILL_BLOCKS`、
                        熄着时 FD 的件怎么冷却 `cooledTimer`、什么点得着 / 灭得了炉灶 `useOf`）
                        StoveFacing（炉灶的朝向：方块的 aux -> 站点朝向，炉灶自己的坐标 / 姿态 -> 世界，六件跟着炉灶转）
                        StoveLookState（炉灶"看上去是什么样"：广播和方块实体里存的那份怎么读）  EggLook（煎锅 / 炉灶里的蛋从生到熟的三档专用图标）
                        DishStation（砧板摆盘：哪些菜搬到砧板、什么能打底、下一层、做成哪道、做几份）
                        StationBooks（四个站点旁的食谱书页：厨锅、砧板摆盘 + 切、煎锅、炉灶；服务端放料挑写法、凑份数；页脚的秒数带着配置的倍率）
                        HandsOnOptions（HoD 配置表的读法：JE 的缺省、read / readTime 的兜法、倍率夹进 0.1..10、派生规则、scaled；每次现读表，两端共用）
                        SyncTables  TableWire  TableDiff  TableMerge（下游在服务端追加的表怎么发给客户端：登记哪些表 / 编码 / 算差异 / 并表，见"联动契约与客户端的表"）
                        FoodEffects（吃喝之后的追加结算：牛奶瓶 / 热可可 / 西瓜汁 / 冰棒 / 原版汤；只返回动作，Server/FoodEffects 执行）
                        BlockDisplay（砧板 / 煎锅 / 炉灶上的物品怎么摆） ItemPose（客户端掉落物姿态换算，实机标定）
                        MobLoot（刀杀死生物的额外掉落、洋葱掉落的概率结算） Slicing（刀切派 / 蛋糕 / 南瓜：剩几片、切片单） Eating（吃一份食物的饥饿 / 饱和度）
                        Livestock（马饲料 / 狗粮喂给谁、有什么效果） ChestLoot（战利品箱追加物品的掷骰）
                        GrowthRates（JE 作物的生长概率 -> 基岩随机刻的概率，换算只在这里） CropTick（一次随机刻长不长、长几级）
                        FarmEdits（随机刻 / 骨粉要改哪些方块） BoneMealRules（骨粉照 JE） WildSpread（野生作物骨粉蔓延）
                        CompostRules（有机肥堆沤） ColonyRules（蘑菇菌落） RichSoilRules（沃土催熟与湿度） StrawRules（刀收草秆）
                        Sparkle（闪亮沙拉的闪光粒子：哪些阶段冒、概率 0.05 × 份数、冒在哪）
                        Crafting（工作台合成：格子里摆的是哪条配方、实际做了几份、剩余物放回哪）
                        Backstabbing（背刺魔咒：物品上几级、是不是从背后打的、伤害乘多少）
                        SkilletRules（煎锅照 JE：烹饪时间含火焰附加的换算、手持热源范围、攻击冷却挑音效、耐久磨损、存取煎锅物品、创造拆煎锅记录）
                        SkilletHandRules（手持煎锅烹饪：右键按住的上报与记录、一次烹饪的计时、滋滋声概率）
                        Basket（篮子吸掉落物：收集区、往 27 格里塞的次序、冷却） RopeReel（卷绳子：整根绳子最下面一节）
                        NetBounce（安全网：摔落距离推撞击速度、弹跳系数） StoveBurn（站在点燃炉灶上的烫伤：烤架区、豁免条件）
                        TatamiMat（长榻榻米垫两格怎么摆、另一半在哪、脚下没了方块） RopeFence（绳栅栏门的开关、朝向、声音）
    HandsOn/            Hands-On Delight 规则内核的移植：搅锅评星、批量烹饪、刀口、煎锅 / 灶台两面、摆盘（MIT）；
                        厨锅的表现也在这里（纯计算，Pot 开头的那些）：汤面（水位、汤色、沸腾）、勺子的手感、漂着的料、碎料、
                        出锅的收尾、声音日程、徽章、盛汤和倒 / 打 / 抖的手部动作
  Menus/                dolorContainer 的界面模型（两端各建一份）：CookingPot（厨锅）
Api/
  LegacyModAttr.py      对外联动契约 v1（linkage.md 的三个函数，显式白名单）
Server/                 服务端
  ModServer.py          导入全部玩法模块；33 个引擎事件各只挂一次 @Listen，转给 EventRegistry
  EventRegistry.py      registerHandler / dispatch：按方块 / 物品名匹配、优先级、短路、异常隔离
  Helpers/              Engine（引擎入口唯一出处）Player Fx Heat Items Placement BlockItems（方块上的物品：广播 + 清理旧展示实体）
                        PotContainer（厨锅容器格与预览槽的读写：出一份、加份数、装碗转出）
                        BoardDish（砧板摆盘的存档：叠着的层、做好的那叠；经典右键还回、拆板掉落）
  CookingPot Skillet Stove CuttingBoard ItemToBlock Crops BoneMeal RichSoil WildCrops
  SkilletItem           煎锅物品：潜行才放成方块、方块实体里记着放下的那件煎锅（耐久 / 附魔 / 名字）、拆掉原样掉回、打一下只磨损 1 点
  SkilletHand           手持煎锅烹饪：一只手煎锅、另一只手原料，热源旁按住右键煎好一件（SkilletHold 是客户端右键上报的 RPC 端点）
  CropTicks FarmWorld   作物随机刻（照 JE 的生长概率）与它读写世界的那一层；OrganicCompost MushroomColony Straw 同属种植
  HandCooking           每口锅的烹饪计时（HoD PotClock）：FD 原样一份一份煮，或厨师搅着整批煮、按星多送
  PotLook               厨锅的世界外观广播：锅里有什么、勺子在哪、煮到哪，发给 32 格内的人，静态部分写进方块实体数据
  PotServe              盛菜：取一份、记"做过几份"、给经验；主手拿着容器右键直接盛
  HandFrying            煎锅手放的一批（HoD Frying）：先煎贴锅面、等颠锅翻面、两面熟了留在锅里；右键放的照 FD 原样
  HandGrill             炉灶手放的每一件（HoD Grill）：逐件两面分开烤、等翻面、烤好留在灶台上；右键放的照 FD 原样
  StoveSwap StoveFire   炉灶点火 / 灭火：点着的是 `arris:stove`、熄着的是 `arris:stove_extinguish`，换方块名等于换方块实体，StoveSwap 换之前拍炉灶自己的键（六个烤位、cookingIndex、
                        handGrill）和朝向的快照、换完写回（事件先后两种都兜；5 秒还写不上把东西丢在地上；旧方块的移除事件用 claims 挡住；换完一秒里重发世界外观），
                        StoveFire 是 `ServerItemUseOnEvent` 优先级 11 的处理：打火石、火焰弹点着，铲子、水桶熄灭（JE 的 AbstractStoveBlock.use），用上了就认领，不再放食物
  PanLook StoveLook     煎锅 / 炉灶的世界外观广播：东西、两面烤到哪、翻面 / 取走 / 放不进 / 烤好的一次性事件，发给 32 格内的人（站点开不开着都一样），
                        新走进 32 格的人单发一份当前的、样子没变时每 5 秒再单发一份（广播丢了就这么补）、开站那一刻单发给开站的人
                        （Helpers/LookWatch：玩家位置快照 + 每口锅 / 灶一份"已经收到当前样子的人和时刻"）
  CookingPotHost        厨锅接入 dolorContainer：容器类型 + 方块宿主 + 界面数据读数
  CookingPotItem        厨锅拆下来带着锅里的菜、放回去菜还在（JE 的 copy_meal；规则在 Shared/Rules/PotItem.py）
  FoodBlocks Storage RopeAndNet FoodEffects Livestock Tools DisplayGuard PlayerSession LegacyApi
  TableSync             下游在服务端追加的表发给客户端：玩家进服发一次累计的差异，之后每 5 秒看表变没变、补发（客户端的站点表现读的是客户端那一份表）
  Basket                篮子吸掉落物（事件 + 每 0.25 秒轮询，由 Storage 导入来登记）；RopeAndNet 另管卷绳子、安全网弹跳，Stove 另管站上去的烫伤
  KnifeSlicing          刀切蛋糕、用刀拆派 / 蛋糕 / 南瓜掉切片（拆的时候先记切片单、方块真没了才兑现）
  ChestLoot             战利品箱第一次打开时追加 FD 的物品（JE 的 add_loot_table），原版战利品表一个字不动
  CraftReturns          工作台合成后补还无序配方的剩余物（读合成格，照 JE 放回原格 / 进背包）
  Backstabbing          背刺魔咒：玩家从背后打中目标时在 DamageEvent 里加伤害
  TatamiMats            长榻榻米垫两格一起放、一起拆（只掉一个）、长短垫脚下没了方块就碎；RopeFences  绳栅栏门右键开关
Client/                 客户端
  ModClient.py          入口：query 变量、指南书界面
  Engine.py             compFactory 等 + unwrap（客户端方块实体数据的 __value__ 解包）
  Endpoints.py          服务端调用的 4 个客户端端点
  TableSync.py          客户端端点 OnTableSync：把服务端发来的"下游追加的表内容"并进本端自己的表，重算依赖它的缓存
  BlockEntityRestore.py BlockItems.py（方块上的物品用客户端掉落物渲染）
  Input.py              跳跃键、指南书、对着方块拿原版南瓜派不吃、主手煎锅时右键的按住 / 松开上报
  BlockSparkle.py       闪亮沙拉的闪光：收到 BlockAnimateRandomTickEvent 就放 arris:sparkle 粒子
  CookingPotUi.py       厨锅的 dolor 界面：登记界面模型、导入方块宿主的客户端一半
  Ui/                   GuideBook；CookingPotProxy + CookingPotScreen 是厨锅的旧原生界面（只在 DOLOR_SCREEN 关掉时用）
Compat/
  Jei/                  arrisJei 配方页（未安装则不做任何事）
  Create/               机械动力配方（未安装则不做任何事）
  Diegesis/             场景交互前置（diegesisBp）在场时的亲手做菜站点：ServerBoot / ClientBoot 发现并登记，
                        BoardLogic + BoardSlots / BoardGive / BoardChop / BoardAssemble / BoardTools / BoardEmit（服务端）+ BoardView + BoardDraw /
                        BoardDrawEvents / BoardThing / BoardHandDraw（液体层倒、蛋层磕的那只手）/ BoardCutter / BoardEffects / BoardFx / BoardInv / BoardGlow（客户端）= 切菜板站点（切、摆盘、插工具），
                        声音按 Shared/Rules/BoardSounds，旁边没开站点的人由 Server/BoardLook 广播 + BoardWatch（客户端）补上声音；
                        PotLogic + PotSync + PotScoop（服务端）+ PotView + PotPick + PotHud + PotOffer（客户端，开着站点的人：点击、拾取盒和
                        拿着容器时哪些点法算盛、徽章和提示、悬着的容器和它浸汤的动作）= 厨锅站点；
                        PotScenes + PotScene + PotSceneFx + PotModel + PotFx + PotHands + PotBiome（客户端）= 谁都看得见的锅里场景：开盖、
                        汤面（清水按所在群系取色）、漂着的料、碎料、勺子、气泡蒸汽和声音、倒 / 磕 / 抖进锅的手部动作（docs/diegesis/DESIGN.md §10）；
                        PanLogic（服务端）+ PanView（客户端，开着站点的人）+ PanScenes / PanScene / PanModel / PanFx（客户端，谁都看得见的
                        锅里场景：食物落进来、颠锅、油膜热气）= 煎锅站点，世界外观由 Server/PanLook 广播；
                        GrillLogic（服务端）+ GrillView（客户端，开着站点的人：机位、托盘、命中盒、点击变动作）+ StoveScenes / StoveScene /
                        StoveWorld / GrillPieces / GrillSpace / GrillGhosts / GrillFx（客户端，谁都看得见的烤架场景：东西、落下 / 翻面 / 取走的动作、
                        热浪蒸汽和该翻了的烟、声音）= 炉灶站点，世界外观由 Server/StoveLook 广播；
                        DishCrafts（工作台摆出砧板菜的配方时拦下）；三个站点照 JE 的做法见 docs/diegesis/DESIGN.md §11；
                        四个站点的开关、搅拌、食谱书、烹饪倍率读 Shared/Data/HandsOnConfig（docs/diegesis/DESIGN.md §4.1）：每个站点的 register 在配置里关了返回 None
                        （服务端、客户端同一个条件），ServerBoot / ClientBoot 看返回值连带广播、场景、旁观声音、DishCrafts；
                        BookSources（客户端，把各站点的食谱书交给前置包）+ BookFill（服务端，照书从背包放料）；
                        未安装则不做任何事
```

## 分层与导入规则（tests/test_architecture.py 守着）

- `Shared/` 不导入引擎模块（`mod.*`）、`QuModLibs`、`Server`、`Client`、`Compat`、`Api`。`Shared/Menus/` 的界面模型可以导入
  dolorContainer 的纯逻辑部分（`Common/`、`Std/` 里不带 `Server` / `Client` 的模块）；库的引擎一半（`Server/`、`Client/`、
  `Std/Block/Server.py` 这类）只由 `Server/`、`Client/` 的模块导入。tests/test_cooking_pot_menu.py 在没有引擎的环境里导入界面模型，
  混进引擎的导入会让它失败。
- `QuModLibs/`、`dolorContainer/` 与生成的 `dolorLayouts.py` 是拷入件，不进下面的任何规则（完整性由 kit 与 `tests/test_dolor_vendor.py` 守着）。
- `Api/` 只导入 `Shared/`。
- `Server/` 与 `Client/` 互不导入，也不导入 `Compat/`；联动模块在 `modMain.py` 里单独登记。
  联动模块按端分：服务端的（如 `Compat/Diegesis/BoardLogic.py`）不导入 `Client/`，客户端的反之。
- 一律显式导入，不用星号导入（`modMain.py` 的 QuMod 模板除外）。
- 不出现 `import sys`、`__import__`、`namedtuple`、`eval` / `exec`、`pickle.loads`（网易机审与安全规则）。
- 每个相对导入都要解析到真实模块；层级写错只有引擎加载时才报错，还会连累整条导入链。
- 模块名不要与 py2 会被隐式相对导入劫持的名字同名（`random.py`、`time.py`、`common.py`……）。
- 单文件 ≤ 250 行（`Shared/Data/` 纯数据表除外）、单函数 ≤ 120 行。

## 服务端事件

每个引擎事件只在 `Server/ModServer.py` 里挂一次 `@Listen`，玩法模块这样登记：

```python
from .EventRegistry import registerHandler

@registerHandler("ServerBlockUseEvent", match="arris:skillet")
def OnServerSkilletBlockUse(args):
    ...
```

- `match` 可以是名字、固定名字组（tuple）、**活的配置容器**（list / dict：下游往 `StoveList` 之类追加的名字立即生效）或谓词。
  匹配键缺省是 `ModServer` 传进来的方块名 / 物品名；`keyOf=` 可以改成从事件参数里取。
- `priority` 从大到小执行；处理函数返回 `True` 时后面的不再调用。
- `ServerItemUseOnEvent` 与 `DamageEvent` 的处理函数靠顺序区分谁来处理，优先级写在 `ModServer.py` 的模块说明里，新增处理函数要按那张表选值。
- 同一次点击会同时触发 `ServerItemUseOnEvent` 与 `ServerBlockUseEvent`，按住右键时引擎每 tick 重发。
  所有交互处理共用 `Helpers.Player.SetPlayerUsedCD` 的 0.2 秒冷却：先处理的一方认领这次点击，其余在冷却内直接 return。

## 联动契约与客户端的表（下游追加的内容怎么到站点客户端）

联动契约（`Api/LegacyModAttr.py`，对外文档 linkage.md）是服务端的：`ArrisFarmersDelightInterface / Obtain / AddCookingPotRecipe` 按显式白名单把 `Shared/Data` 里的容器**按引用**交给下游，
下游在 `LoadServerAddonScriptsAfter` 里往里追加厨锅配方、砧板配方（`tool` 就是 `obtain("knifeList")` 拿到的那个列表）、可烹饪物、炉灶和热源方块，也有直接改 `obtain` 拿到的对象的。
**客户端是另一个进程，有自己的一份 `Shared/Data`，下游追加的它没有。** 经典玩法（右键）全在服务端判，不受影响；四个站点的客户端表现读的是客户端那一份，
没同步时就是"服务端认、站点客户端不认"：托盘里不亮、借不到下游的刀、点板只敲一声、下游的炉灶不开站点、食谱书里没有那一页、书里放料发的键对不上服务端的下标……

**联动契约本身一个字没动**（`tests/test_legacy_modattr_contract.py` 锁着；同步登记的容器必须就是契约交出去的那个对象，`tests/test_table_sync.py` 逐个核对）。
同步是旁路：服务端在模块导入时记下各张表的样子，下游追加完之后把"现在 - 基线"发给客户端，客户端并进它自己的表。

**同步哪些表**（表名即契约的变量名，`Shared/Rules/SyncTables.py` 登记；客户端真有地方读的才同步）：

| 表 | 下游怎么改 | 客户端哪里读 |
|---|---|---|
| `CuttingBoardDict`（键 `(物品名, aux)`） | 追加键；`tool` 引用 `knifeList` / `axeList` | 砧板 `BoardStation.Env` 的 `recipeOf / cuttable / cutsWith / isToolItem / usable / shiftPlaces`（托盘亮不亮、借哪把刀、Shift 放不放、点板是落刀还是敲一声，`BoardView.py:68-101,125-130,179`）、`BoardDraw.kindOf`（`:58`，工具类的东西是不是插着的）、`StationBooks.boardPages / boardCurrent`（食谱书"切"的页） |
| `knifeList`、`axeList` | 追加名字（`append`） | `BoardInv.isKnife`、`CuttingStation.isKnifeRecipe / fitsTool`、`BoardStation._tools`（全部配方的工具名）、`GrillStation.opens`（手里拿刀开不开炉灶，`GrillStation.py:78`） |
| `CanCookedFoodDict` | 追加键 | 煎锅 `PanStation.usable / canFry / friedOf / acceptsFryable`（`PanView.py:112,123`）、炉灶 `GrillStation.usable / canGrill / mayPlace / opens`（`GrillView.py:46,49,69`）、`StationBooks.panPages / grillPages`、手持煎锅"煎还是吃"（`Client/Input.py:42`） |
| `StoveList`、`CanProvideHeatBlockList` | 追加名字 | `GrillStation.STOVE_BLOCKS`（`GrillBlocks.GRILL_BLOCKS`：每次按 `StoveList`（还是那个列表对象）加上熄着的孪生方块现判，`GrillView.py` 交给前置包按"方块名 in 它"认站点方块：客户端先判再请求开站）、`StoveScenes`（哪些方块有场景）、`Client/BlockItems.kindOf`（灶上的东西怎么摆）、`Client/Input._nearHeat`（手持煎锅身边有没有热源，读 `CanProvideHeatBlockList`）。熄着的方块不进这两张表（不烤、不烫脚、不给锅热） |
| `CookingPotRecipeList`（按下标对应） | `interface` 追加配方；`AddCookingPotRecipe` 给已有配方的 `Recipe` 列表就地加一种写法 | 厨锅索引 `CookingPot.rebuildIndex`（`PotStation.usable / mayPlace / isIngredient / isVessel`，`PotView.py:62,65`；`PotLayout`、`vesselOf`、`cookSecondsOf`）、`PotScenes.opensStation`（`:49`，读 `Vessel`）、`StationBooks.potPages / potRecipe / potCurrent`（书页的键就是下标）、dolor 食谱书的客户端预测（`CookingPotBook`） |
| `platePackagedFoodDict` | 追加键 | `BoardInv.typeOf`（盘装的盛宴当食物，和服务端 `GetItemType` 一致） |

没有同步的（`SyncTables.NOT_SYNCED` 逐个写着原因，测试核对"白名单 = 同步的 + 这里的"，新增变量时会红）：`ComposterItemDict`、`itemChangeBlockDict`、`shapedRecipeContainerDict`、`pieList`、
`canClimbList`、`cabinetList`、`WildCropDict`、`cropsDict`、`negativeEffect`、`horseComponentsDict`、`wolfComponentsDict`（只有服务端读），`uiGuideBookPath / Screen`（字符串常量，契约没法往里追加）。
联动契约之外的表（`Dishes` 摆盘菜谱、`BrothColors / FoodColors / ItemMasks`、`Remainders`……）下游本来就够不到，没有"追加"可同步：下游的菜用兜底汤色，没有刀口遮罩。

**怎么同步**（纯规则在 `Shared/Rules/`，服务端和客户端各一个薄模块）：
- **基线与差异**（`TableDiff.Syncer`，服务端）：`Server/TableSync.py` 导入时建一个，记下各表那一刻的编码——下游在 `LoadServerAddonScriptsAfter` 里才追加，晚于任何模块的导入，
  客户端导入后的表也是这个样子。发的是**累计**的"现在 - 基线"，只含新增和改动：名字列表是基线里没有的名字；字典是键不在基线里、或值不一样的条目；
  厨锅配方按下标，新增的行和被 `AddCookingPotRecipe` 加了写法的行（带基线的行数 `base`）。**不同步删除**（契约只有追加）。
- **编码**（`TableWire.Codec`）：Call 载荷的规矩是键 `str`、列表元素类型一致、没有 `unicode`、元组到对端变列表（前置包 `Shared/Wire.py` 记着同一组，两个包互不导入，
  测试用它的 `wireProblem` 核对每条消息），所以数据表里的值要换写法：`(物品名, aux)` 压成 `{"$pair": "名字|aux"}`，别的元组 `{"$tuple": …}`，类型混着的列表 `{"$mixed": {"0": …}}`；
  **就是** `knifeList` / `axeList` 等登记过的那个列表对象的，写成 `{"$ref": "knifeList"}`，客户端换回它自己的那一个——砧板配方的 `tool` 和服务端一样是引用，之后追加的刀对所有配方一起生效。
  py2 的 `unicode` 两端各换一次 `str`。传不了的值（自定义对象、集合、键不是 `str` 的嵌套字典、嵌套超过 16 层）：**那一条跳过并记日志**（`[arrisFarmersDelight] 表同步：…`），别的照发；
  厨锅配方新增的那一行编不了时放一个空行占着下标（书页的键、书里放料发的键都是下标，后面几行不能错位）。deepcopy 不认的东西让"变没变"的快速检查退成每次重算，同步不会停。
- **并表**（`TableMerge.apply`，客户端）：就地改、不换对象（前置包拿着的容器每次按 `StoveList` 这个列表对象判）；幂等（本端已经有一样的东西就不动它：重复收、晚收都一样，
  单机联机两端共用一份表时也不会把下游手里的配方字典换成副本）；厨锅配方里本端已有的行就地合并（`Recipe` 列表原地换内容，保住 `_Ways.slots`：食谱书一格一格轮换备选要读它）；
  一条条隔离，换不回来的条目记日志跳过，消息本身不对（版本、表名、种类，或 `base` 比本端的表还长：两端不是同一版）整条不理；
  并进去有变化的表重算缓存：厨锅配方索引（`CookingPot.rebuildIndex`）和砧板的工具表（`BoardStation.invalidate`，它的缓存键现在也看 `knifeList` / `axeList` 的长度）。其它站点读表都是现读的，没有缓存。
- **什么时候发**（`Server/TableSync.py`）：① 玩家进服（`ClientLoadAddonsFinishServerEvent`：客户端刚加载完 Addon、端点已经登记好；dolorContainer 也在这时把绑定的方块名告诉客户端）
  发一次累计的差异——必须在他开任何站点之前，而且"这一下右键开不开站点"是客户端先判的（`StoveList` 里没有的方块客户端根本不会去请求开站），**所以不能等开站时再发**；
  ② 之后每 5 秒看一眼表变没变（下游可以随时追加，也可以不经接口直接改 `obtain` 拿到的对象，没有事件可听；一次检查是几张表和上次的深拷贝在 C 层比一下，开发机上不到 0.1 毫秒），
  变了就把新的一版补发给进过服的人，每张表记着自己的版本（`rev`），补发只要他没收过的那几张；没进服的人（客户端还没加载完）和走了的人不发。没有任何追加时什么都不发。
  两条路都要：万一某个环境里 `ClientLoadAddonsFinishServerEvent` 比下游的 `LoadServerAddonScriptsAfter` 还早，定时那条 5 秒内补上。热重载脚本之后进过服的名单是空的、
  也不会再有进服事件，调试时用 `TableSync.step(everyone=True)`（游戏内自检的追加函数里就是它）。
- 客户端端点 `OnTableSync`（`Client/TableSync.py`；`status()` 给调试看收了几条、改了几张、跳过几个）。

**限制**：只同步新增和改动，下游从表里删东西客户端留着（多认一个不会坏事）；只靠 `arris:knife` 物品标签认的刀（不在 `knifeList` 里），客户端只在读得到 `GetItemTags` 时才认（`BoardInv.isKnife`，
没实机核对客户端有没有这个接口）；JEI 联动（`Compat/Jei`，界面就绪时一次性登记）读的是登记那一刻的客户端表，晚到的下游内容不在 JEI 里；站点开着时表又变了，托盘亮不亮等下次开站才按新表算
（`BoardView._usable` 每次开站建一份）；已经加载好的下游炉灶方块，场景要等下次加载 / 广播才建。

## 厨锅界面（dolorContainer）

右键厨锅开的是 dolorContainer 的界面，不是 `netease:block_container` 的原生界面（阶段 A：只换界面，存储和烹饪逻辑不动）。

- 存储不变：8 个引擎容器格（`netease:block_container`，0-5 食材、6 容器、7 成品）；烹饪、热源、预览槽仍由 `Server/CookingPot.py` 在
  方块实体数据里推进，dolor 只接管界面、格子操作和食谱书。
- 打开：`Server/CookingPotHost.py` 登记容器类型 `arris:cooking_pot` 与方块宿主（库的 `Std/Block/Server.Host`）。宿主自己监听
  `ServerBlockUseEvent` / `ServerItemUseOnEvent`：对着厨锅使用时打开界面（潜行并拿着东西时放过，按住不重复开）。登记时库在运行期
  让引擎报厨锅的移除，所以方块 JSON 里**不能**再写 `netease:listen_block_remove`（两处同时开，方块和物品图标都不画）；
  `OnCookingPotRemove` 照常经 `BlockRemoveServerEvent` 收到事件。客户端那一半（`Std/Block/Client.py`）在 `Client/CookingPotUi.py` 里导入。
- 界面模型 `Shared/Menus/CookingPot.py` 两端各建一份：格子类型、Shift 点击的去向、界面数据、动作；服务端权威，客户端只预测。
  热源 / 进度 / 预览由 `CookingPotHost.readState` 从方块实体数据读，开着界面时每 4 刻重读（`dataEvery`）。手动放东西什么格子都收（与旧界面一致，
  成品格除外）；Shift 点击时容器格与食材格各挑自己收的：只当容器的碗、玻璃瓶进容器格、不会落进食材格，既是容器又是食材的卷心菜叶当食材
  （容器格里已经是它时才续上）。联机时客户端按自己的食谱表预测 Shift 点击；下游模组只在服务端追加的配方，经 `Server/TableSync` 进服时发给客户端、并进它的表
  （见"联动契约与客户端的表"），预测用的是同一批，没同步到的（条目传不了被跳过、消息还没到）仍以服务端为准。
- 食谱书：搜索、选中、换变体、"添加食材"都是动作（`search` / `pick` / `nextVariant` / `addFood`），选中的食谱和变体记在服务端会话里
  （每位查看者各一份）。客户端不传位置、玩家、背包下标；`addFood` 在会话的工作副本上从玩家背包搬运，整体成功或整体不做。
- 布局：仓库根的 `layouts/cooking_pot.json`（手写）经 `tools/vendor.py` 编译成 `rp/ui/dolor_layout_*.json` 与 `dolorLayouts.py`。
  经典版照旧界面的三栏（中间厨锅，左详情、右列表）；携带版整屏，右半屏"烹饪""食谱"两页。
- 退回旧界面：`CookingPotHost.DOLOR_SCREEN = False` 时宿主放行，引擎照旧开 `screen_name` 的原生界面。旧代理（`Client/Ui/CookingPotProxy.py`、
  `CookingPotScreen.py`）、`rp/ui/arrisCookingPot.json`、`CookingPotAddFood` 端点、`PlayerSession.py` 推食谱表的 ModAttr 都还在。
  实机验证通过后一并删：上面这些，加 `ModClient.py` 的导入、`rp/ui/_ui_defs.json` 里的登记、`tests/test_architecture.py` 里的
  `allowLong` 与 `endpoints` 的 `CookingPotAddFood`、`tests/test_dotted_paths.py` 的代理路径用例；方块 JSON 的 `screen_name` 能不能省要看引擎。

升级库或改布局：在 dolorContainer 仓库（工作区要干净）运行 `py -3 tools/vendor.py <本仓库>`，把 `dolor.lock`、`dolorContainer/`、
`dolorLayouts.py`、`rp/ui/dolor_*.json` 一起提交，提交信息写上库的提交号。改了 `layouts/*.json`、`dolor.json`、界面模型里导入的库模块
也要重新运行（`tests/test_dolor_vendor.py` 会报）。

待实机验证（写完这一版时没进过游戏）：

1. 右键厨锅只出 dolor 界面、不出原生界面（`ServerBlockUseEvent` 的取消能不能压住 `netease_container` 的 `screen_name`）。
2. `ENGINE_CONTAINER` 在 `netease:block_container` 上：放、拿、Shift、双击、数字键；烹饪 tick 改格子时界面跟得上（成品最多晚 1 秒到）。
3. 去掉 `netease:listen_block_remove` 后方块和物品图标照常画，拆厨锅时 `OnCookingPotRemove` 照常把预览格里的成品掉出来。
4. 热源、进度箭头、预览框随烹饪变化；食谱书的搜索、选中、换变体、"添加食材"（食材或空格不够时什么都不动）。
5. 携带版的两页与手柄焦点；活塞推动的厨锅、`/setblock` 出来的厨锅、断热源、成品格满了。

## 厨锅物品带着菜（对照 JE）

JE 的厨锅拆下来菜还在锅里：战利品表的 `copy_meal` 把"盛出格里那叠菜"写进厨锅物品的 `BlockEntityTag`，放回去照样在；食材格、容器格、
成品格里的东西照常掉出来；创造模式拆不出物品；物品堆叠 1；方块 `strength(0.5F, 6.0F)`。这边（`Server/CookingPotItem.py` + `Shared/Rules/PotItem.py`）：

- 方块的战利品表是空的（`air_loot.json`），厨锅物品由脚本在 `BlockRemoveServerEvent` 里掉：预览槽里煮好还没装碗的那叠菜记进物品字典的 `extraId`
  （`arris_pot_meal|物品名|aux|份数`），悬停文字写进 `customTips`（JE 的"装有 N 份：" + 菜名，前面留着 `%name%%category%…` 那几个占位符）。
  玩家是创造模式时（`ServerPlayerTryDestroyBlockEvent` 记一笔）不掉；那一格这时是移动中的方块（活塞推着走）不算拆。
  和煎锅一样，命令 / 脚本把厨锅换掉也会掉一口锅（方块没了的事件里分不出是谁拆的）。
- 放置：引擎放方块的时候看不到物品，所以放置前（`ServerEntityTryPlaceBlockEvent`，`ModServer` 新挂的监听）读手里那口锅的 `extraId` 记一笔，
  方块实体建好（`ServerPlaceBlockEntityEvent`）时写进预览槽；记录按位置、5 秒过期（放置被取消就作废）。
- 实机核对过（3.10）：装着 3 份番茄酱的厨锅拆掉，背包里是一口带 `extraId` 和"装有3份：番茄酱"的厨锅，没有散落的番茄酱、没有多掉一口锅；
  右键放回去预览槽里还是 3 份。没核对的：活塞推厨锅（脚本摆的活塞没伸出来，没测成）、爆炸、悬停文字在界面里的样子。
- 没做：JE 的 `FoodServingRecipe`（带着菜的厨锅和碗一起放进合成格直接盛出一份）——基岩版的合成结果由客户端按配方 JSON 算，按物品数据变的配方写不出来；
  物品上的份数条（`isBarVisible`）；空锅的悬停文字"空"（方块物品没有地方写缺省的悬停文字）。

## 合成与合成剩余物（对照 JE）

JE 里原料自带"合成剩余物"（`Item.getCraftingRemainingItem`）：奶桶 / 水桶剩空桶，蜂蜜瓶、FD 的饮料剩玻璃瓶，FD 的碗装食物和番茄酱剩碗。
表只有一份：`Shared/Data/Remainders.py`（`CRAFT`；厨锅另认 `POT_OVERRIDES`，即 JE 的 `INGREDIENT_REMAINDER_OVERRIDES`）。三处都按它还：

- **厨锅**：`Shared/Rules/CookingPot.pushItemsOf`，出一份吐出配料剩下的容器（番茄酱进锅会吐碗）。
- **工作台**（`Server/CraftReturns.py`）：照 JE 的 `ResultSlot.onTake`——做完一份，每格原料的剩余物放回原来那格（那格空了才放得回，同种就叠上去），
  否则进背包，背包满了掉在脚下。
  - 有序配方把剩余物写进 `result` 数组，引擎自己给（原版蛋糕就是这样还桶的）。
  - 无序配方的 `result` 数组引擎只认第一项，由脚本补：`CraftItemOutputChangeServerEvent` 时读合成格（`GetPlayerUIItem`，2×2 是槽位 28..31、3×3 是 32..40），
    对上 `Shared/Data/CraftReturns.py`（`tools/gen_crafts.py` 从 `bp/recipes` 生成：成品 -> 原料名、一份几个、哪种原料剩什么），下一刻再读一遍格子，
    按每格真的少了几件算做了几份（`Shared/Rules/Crafting.craftsDone`：被取消、请求被拒都是 0 份；同一刻玩家又挪走别的格子也不会多算，上限是取出个数 ÷ 一份个数）。
  - JE 的面团配方（`DoughRecipe`）把水桶原样留下：表里它的剩余物是水桶自己，做完水桶回到原来那格。
  - `Food.shapedRecipeContainerDict` 是 linkage 的旧接口（下游包按成品名登记"还一个容器"），生成的表里没有的成品才走它；表不能清空——
    `Interface` / `Obtain` 对空容器返回 `False`。本包留在里面的条目由 `tests/test_recipe_rules.py` 核对和生成的表一致。
- **砧板摆盘**（前置包在场）：`tools/gen_dishes.py` 给每道菜算 `extras`（换成了别的东西的容器）和 `keeps`（原样留下的配料，即面团的水桶）。
  照 HoD 的 `Assembling.make`：`keeps` 的那层每轮都放回去，不限做几份（一桶水揉完一整叠小麦），做完整层还给厨师（`DishStation.roundsOf / leftOf`）。

配方的写法也照 JE：JE 是无序的这边也是无序（面团、牛奶瓶倒回桶、蜂蜜火腿、牧羊人派、填馅马铃薯……）；标签占好几格的各格可以混着放
（熟羊肉 / 熟羊排、奶桶 / 奶瓶——有序配方把每种位置组合各写一份，左右镜像引擎自己认，只写一边）。`tests/test_recipe_parity.py` 逐条对照 JE。

前置包在场时工作台不再出砧板菜（`Compat/Diegesis/DishCrafts.py`）：拦的是"配方"不是"成品"——取结果时读合成格，格子里的原料正好是这道菜在砧板上的某条配方才取消
（`DishStation.isDishCraft`）。切片拼回整个派（一种原料）、原版自己的南瓜派配方、创造模式从物品栏拿东西（合成格对不上）都不拦。

实机核对过的引擎事实（3.10，`Server/Debug/McdkCraftTest.py`）：
- `CraftItemOutputChangeServerEvent` 一次合成请求只发一次，这时 `GetPlayerUIItem` 读到的还是合成前的格子；下一刻每格已经扣掉。
- 潜行点结果格一次做多份时 `itemDict.count` 是总数（做 3 份、一份 1 个就是 3）；成品堆叠是 1 的（奶桶）会拆成几次请求、各发一次事件。
- `CreateBlockInfo(playerId).OpenWorkBench()` 不靠方块打开工作台，同一刻就能 `SetPlayerUIItem(playerId, 32..40, …, False, False)` 摆格子（没开界面时返回 False）；
  槽位 0 是鼠标上拿着的东西。服务端摆的格子，开界面后第一次摆客户端不出结果，摆第二遍才出（玩家自己放的没有这个问题）。

## 战利品、刀与喂养（对照 JE）

- 刀杀死生物的额外掉落、玩家杀僵尸 / 灾厄村民掉洋葱：`Server/Tools.py` 在 `EntityDieLoottableServerEvent` 里把物品接在列表后面并置 `dirty`；
  表在 `Shared/Data/MobLoot.py`，概率照 JE 的 `random_chance_with_looting`（基础 + 手持物抢夺等级 × 每级加成），着火读 `CreateAttr.IsEntityOnFire`。
- 刀切：手里拿刀右键派在 `FoodBlocks.py`；蛋糕与"用刀拆方块"在 `KnifeSlicing.py`。原版蛋糕要 `AddBlockItemListenForUseEvent` 登记才有
  `ServerBlockUseEvent`；`DestroyBlockEvent` 读不到派的口数和蛋糕的状态，所以先在 `ServerPlayerTryDestroyBlockEvent`（方块还在）记一张切片单，
  方块真的没了才兑现（`Shared/Rules/Slicing.SliceTickets`，认玩家、会过期）。
- 南瓜派（JE 1.3 的 PieBlock + PlacePumpkinPieMixin）：方块 `arris:pumpkin_pie` 和另三个派走同一套（`Food.pieList` 吃一口、`Slicing.pieSliceItems` 刀切 / 刀拆），
  但它的物品是**原版的** `minecraft:pumpkin_pie`，没有自己的 `*_item`：`Food.itemChangeBlockDict` 里挂着它，`ItemToBlock.py` 对方块使用时放成方块，
  并置 `ret` 取消物品使用（JE 的 `BlockItem.useOn` 放得下放不下都不落到"吃"，所以对着方块的南瓜派吃不到，对着空气才吃）；
  JE 配置 `enablePumpkinPieSneakToPlace`（缺省关）是 `Food.PUMPKIN_PIE_SNEAK_TO_PLACE`，改成 `True` 就要潜行才放、不潜行照常吃。
  合成配方的成品、砧板配方的原料也是原版名（`tools/gen_dishes.py` 的 `DISH_RESULTS` 里写 `minecraft:pumpkin_pie`）。派方块吃一口照 JE 要饥饿值没满或创造模式
  （`Rules.Eating.canEat`），拿刀切不受限。
- 喂食（马饲料、狗粮）：`Livestock.py` 在 `PlayerInteractServerEvent` 里直接处理并取消（JE 同样用右键事件）。官方文档说这个事件在玩家"可以与实体交互"时才来，
  也就是目标对手里的物品有交互时；所以马和狼身上加了 `minecraft:bribeable` 记号（原版只有海豚用，没有自带行为，见 `Shared/Data/Mobs.py` 开头），
  否则马饲料触发不了事件、能吃的狗粮会被玩家吃掉。野生的目标也由这里接管取消，什么都不发生。
- 覆盖原版文件（猫、农民与流浪商人的交易表）：附加包里同路径的文件整份替换原版、不合并，所以是"原版整份拷来，只在列表末尾追加"，
  由 `tools/gen_vanilla_overrides.py` 生成；`tests/test_vanilla_overrides.py` 找得到本机原版行为包时逐字比对，游戏升级后原版变了就失败，重新生成即可。
- 战利品箱：JE 的 `add_loot_table` 在基岩版没有对应物，同路径文件又是整份替换，所以 `ChestLoot.py` 在 `OnContainerFillLoottableServerEvent` 里追加；
  表名是基岩版原版文件名（`shipwrecksupply` 不是 `shipwreck_supply`）。JE 里菜刀和煎锅的 `set_damage` 没搬（掉出来是满耐久）。
- 离线测试服务端模块：`tests/fakeengine.py` 把 `Server/Helpers/Engine.py` 换成假的，真正的 Helpers 和玩法模块跑在它上面。

待实机验证（写完这一版时没进过游戏）：

1. 右键驯服的马 / 驴 / 骡 / 羊驼 / 骷髅马 / 僵尸马拿马饲料、右键驯服的狼拿狗粮：回满血、状态效果各 5 分钟、扣一个（狗粮还碗）；
   对着驯服的狼右键时玩家不会开始吃狗粮（`bribeable` 记号是否让引擎当作"可用"，按钮写"喂食"）。不行的话右键事件根本不来，需要换记号组件。
2. 用刀右键原版蛋糕：不再吃蛋糕、掉一片蛋糕片，`bite_counter` 读写正常；插蜡烛的蛋糕变成少一片的蛋糕并掉出蜡烛。用刀拆派 / 蛋糕 / 南瓜掉的切片数。
3. 用刀杀着火的猪 / 疣猪兽掉烟熏火腿；抢夺等级是否读得到。
4. `OnContainerFillLoottableServerEvent` 的 `loottable` 字符串长什么样（`Rules.ChestLoot.tableKey` 兼容几种写法）、追加的物品进了箱子。
5. 引擎采用了 `entities/cat.json` 与两张交易表（猫吃鱼片、农民收洋葱、流浪商人卖种子）。
6. 南瓜派：对着方块（含潜行）按住右键拿原版南瓜派，只放下一个、不开始吃（`ServerItemUseOnEvent` 的 `ret` 压不压得住"吃"；压不住要再在
   `ServerItemTryUseEvent` / `ClientItemTryUseEvent` 里拦）；对着空气右键照常吃。放下的方块图集、四口动画、拿刀切 / 拆掉的切片数、饥饿值满时点派没反应、
   创造模式中键拾取给什么（JE 是原版南瓜派，这边多半给 `arris:pumpkin_pie` 方块物品）。

- 背刺魔咒（JE 的 `BackstabbingEnchantment`）：`bp/netease_enchants/` 和 `rp/netease_enchants/` 各放一份 `arris_backstabbing.json`
  （最高 3 级、稀有度 uncommon、`cost` = JE 的 `getMinCost`：15 / 24 / 33），规则在 `Shared/Rules/Backstabbing.py`，`Server/Backstabbing.py` 在 `DamageEvent` 里
  把伤害乘 级 × 0.2 + 1.2：伤害来源是玩家、主手物品的 `modEnchantData` 里有它、伤害来的位置（近战是玩家，弹射物是弹射物）在目标视线背后
  （来袭方向归一化后去掉竖直分量，和视线的点积 < -0.5）。JE 的魔咒类别是"刀"；网易的自定义魔咒只能从固定槽位里选，刀是 `netease:weapon` 的 sword 类型，
  所以原版的剑在附魔台上也可能出背刺（效果和 JE 一样只看主手物品上有没有它）。实机：`Server/Debug/McdkBackstabTest.py`（背后 5 → 9，正面 5 → 5）。

## 闪亮沙拉（JE 1.3 盛宴，对照 JE）

- 方块 `arris:gleaming_salad_block_stage0..3` + `_leftover`（`bp/netease_blocks/gleaming_salad_block/`）= JE `GleamingSaladBlock` 的 servings 4..1 与 0。
  盛菜走 `platePackagedFoodDict` 的通用流程（拿碗右键盛一碗 `arris:gleaming_salad`，4 份盛完留空盘，空盘再点一下收走），战利品整份掉自己、其余掉一个碗，
  整份方块物品堆叠 1（`minecraft:max_stack_size`）、被活塞推时破坏（`netease:redstone_property: break_on_push` = `PushReaction.DESTROY`，官方只认这一个值）。
  硬度 / 抗爆 0.5、声音木头；发光 = 份数 × 3；轮廓和碰撞是 JE 写死的两个盒子（`Block.box(3,0,3,13,2,13)` 与 `(2,2,2,14,6,14)`，不随份数变）。
- 配方是 JE 的 9 格无序配方（发光浆果 ×2、蜂蜜瓶、番茄、金胡萝卜、甜菜根、卷心菜 ×2、碗），蜂蜜瓶的玻璃瓶由 `Server/CraftReturns.py` 按生成的表补还（见“合成与合成剩余物”）；
  前置包在场时和别的盛宴一样改在砧板上摆（`tools/gen_dishes.py` 的 `DISH_RESULTS`，碗打底、9 层）。
- 模型：JE 的 `models/block/gleaming_salad_block_stage0..3 / leftovers.json` 用 `tools/je_model_to_netease.py` 原样转成网易方块模型
  （`py -3 tools/je_model_to_netease.py --je <JE 模型> --id arris:xxx [--icon arris:xxx_icon] --map JE贴图名=terrain_texture短名 … --out <输出>`，
  只有 stage0 带 `--icon`，贴图的对照表在 `tests/test_gleaming_salad.py`）。换算依据是 Strata 知识库 `rp/16_netease_block_model`：文件里 x 取反，
  元素旋转 x / y 轴写 `-angle`、z 轴写 `+angle`，顶面的 UV 角另排（写负的 `uv_size`）；`tests/test_je_model_convert.py` 一边按 JE 的 FaceBakery、
  一边按引擎的面表逐顶点逐 UV 对照。找得到 JE 资源时（环境变量 `FD_JE_ASSETS` 指到 `…/assets/farmersdelight`，缺省 `.refs/FarmersDelight/src/main/resources/assets/farmersdelight`），
  `test_gleaming_salad.py` 把五个模型重转一遍逐项比对。`forge_data` 的浆果自发光、`shade: false`、`cullface` 网易模型没有对应物，没搬。
- 闪光粒子：JE 的 `animateTick` 在客户端按 `0.05 × 份数` 的概率放 `SparkleParticle`（4 张 8×8、满亮度、4 刻寿命、不动）。基岩版 stage0..3 写
  `netease:block_animate_random_tick`（`trigger_rate` = 0.2 / 0.15 / 0.1 / 0.05，引擎按概率给客户端发 `BlockAnimateRandomTickEvent`，不用服务端参与），
  `Client/BlockSparkle.py` 收到就在 `Shared/Rules/Sparkle.sparkleSpot`（JE 的位置公式）放 `arris:sparkle`（`rp/particles/sparkle.json`，4 张贴图竖着拼成
  `textures/particle/arris_sparkle.png`，帧号 `floor(floor(age × 20) × 0.75)` 复现 JE 的 `SpriteSet`，寿命 0.25 秒，不写 lighting 即满亮度）。
- 没搬的：JE 的 `canSurvive`（脚下没了盛宴消失）、红石比较器输出、`isPathfindable = false`、盛菜时的方块碎屑粒子和 `BLOCK_FOOD_TAKE_PORTION` 音效（统一用
  `FoodBlocks` 里的声音）、成就。别的盛宴方块（烤鸡、南瓜盅、蜂蜜火腿、牧羊人派、饭卷拼盘）的硬度（这里都是 0.8，JE 0.5）、声音（多数 cloth，JE 木头）、
  整份堆叠（JE 1）、活塞推动与 JE 不一致，这次没动。

待实机验证（写完这一版时没进过游戏）：

1. 朝向：官方文档说 `netease:face_directional` 放置时 north 贴图面向玩家（与 JE 的 `FACING = 玩家朝向的反方向` 一致），所以模型没有预先转 180°；
   实机看第一份是不是从靠玩家的一侧盛走（stage1 少的是 JE 模型的 north 侧叶子）。
2. 模型：叶子伸出方块边界（-1..17 像素）后在区块网格里不被裁掉、镂空边缘（alpha test）正常；`use_ao` 不把整块压得过暗。
3. 发光：四个阶段实际是 12 / 9 / 6 / 3 级、空盘 0（旧写法 ×15 取整的结果）。
4. 活塞推：整份掉方块、其余阶段掉碗（`netease:redstone_property` 只在服务端生效，不同步给客户端）。
5. 闪光：`BlockAnimateRandomTickEvent` 的 `blockPos` 是方块整数坐标；闪光出现的频率合不合手感（JE 的 `animateTick` 离得近的方块估算每秒有两次机会，
   官方文档说 `trigger_rate` = 1 时 16 格内几乎每秒触发一次），不合就只调四个方块 JSON 的 `trigger_rate`（`test_gleaming_sparkle.py` 里"概率等于 0.05 × 份数"那条跟着改）。
6. 无序配方做出整份方块后返回玻璃瓶；砧板一次做多份时 `BoardGive.give` 按堆叠 1 拆开给；创造栏和背包里的方块物品是平面图标（`item_texture`）。

## 煎锅（对照 JE，FD 1.3.4）

JE 数值（SkilletItem / SkilletBlock / SkilletBlockEntity）：铁档（Tiers.IRON）耐久 250、附魔能力 14、修复材料铁锭；攻击修饰符 5.0 + 2.0 = 7
（加在玩家基础 1 上，实际 8）、攻击速度 4.0 - 3.1 = 0.9、攻击击退 +1；打一下、挖一块磨损 1 点；只有潜行才放成方块；放下去的那件连耐久 / 附魔 / 名字
存在方块实体里（火焰附加缩短方块煎的时间），拆掉由战利品表原样掉出（创造模式不掉）。一件食物煎多久 = `SkilletBlock.getSkilletCookingTime(营火配方 600 刻, 火焰附加)`：
float 运算后 6 秒，火焰附加 I 4 秒、II 起 3 秒（下限 60 刻）。`Shared/Rules/SkilletRules.cookingTicks` 逐位照抄（含 Mth.clamp 的取法，`tests/test_skillet_rules.py`）。

- 物品 JSON（`netease_items_beh/arris_skillet_item.json`）：`custom_item_type: weapon` 才会读 `netease:weapon`（以前没写，攻击 / 附魔能力 / 修复都没生效），
  `max_damage` 250（基岩版"损伤 > 最大耐久才坏"，与小刀、原版基岩工具同一个约定，不再减一）、`enchantment` 14、`level` 2（网易文档：铁砧用铁锭修）、
  `attack_damage` 7（取 JE 的修饰符，按"加在玩家基础 1 上"理解，实际 8，待实机核）、提示改成 JE 的"潜行可放置"
  （`netease:customtips` 是整段悬停文字的格式串，所以后面补了 `%enchanting%%attack_damage%`，不然附魔和攻击伤害两行可能被盖掉）。
- 放置：`SkilletItem.OnUseSkilletItem`（`ServerItemUseOnEvent`，优先级 98.5）只有潜行才放，不潜行直接拦下（不让 ItemToBlock 当普通方块物品放，也不取消引擎的 `ret`，
  右键箱子照样开箱）。放置本身仍调 `ItemToBlock.OnPlaceItemAsBlock`；放好后把那件煎锅（`SkilletRules.storeItem`：名字、附加值、耐久、附魔、提示、额外 ID、用户数据，
  元组换列表、py2 的 unicode 换 str）记进方块实体数据 `skilletItem`，方块实体还没建好就先挂在待办里，等 `ServerPlaceBlockEntityEvent` 再写。
- 拆掉：方块的战利品表改成空的（`air_loot.json`），`Skillet.OnSkilletRemove`（`BlockRemoveServerEvent`）调 `SkilletItem.dropStored` 掉出存着的那件；
  创造模式在 `ServerPlayerTryDestroyBlockEvent` 记一笔（`SkilletRules.BreakMarks`，按位置、5 秒过期），方块真没了时认这笔记录不掉煎锅；
  没存过的（/setblock、旧存档）掉一把新的。方块的火焰附加读 `skilletItem`，`Skillet._timerStart` 换成倒计时起点（秒数 + 1）。
- 含水的煎锅（液体层 `GetLiquidBlock` 有水）：放食物提示"被水泡着可没法烹饪啊……"，锅里已有的东西浮出来（JE `cookingTick`）；
  放非食物仍是"这东西可不能被烹饪……"（JE 先查配方，所以泡着水也先报这句；锅里有东西时同样报）。
- 手持烹饪（`SkilletHand`）：JE 的 `SkilletItem.use` 两只手都认（煎锅在哪只手，原料就在另一只手）。**基岩版的副手只收引擎允许的那几种物品，生肉放不进去**（实测 `SetEntityItem(OFFHAND, 生牛肉)` 返回 False），所以这边常用的是反过来拿：煎锅放副手（物品 JSON 开了 `netease:allow_offhand`）、原料拿主手，这时在热源旁按住右键是煎不是吃——客户端在 `ClientItemTryUseEvent` 里取消"吃"（`SkilletHandRules.cooksInsteadOfEating`：副手煎锅、主手有营火配方、身边 3x3x3 有热源；JE 里饿着的时候主手的食物会先被吃掉，这里改成有热源就煎，不然基岩版饿着就没法手持煎东西了）。下面说的"副手食物"换成这种拿法就是主手的那件。
  基岩版没有"按住使用"的服务端事件，由客户端在主手或副手拿着煎锅时报告右键：`RightClickBeforeClientEvent` 报一次，按住期间 `OnScriptTickClient`
  每 0.2 秒报一次，`RightClickReleaseClientEvent` 报松开（`Client/Input.py` + `SkilletHandRules.HoldReporter`，RPC `SkilletUseHeld`）；服务端按最后一次"按着"的时间判断还按不按着
  （超过 0.8 秒没消息就当松手）。每次"按着"没有在煎的话就是 JE 的 `use()`：主手煎锅，着火或脚下 3x3x3 有热源（只看方块名，不看营火 / 炉灶点没点着，与 JE 一致），
  副手食物在 `CanCookedFoodDict`（= JE 营火配方 16 条，补上了海带），头没泡在水里（脚 + 1.62 那一格的液体层）→ 开始；副手没食物 / 不能煎提示"用另一只手拿着原料！"，
  泡在水里提示"在水里可没法煎啊……"，没热源什么都不说；潜行时不提示（潜行右键方块是放煎锅，JE 那一下不走 `use()`）。按满 6 / 4 / 3 秒做好：副手少 1 件（创造模式也扣，JE 就是这样）、
  成品进背包（`GiveOrDropItem`，满了掉脚下）、不磨损煎锅；中途松手、换主手物品、掉线什么都不做——食物到做好那一刻才从副手拿走，所以不会丢东西
  （JE 是开始就拿走、松手放回背包）。按住不放，下一次"按着"的报告接着煎下一件（JE 按住右键每 4 刻重新使用）。滋滋声每刻 1/50（每 0.25 步 9.6%），只发给自己（JE 是本地声音）。
- 耐久：`ItemDurabilityChangedServerEvent`（`ModServer` 新挂的监听）里 `SkilletRules.wearAfter`：一次磨损超过 1 点就改回 1（基岩版自定义武器打一下磨损 2 点，原版剑 1 点），
  修复不动，引擎说不能改（`canChange` 假）时不动。**挖方块不另外扣**：引擎对自定义物品挖方块是扣 0 点还是 2 点这里没法核实，加一道脚本扣可能重复，
  所以交给引擎（扣 2 点时上面的夹取会把它压成 1 点）。
- 打人：JE 的攻击速度 0.9 次 / 秒、冷却不够伤害变小、击退 +1，基岩版都没有（没有攻击冷却；`DamageEvent` 只能开关击退，`SetMobKnockback` 的方向约定离线核不了，所以没做击退）。
  只保留 JE 的声音分档：`PlayerAttackEntityEvent` 里按距上次挥煎锅的时间挑 `attack_strong`（够 0.8 × 22.2 刻 ≈ 0.89 秒）或 `attack_weak`（音量 0.8、音调 0.9，
  `sound_definitions.json` 里补了定义）。JE 里切物品也会重置冷却，这里不管。
- 没做：JE 的进度条（客户端物品装饰，基岩版画不了）、翻面动作（左键翻面，纯画面）、煎锅里的食物在手上的渲染、同种食物往锅里叠加（`ItemStackHandler.insertItem`，现在锅里有东西就不收了）、
  `minecraft:lava_cauldron`（基岩版是 `cauldron` 加 `cauldron_liquid` 状态，热源表按方块名，认不出）、含水放置（现在只往空气里放）。

待实机验证（写完这一版时没进过游戏）：

实机核对过（3.10，MCDK 后台模式的 mc_input）：不潜行右键不放、潜行右键放出煎锅；带火焰附加 II、耐久 200 的煎锅放下再拆，拿回的还是那一把（附魔、耐久都在）；副手煎锅、主手 3 块生牛肉站在点燃的炉灶旁按住右键 6.9 秒：生牛肉剩 2、背包多 1 块熟牛肉、饥饿值没变（没吃）；按 3 秒松手什么都没变；右键的按下 / 每 0.2 秒 / 松开上报都到了服务端。下面是还没核对的：

1. 火焰附加 I / II 手持是 4 / 3 秒；煎锅在主手、能进副手的原料在副手的那种拿法；
   `RightClickBeforeClientEvent` / `RightClickReleaseClientEvent` / 每 0.2 秒的上报确实到服务端（手柄、触屏"新交互键"也算，经典触屏的长按可能要另外接 `HoldBeforeClientEvent` / `TapOrHoldReleaseClientEvent`）。
2. 潜行右键方块放出煎锅，不潜行右键不放；放完不会在炉灶边冒"用另一只手拿着原料！"；站在炉灶 / 营火旁右键箱子仍然开箱。
3. 带附魔、磨损过的煎锅放下再拆，掉出来的还是那一把（耐久、附魔、改名都在）；创造模式拆不掉煎锅；爆炸 / 命令拆会掉。
4. 煎锅物品的数值：新煎锅打僵尸一下掉 8 点血（`attack_damage` 7 加玩家基础 1；若掉 7 点就改成 8）；打一下耐久只少 1；铁砧用铁锭能修；附魔台能出火焰附加 / 锋利等；
   3D 手持模型（`attachables/skillet_item.json`）在变成武器类物品后姿势没变；悬停文字：潜行可放置 / 附魔 / 攻击伤害各一行、没有重复
   （重复了就去掉 `%enchanting%%attack_damage%`，缺了就说明格式串是替换式的、现在的写法对）。
5. 放下的煎锅：火焰附加 I / II 煎一件 4 / 3 秒；水能不能流进煎锅所在的格（`GetLiquidBlock` 读到水）——能的话放食物提示、锅里的东西浮出来。
6. 打人音效：连点是轻击、隔 1 秒再打是重击。

## 篮子、绳子、安全网、炉灶（对照 JE）

JE 依据：FD 1.3.4 的 BasketBlock / BasketBlockEntity / Basket、RopeBlock、SafetyNetBlock、AbstractStoveBlock、ModDamageTypes、ModBlocks、Configuration。

- 木篮 `arris:wooden_basket`（JE wooden_basket）：方块 JSON 与竹篮一份（27 格箱子、碰撞盒、斧挖、`on_entity_inside`），模型是竹篮模型整份拷贝、只改 description 的标识与贴图名，
  贴图是 JE 木篮四张拼成的 32×32 图集（左上 handle、右上 side、左下 bottom、右下 top，和 `basket.png` 的格子用法一致）。
  不用"两个方块共用一个 `netease_model` 再各写 `model_textures`"：那会改写全局模型对象，还会让竹篮的物品图标也变成平面图（NM §3.4）。
  配方（木棍 + 帆布，摆法同竹篮）与砧板（斧 -> 帆布 + 木棍）照 JE。两种篮子的硬度、爆炸抗性都是 JE 的 1.5。
- 篮子吸掉落物（`Server/Basket.py`，规则在 `Shared/Rules/Basket.py`），照 JE BasketBlockEntity：
  - 收集区 = 篮子自己那一格 + 朝向那一格（JE 六种朝向的盒子都写在 `AREAS` 里）。本模组的篮子 `face_directional` 只有水平四向、碰撞盒也只朝上开口，所以取朝上：身体加上面一格，1×2×1。
    判断用掉落物碰撞盒（0.25）与收集区严格相交（边贴边不算）。
  - 往 27 格里塞照 `putStackInInventoryAllSlots`：从 0 号格往后逐格试，遇到空格整堆放进去、遇到同种没满的补满，哪一格先遇到用哪一格——
    **不是**先补同种再找空格（0 号格空着、5 号格有半堆同种时，整堆进 0 号格）。同种 = 名字、aux、userData、附魔、tips、extraId 都一样。
    27 格全是满堆不吸；吸一半的，剩下的在原处重新放一个掉落物（基岩版改不了掉落物的数量）。原来的实现没传 `getUserData`，带数据的物品会丢数据，现在带上。
  - 冷却：吸进一整个掉落物之后 8 刻（0.4 秒）不再吸（`transferCooldown`）；没吸成（满了、被红石锁住）每 0.2 秒再试（JE 每刻都试，这边每次试要读 27 格）。
  - 红石：邻居有信号（`CreateRedStone.GetBlockPoweredState` 非 0）时不吸，对应 JE 的 ENABLED 状态。
  - 篮子是 `netease:block_chest`，没有方块实体 tick（`netease:block_entity` 要网易的 ModBlockActor，箱子是原版 ChestBlockActor，一个方块只能有一种方块实体 [推断，没在游戏里试过两个组件并用]），所以两条路共用 `pull` 和一份冷却：
    掉落物进了篮子这一格走 `OnEntityInsideBlockServerEvent`；上面那一格靠每 0.25 秒一次的轮询——`GetEngineActor()` 一次拿到全部已加载实体（带维度和类型名），挑出掉落物，
    用 `basketCells` 找收集区碰得到它的篮子。不登记篮子的坐标，`/setblock`、结构放出来的篮子照样吸。定时器在第一个玩家进服（或第一次有东西落进篮子）时开。
    JE 的 `onEntityCollision` 是死代码（BasketBlock 没覆盖 `entityInside`），篮子只靠 `pushItemsTick`。
- 卷绳子（`RopeAndNet.OnUseRope`，`Shared/Rules/RopeReel.py`），照 RopeBlock.use：手里空着；配置 `enableRopeReeling`（JE 缺省开，`Shared/Data/Blocks.enableRopeReeling`）且潜行时，
  从被点的绳子往下数、一路都是 `arris:rope`，拆**最下面**那一节（`destroyBlock(pos, false)`：不掉落，所以用 `SetBlockNew(…, 0)` 而不是 1），给玩家背包放一根绳子；
  创造模式不给；没有建造权限（`GetPlayerAbilities()["build"]`，对应 mayBuild）或背包放不下什么都不做，也不会转去敲钟。
  不潜行（或配置关了）时才敲钟，一路连着往上最多 24 格的钟；敲钟也要空手（原来拿着东西也敲）。
- 安全网（`RopeAndNet.OnFallOnSafetyNet`，`Shared/Rules/NetBounce.py`），照 SafetyNetBlock：不潜行时 `causeFallDamage(fallDistance, 0.0F)`，没有任何摔落伤害；
  竖直速度反过来：生物（LivingEntity，`IsLiving` 看 `EntityType.Mob`）乘 0.6，其它实体（掉落物、船、矿车……）乘 0.8；潜行（`isSuppressingBounce`）照常摔、不弹。
  引擎事件只给摔落距离，撞上去的速度用自由落体推回来（每刻先按当前速度走一步，再 v = (v + 0.08) × 0.98，末速度 3.92 格/刻；10 格落差约 1.14 格/刻），
  所以弹起的速度是 0.6（或 0.8）× 撞击速度，原来自拟的曲线（10 格落差给 1.0 格/刻）作废。落差不到 0.5 格不弹（JE 站在网上会一直微微颠，这里不跟，也省得事件连发）。
- 炉灶烫伤（`Stove.OnStandOnStove`，`Shared/Rules/StoveBurn.py`），照 AbstractStoveBlock.burnEntitySteppingOnStove：站在点燃的炉灶上，
  碰撞盒碰到烤架区（`Block.box(3,0,3,13,1,13)` 平移到炉灶上面一格）、没潜行、是生物、脚上没有冰霜行者（鞋子附魔里没有 `EnchantType.FrostWalker`）就受 1.0 点伤害（半颗心），
  之后靠引擎的无敌帧（10 刻，和 JE 的 invulnerableTime 一样）每 0.5 秒扎一下。点燃的炉灶 JSON 带 `netease:on_stand_on`（熄灭的 `arris:stove_extinguish` 是另一个方块，不带），
  事件 `OnStandOnBlockServerEvent` 在 `ModServer.py` 里挂了监听（第 31 个）。点燃亮度 13、硬度 2.0（copy BRICKS）也照 JE 改了。
  - 伤害类型：JE 的 `stove_burn`（死亡信息 `death.attack.farmersdelight.stove`：%1$s被烤的酥脆）基岩版给不出。引擎的死亡信息是 `ActorDamageSource::getDeathMessage` 按 cause 查固定的表，
    `magma`、`custom` 等表外的 cause 一律落到 `death.attack.generic`（"死了"），网易的 `Hurt(…, "custom", customTag)` 只是给伤害事件打个标记、不改消息，也没有找到换死亡消息的接口。
    所以取最接近的 `magma`（JE 里岩浆块的 hot_floor 正是这个脚感）：好处是 `fire_immune` 的实体（烈焰人、岩浆怪、凋灵骷髅……）引擎本来就对 magma 无敌，对上 JE 的 `fireImmune()`；
    代价是抗火药水大概也会挡住（JE 的 stove_burn 不在 `is_fire` 标签里，抗火拦不住）。护甲照常减伤（两边都不绕过护甲）。
- 外加 `tests/test_event_wiring.py`：服务端每个 `registerHandler` 的事件在 `ModServer.py` 里都要有 `@Listen`；需要触发组件的事件，方块 JSON 里要带那个组件。

待实机验证（写完这一版时没进过游戏）：

1. 篮子：扔进篮子的掉落物被吸进 0 号格、附魔 / 命名物品数据不丢；同种补满再进下一格；两个篮子上下叠放时一个掉落物只进一个；
   接红石（拉杆贴着篮子，或旁边放红石块）停吸、断开 0.2 秒内恢复；篮子上面一格里的掉落物（比如放块地毯 / 半砖挡着让它浮在那）被轮询吸走；
   27 格满堆不吸；只剩一格半堆时吸一半、剩下的原地留一个掉落物；活塞 / `/setblock` 出来的篮子也吸；`GetBlockPoweredState` 对非实心的篮子是否如实回答。
2. 卷绳子：潜行空手右键绳子卷掉最下面一节、背包 +1、不掉落、有拆绳子的声音；点中间一节也是拆最下面；背包满了什么都不发生；创造模式不给；冒险模式不行；不潜行空手敲钟，手里拿东西不敲；
   潜行时 `ServerBlockUseEvent` 是否照来（原版容器潜行空手能开，绳子应同理）。
3. 安全网：从 10 / 30 格落下不掉血、弹起约落差的三分之一（玩家）；潜行落下照常摔且不弹；牛 / 掉落物也弹（掉落物更高）；
   `SetPlayerMotion` 的单位按"格/刻"用，弹得过高或过低就要重标定 `NetBounce`。
4. 炉灶：`netease:on_stand_on` 让 `OnStandOnBlockServerEvent` 每刻来一次（对玩家和怪都来）；站在点燃的炉灶中央每 0.5 秒掉半颗心，潜行不掉，穿冰霜行者不掉，站在熄灭的炉灶上不掉，
   烈焰人 / 岩浆怪不掉；死亡信息是引擎的"死了"；点燃后亮度 13。

## 榻榻米垫与绳栅栏（对照 JE）

- 长榻榻米垫（JE `TatamiMatBlock`，像床的两格方块）是两个方块：`arris:tatami_full_mat`（脚，物品就是它）和 `arris:tatami_full_mat_head`
  （头，技术方块，不进创造栏），模型和 JE 的 `tatami_mat_foot` / `tatami_mat_head` 一一对应（odd / even 顶面、inner 接头面）。
  放置在 `Server/TatamiMats.py`：`ServerItemUseOnEvent` 里自己放两格并取消引擎的放置（`ret`，同 `WildCrops` 的做法），朝向用玩家的 yaw
  （`Placement.facingOfYaw` -> `directionOfFacing`，direction 的编号见官方文档：south 0、west 1、north 2、east 3，方块前面朝向玩家），
  头在放置者面朝的方向；头那格要能被顶替（空气、草、水……）、两格下面都不是空气，放不下什么都不做。点到砧板、厨锅、煎锅、炉灶、橱柜、篮子、
  展示框这些自己会处理右键的方块时不放、不抢交互冷却，潜行才放（JE：方块的 use 优先；短垫子由引擎放，这个先后引擎自己会排）。
  拆：不挂拆除事件，两个方块都开 `netease:neighborchanged_sendto_script`，一半变成别的方块，另一半在邻居变化里静默清掉（不掉落、不通知邻居）；
  掉落全交给被拆那一半的战利品表（头的表指向长垫子，脚掉自己），所以整张只掉一个、创造模式一个不掉。脚下变空气时先静默清掉另一半，
  再把这一半以"销毁"（`SetBlockNew` 第三个参数 1）清掉，同样只掉一个；短垫子也走这一条（JE 的 `canSurvive`），放置时下面是空气会被取消。
  与 JE 的差别：两半都 `break_on_push`（被活塞推会碎成一个掉落物；JE 里长垫子能被推，推一半会留下一个孤零零的头）。
- 榻榻米合成照 JE 四条无序配方（方块 -> 2 长垫、2 短垫 -> 1 长垫、1 长垫 -> 2 短垫、2 长垫 -> 1 方块），原来基岩版自加的"方块 -> 4 短垫"去掉了。
- 绳栅栏（JE `RopeFenceBlock`）没有脚本：连不连邻居靠方块 JSON 的 `netease:connection`（按标识符列名单）和模型 / 碰撞盒里的
  `query.is_connect(面)`（2 北 3 南 4 西 5 东）。名单 = 实心整格的原版方块（引擎方块表里形状是整格的，去掉树叶、屏障、南瓜、西瓜、潜影盒这些
  JE `isExceptionForConnection` 的例外，约 490 个）+ 本模组的整格方块（箱子、橱柜、草垛、榻榻米、沃土、炉灶……）+ 绳栅栏自己和它的门。
  所以不连原版栅栏 / 墙 / 玻璃板（JE 里它们的面不是实心的，原版栅栏还被 mixin 明着拒绝），别的模组的实心方块也不连（名单是静态的）。
  碰撞盒是 JE `CrossCollisionBlock(1, 1, 16, 16, 24)`：中间柱 + 四条臂，选取框高 1、碰撞高 1.5（`netease:aabb` 的 `max` 能写到 2）。
- 绳栅栏门（JE `RopeFenceGateBlock`）是两个方块：`arris:rope_fence_gate`（关着）和 `arris:rope_fence_gate_open`（开着，不进创造栏，
  没有碰撞、`netease:pathable`），右键由 `Server/RopeFences.py` 换成另一个并写回朝向（`Shared/Rules/RopeFence.toggleGate`：从门背面开会先转向，
  和 JE `FenceGateBlock.use` 一致），声音是 `leashknot.break`（打开）/ `leashknot.place`（关上），即 JE 的 `entity.leash_knot.*`。
  两侧都是墙时模型换成"在墙里"的样子（JE `in_wall`，这里按"两侧都是墙"，名单是原版的 26 种墙）。门的碰撞 / 选取框写在 `direction`
  未旋转的坐标里，靠引擎随朝向转（本机别的附加包里带 `direction` 的竖半砖等方块都是这么写不对称碰撞盒的，引擎源码里盒子也是存成以方块中心为原点的，
  但这一条没有实机核实过）。
- 模型里的零厚度片（栅栏的臂、门的布）用一个面双面渲染：栅栏臂贴图左右镜像对称，所以背面和 JE 的另一个面完全一样；门的布两面颜色略有差别，
  所以北、南各出一片并错开 1/16 像素（网易模型坐标的最小刻度）。
- 没做的：拴绳（JE 的 `use` 里 `LeadItem.bindPlayerMobs`）、红石开关门、`waterlogged`、栅栏只连"门轴向对得上"的门（现在连所有朝向）、
  JE 放置门时"任一侧是墙就画墙里的样子"（现在只认两侧都是墙）、`fences` / `fence_gates` 标签、`combination_step_sound_blocks` 标签。

待实机验证（写完这一版时没进过游戏；Strata 沙箱已把放置、邻居变化、开关门的脚本跑过一遍，模型也出过图）：

1. 长垫子：右键地面两格一起出现，头在面朝方向；四个朝向下头的位置对、两个接头面贴在一起、顶面 odd / even 接得上（若头出现在反方向，改
   `Placement.directionOfFacing`）；引擎自己没有多放一个脚（`ret` 取消了方块物品的放置）。
2. 头那格被占 / 下面是空气 / 点的是草 / 冒险模式 / 按住右键：分别什么都不放 / 放进草那格 / 不能放 / 不连放；拿着长垫子点橱柜、厨锅
   这些：开界面而不是放垫子，潜行才放。
3. 拆脚、拆头（生存、创造）、活塞推、爆炸、`/setblock air`：另一半跟着没，生存只掉一个；脚下方块被拆整张碎、掉一个；短垫子同理，
   也不能放在悬空的格子。创造模式中键点头方块拿到的物品能当长垫子放。
4. 栅栏：`netease:connection` 里写 `minecraft:` 开头的名字能连上（碰撞盒的 `enable` 也能）；碰撞高 1.5 挡得住跳；相邻原版栅栏 / 墙 / 玻璃板
   不连；两个栅栏、栅栏和门相连；栅栏物品图标。
5. 门：东西向的门碰撞盒 / 选取框跟着转（若不转，门要拆成东西两个方块）；两侧是墙时的样子；开关的模型、朝向、声音；开着的门能走过去、能点中关上；
   关着的门 1.5 高挡得住；门布的两片没有闪烁。
6. `netease:fuel`（长垫子 / 栅栏 / 门 10 秒，榻榻米 20 秒，短垫 5 秒，绳子 10 秒）在熔炉里的时长（200 刻 = 10 秒，榻榻米 400 刻）。

## 引擎坑（踩过的）

- 方块实体数据（`GetBlockEntityData`）是引擎对象，不是 dict：没有 `.get()`，缺键读出来是 `None`，用 `data["k"] or 缺省值`。
- `netease:face_directional` 的缺省状态 `direction = 0` 会把网易方块模型转 180°（Strata 的 `render --block` 不给状态就是这样），玩家放置时官方文档保证 north 贴图面向玩家；
  所以模型照 JE 的朝向原样转，和 JE 对照出图时要加 `--state direction=2`（不转）。
- 旧写法 `minecraft:block_light_emission` 是 0~1 的小数，引擎 ×15 取整：写 0.8 / 0.6 / 0.4 / 0.2 这种乘 15 正好落在整数上的值，别靠取整的方向碰运气。
- 它的读取走 Python 侧缓存，**只有赋值才会写进引擎、随存档落盘**，缓存在区块卸载时丢弃：
  改了取回来的字典 / 列表之后一定要整体赋值回去，否则区块卸载后恢复原值（煎锅曾因此刷熟食）。
  键必须是 `str`、列表元素类型要一致、值不能是 `unicode`，不满足时引擎只打日志不报错。
- `/setblock`、`/fill`、结构放出来的方块不走 `ServerPlaceBlockEntityEvent`，方块实体数据里没有初始化过的键，读取处要补默认值。
- `ServerBlockUseEvent` 的取消字段是 `cancel`；`ServerItemUseOnEvent` 的是 `ret`。
- `DestroyBlockEvent` / `BlockRemoveServerEvent` / `BlockRandomTickServerEvent` 的方块名字段是 `fullName`，其余事件是 `blockName`；
  `BlockRemoveServerEvent` 的维度字段是 `dimension`。
- 营火点燃 / 熄灭只改 `extinguished` 状态、名字不变：判断热源要读状态（`Helpers.Heat.IsHeatSource`）。
- 客户端读方块实体数据拿到的是 NBT 形式，每个值包成 `{"__type__": …, "__value__": …}`（`Client.Engine.unwrap`）。
- 世界时间（`CreateTime().GetTime()`）会被 `/time set` 改、被 `doDaylightCycle false` 冻住，不能拿来做 tick 节拍：
  用 `Shared/Rules/Ticks.Pacer`（真实时间）。
- 客户端读方块实体数据时，服务端存的 None 可能读成整数之类的占位，先校验类型再用（`BlockDisplay.isItem`）。
- 服务端 `SetBlockNew` 放的方块，客户端不发 `ModBlockEntityLoadedClientEvent`；这个事件也可能重复触发——客户端渲染要幂等，
  内容以服务端广播为准。
- 客户端掉落物（`AddDropItemToWorld`）：轴心在贴图底边中点，缩放 1 时半格；`SetDropItemTransform` 的 `rot=(x,y,z)` 是
  R = Rz·Rx·Ry，"躺平后再绕竖轴转"要先拼矩阵再换算（`ItemPose.engineEuler`）。
- 新加的自定义魔咒（`netease_enchants/`）、方块、物品定义要**完整重启游戏**才登记，重进存档不够（配方 JSON 重进存档就生效）。
- 服务端取消 `ServerItemUseOnEvent`（`ret`）拦不住客户端接着"使用物品"（吃）：原版南瓜派对着方块按住右键，放下一个之后还会吃掉一个。
  要在客户端 `ClientItemTryUseEvent` 里取消（`Client/Input.py`：准星对着方块时不吃，`CreateCamera.PickFacing()` 的 `type == "Block"`）。
- QuMod 的 RPC 端点按裸函数名注册：服务端端点一律 `@AllowCall` + `@InjectHttpPlayerId`，玩家身份只认注入的，坐标、维度、背包下标都要校验。
- `OnScriptTickClient` 这类每帧事件引擎不带参数，处理函数写 `def f(args=None)`（Strata 沙箱 `script inspect` 抓到的）；`ItemPosType`：背包 0、副手 1、主手 2、盔甲 3。
- Netease 没有"按住使用"的服务端事件（据引擎反编译，武器类物品的 `use` 不会 `startUsingItem`，没实机核），要知道玩家有没有按住右键只能让客户端报告
  （`RightClickBeforeClientEvent` / `RightClickReleaseClientEvent` + 每帧事件里的心跳，服务端对超时的当松手）。

## 新增内容的清单

新食物 / 方块 / 配方需要同时改：
1. `Shared/Data/` 对应的表（厨锅配方、砧板配方、可烹饪食物、作物阶段……）；
2. `bp/netease_items_beh/`、`bp/netease_blocks/`、`bp/recipes/`、`bp/loot_tables/` 的定义；
3. `rp/` 的贴图、模型、`netease_items_res`、`blocks.json`。
   JE 的方块模型（盛宴一类）用 `tools/je_model_to_netease.py` 转，不手抄坐标（见"闪亮沙拉"一节）。

Python 只管运行时行为，物品 / 方块是否存在由 JSON 决定。

## 测试

```
py -3 tools/run_tests.py           跑全部（按每个文件第 2 行的 "# runner: py2|py3|both" 选解释器）
py -3 tools/run_tests.py cooking   只跑文件名含 cooking 的
```

`tests/` 只测不依赖引擎的部分（`Shared/`、`Api/`、`Server/EventRegistry.py`）和静态结构；
与引擎交互的部分用 Strata 的 `script_inspect` / `script_run`（沙箱加载、按剧本驱动事件）和游戏内实测。

- `fdtest.py`：农夫乐事包的导入与用例收集；`test_handson_*.py` 是 HoD 规则内核的测试。
- 食物 / 小刀对 JE 1.3.4 的核对：`jefood.py`（参照表，抄自 FoodValues.java / ModItems.java，不依赖 .refs）、`test_food_values.py`
  （营养、饱和度、容器、使用时长、效果、提示）、`test_knife_values.py`（耐久、附魔能力、防火）；`test_food_effects_rules.py` 测
  `Shared/Rules/FoodEffects.py`，`test_food_effects_server.py` 把假的 Engine 模块塞进 `sys.modules` 来驱动 `Server/FoodEffects.py` 的事件处理。
- JE 方块模型转网易模型：`test_je_model_convert.py`（转换工具对 JE 烘焙规则逐顶点逐 UV）；闪亮沙拉：`test_gleaming_salad.py`（方块 / 战利品 / 盛菜 / 模型 / 砧板摆盘，
  JE 资源在场时重转模型比对，`FD_JE_ASSETS` 指定位置）、`test_gleaming_sparkle.py`（闪光的概率 / 位置 / 粒子文件 / 客户端处理，假的 `Listen` 与 `compFactory`）。
- 篮子 / 绳子 / 安全网 / 炉灶（对照 JE，期望值抄自 JE 代码）：`test_basket_rules.py`（收集区、塞的次序、冷却）、`test_basket_server.py`（接线：事件与轮询两条路、红石、
  满了、吸一半、叠放的两个篮子）、`test_rope_reel.py`、`test_safety_net.py`、`test_stove_burn.py`、`test_wooden_basket.py`（配方 / 砧板 / 模型 / 贴图 / 名字）、
  `test_block_strength.py`（硬度 / 爆炸抗性 / 亮度）、`test_event_wiring.py`（每个 `registerHandler` 的事件在 ModServer 里有 `@Listen`，触发组件在方块 JSON 里）。
  `RopeAndNet` 导入了离线导入不了的 `QuModLibs.Server`，这几个测试先往 `sys.modules` 里塞一个只有两个装饰器的替身。
- dolorContainer：`test_dolor_vendor.py`（库文件与编译产物的哈希、界面文件登记、导入闭包；随库装入，不手改）、`test_rpc_caller_id.py`
  （客户端可调的服务端端点只用注入的玩家 ID；随库装入）、`test_cooking_pot_book.py` / `test_cooking_pot_menu.py`（厨锅的食谱书规则与
  界面模型，用库的纯逻辑部分在内存里跑，py2 与 py3 都跑）。
- 场景交互前置包（`diegesisBp/arrisDiegesisScripts/`）的测试也在这里：`dgtest.py`（导入 + 假的引擎端口 FakeWorld）、
  `dgkit.py` / `dgfixtures.py`（内核测试的断言与站点夹具），`test_diegesis_*.py`。`test_architecture.py` 同时守两个包。
- 合成：`test_recipe_rules.py`（配方 JSON 的静态检查、生成的 `CraftReturns` 表是否最新）、`test_recipe_parity.py`（对照 JE 的做法 / 摆法 / 剩余物）、
  `test_crafting_rules.py`（`Shared/Rules/Crafting.py` 和 `Server/CraftReturns.py`，`fakeengine.py` 的假合成格驱动）；背刺：`test_backstabbing.py`。
- 下游追加的表同步到客户端：`tablekit.py`（把行为包脚本根换个顶层包名再导入一遍，得到"另一个进程"里各自的 `Shared/Data`；`downstream()` 照 Ends Delight 的写法经联动契约追加；
  `transport()` 先过前置包 `Shared/Wire.py` 的规矩、再 JSON 来回，py2 里字符串变 `unicode`、元组变列表，和网络上一样）；`test_table_wire.py`（编码）、`test_table_sync.py`（一份包当服务端、
  一份当客户端：内容一致、`tool` 引用、幂等、`AddCookingPotRecipe`、之后追加的只补变了的表、传不了的跳过、不是同一版不并、坏消息不理）、`test_table_sync_stations.py`（真的客户端类：
  砧板 / 煎锅 / 炉灶 / 厨锅 / 四本书对着下游追加的东西，并表前说不认、并表后认）、`test_table_sync_server.py`（进服发一次、定时补发只发变了的表）、`test_table_sync_selftest.py`（游戏内自检的两半）。
- 游戏内自检：`Server/Debug/McdkSelfTest.py`（`mcdk_test_run()` / 约 15 秒后 `mcdk_test_collect()`），含切菜板站点用例
  （直接驱动前置包的 Manager，与客户端点击走同一条校验路径；前置没装时跳过）。同目录还有 `McdkDishTest`（砧板摆盘、一桶水揉一叠面团）、
  `McdkBookTest`（食谱书放料）、`McdkPotTest` / `McdkPanTest` / `McdkGrillTest`（三个站点的烹饪；`McdkGrillTest` 还有炉灶四个朝向的自检：服务端读 direction 状态 / aux /
  站点朝向钩子，客户端 `Client/Debug/McdkGrillTest` 读同一格的 aux 和客户端的钩子，在游戏里对起来）、`McdkStoveFireTest`（点火 / 灭火换方块：记下引擎事件到的先后、核对东西带过去，`start` / `collect`）、`McdkCraftTest`（工作台合成：摆格子、
  点结果格、核对剩余物和拦截，要用 mc_input 点）、`McdkBackstabTest`（背刺），调用方法写在各文件头。几个自检别同时跑（共用玩家脚边的位置）。
  `McdkTableSyncTest`（服务端 `Server/Debug/` 照下游的写法追加石剑当刀、黏土球的切菜配方、木棍 / 圆石煮钻石的厨锅配方、胡萝卜可煎烤，再补发；客户端 `Client/Debug/` 用
  `is_client` 为真的 `execute_code` 看本端的表和站点判断认不认得）。
- HoD 的配置（对照 `HandsOnConfig.java`，期望值抄自 JE 代码）：`optkit.py`（`with Config(skillet=False, ...)` 临时改配置表、出来放回原样）、`test_handson_options.py`（随包的表等于 JE 缺省、读法、
  派生规则、`scaled`）、`bootkit.py` + `test_handson_options_boot.py`（真的 `ServerBoot` / `ClientBoot` 和站点模块，引擎换成"什么名字都给无害替身"的模块，前置包服务端 Api 和客户端 Registry 是真的：
  每个开关只关自己的站点和连带的东西、32 种组合两端一致）、`test_handson_options_pot.py` / `_pan.py` / `_skillet.py` / `_stove.py`（三种倍率对着 JE 的 `sideTicks` / `timeFor`、FD 右键放的不乘、站点关了的交还）、
  `test_handson_options_book.py`（食谱书开关）；`test_pot_view.py` 里还有拿着容器点锅的哪些节点算盛。
- 直接用 `python` 跑单个测试文件会在包目录里留下 `.pyc`；用 `tools/run_tests.py`（它设了 `PYTHONDONTWRITEBYTECODE`）。
