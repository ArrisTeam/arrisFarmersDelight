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
  Rules/                纯规则：CookingPot（配方匹配 / 出料结算） CropGrowth（催熟阶段表） Placement（朝向 / 放置位置） Ticks（错峰 / 概率）
                        CookingPotBook（厨锅食谱书：容器格号、搜索、详情格、补食材的计划）
                        CuttingStation（切菜板站点：FD 配方 -> 刀口计划、工具判定、整批产物）
                        PotStation（厨锅站点：份数、放料、按配方把料摆进几格、取回、徽章与提示文字）
                        PanStation（煎锅站点：能煎什么、蛋只煎一面、一面多久、徽章与提示文字）
                        GrillStation（炉灶站点：六个烤位在哪、一面多久、该翻的那件、提示文字）
                        DishStation（砧板摆盘：哪些菜搬到砧板、什么能打底、下一层、做成哪道、做几份）
                        StationBooks（四个站点旁的食谱书页：厨锅、砧板摆盘 + 切、煎锅、炉灶；服务端放料挑写法、凑份数）
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
    HandsOn/            Hands-On Delight 规则内核的移植：搅锅评星、批量烹饪、刀口、煎锅 / 灶台两面、摆盘（MIT）
  Menus/                dolorContainer 的界面模型（两端各建一份）：CookingPot（厨锅）
Api/
  LegacyModAttr.py      对外联动契约 v1（linkage.md 的三个函数，显式白名单）
Server/                 服务端
  ModServer.py          导入全部玩法模块；30 个引擎事件各只挂一次 @Listen，转给 EventRegistry
  EventRegistry.py      registerHandler / dispatch：按方块 / 物品名匹配、优先级、短路、异常隔离
  Helpers/              Engine（引擎入口唯一出处）Player Fx Heat Items Placement BlockItems（方块上的物品：广播 + 清理旧展示实体）
                        PotContainer（厨锅容器格与预览槽的读写：出一份、加份数、装碗转出）
                        BoardDish（砧板摆盘的存档：叠着的层、做好的那叠；经典右键还回、拆板掉落）
  CookingPot Skillet Stove CuttingBoard ItemToBlock Crops BoneMeal RichSoil WildCrops
  SkilletItem           煎锅物品：潜行才放成方块、方块实体里记着放下的那件煎锅（耐久 / 附魔 / 名字）、拆掉原样掉回、打一下只磨损 1 点
  SkilletHand           手持煎锅烹饪：主手煎锅、副手食物，热源旁按住右键煎好一件（SkilletHold 是客户端右键上报的 RPC 端点）
  CropTicks FarmWorld   作物随机刻（照 JE 的生长概率）与它读写世界的那一层；OrganicCompost MushroomColony Straw 同属种植
  HandCooking           每口锅的烹饪计时（HoD PotClock）：FD 原样一份一份煮，或厨师搅着整批煮、按星多送
  HandFrying            煎锅手放的一批（HoD Frying）：先煎贴锅面、等颠锅翻面、两面熟了留在锅里；右键放的照 FD 原样
  HandGrill             炉灶手放的每一件（HoD Grill）：逐件两面分开烤、等翻面、烤好留在灶台上；右键放的照 FD 原样
  CookingPotHost        厨锅接入 dolorContainer：容器类型 + 方块宿主 + 界面数据读数
  FoodBlocks Storage RopeAndNet FoodEffects Livestock Tools DisplayGuard PlayerSession LegacyApi
  KnifeSlicing          刀切蛋糕、用刀拆派 / 蛋糕 / 南瓜掉切片（拆的时候先记切片单、方块真没了才兑现）
  ChestLoot             战利品箱第一次打开时追加 FD 的物品（JE 的 add_loot_table），原版战利品表一个字不动
  CraftReturns          工作台合成后补还无序配方的剩余物（读合成格，照 JE 放回原格 / 进背包）
  Backstabbing          背刺魔咒：玩家从背后打中目标时在 DamageEvent 里加伤害
Client/                 客户端
  ModClient.py          入口：query 变量、指南书界面
  Engine.py             compFactory 等 + unwrap（客户端方块实体数据的 __value__ 解包）
  Endpoints.py          服务端调用的 4 个客户端端点
  BlockEntityRestore.py BlockItems.py（方块上的物品用客户端掉落物渲染）
  Input.py              跳跃键、指南书、对着方块拿原版南瓜派不吃、主手煎锅时右键的按住 / 松开上报
  BlockSparkle.py       闪亮沙拉的闪光：收到 BlockAnimateRandomTickEvent 就放 arris:sparkle 粒子
  CookingPotUi.py       厨锅的 dolor 界面：登记界面模型、导入方块宿主的客户端一半
  Ui/                   GuideBook；CookingPotProxy + CookingPotScreen 是厨锅的旧原生界面（只在 DOLOR_SCREEN 关掉时用）
Compat/
  Jei/                  arrisJei 配方页（未安装则不做任何事）
  Create/               机械动力配方（未安装则不做任何事）
  Diegesis/             场景交互前置（diegesisBp）在场时的亲手做菜站点：ServerBoot / ClientBoot 发现并登记，
                        BoardLogic（服务端）+ BoardView（客户端）= 切菜板站点；
                        PotLogic + PotSync（服务端）+ PotView + PotSpoon（客户端）= 厨锅站点；
                        PanLogic（服务端）+ PanView + PanGesture（客户端）= 煎锅站点；
                        GrillLogic（服务端）+ GrillView（客户端）= 炉灶站点；
                        DishBoard + BoardTools（服务端，砧板站点的摆盘与刀具）、DishCrafts（工作台摆出砧板菜的配方时拦下）；
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
  （容器格里已经是它时才续上）。联机时客户端按自己的食谱表预测 Shift 点击，下游模组只在服务端追加的容器会预测错，以服务端为准。
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
6. 无序配方做出整份方块后返回玻璃瓶；砧板一次做多份时 `DishBoard.give` 按堆叠 1 拆开给；创造栏和背包里的方块物品是平面图标（`item_texture`）。

## 煎锅（对照 JE，FD 1.3.4）

JE 数值（SkilletItem / SkilletBlock / SkilletBlockEntity）：铁档（Tiers.IRON）耐久 250、附魔能力 14、修复材料铁锭；攻击修饰符 5.0 + 2.0 = 7
（加在玩家基础 1 上，实际 8）、攻击速度 4.0 - 3.1 = 0.9、攻击击退 +1；打一下、挖一块磨损 1 点；只有潜行才放成方块；放下去的那件连耐久 / 附魔 / 名字
存在方块实体里（火焰附加缩短方块煎的时间），拆掉由战利品表原样掉出（创造模式不掉）。一件食物煎多久 = `SkilletBlock.getSkilletCookingTime(营火配方 600 刻, 火焰附加)`：
float 运算后 6 秒，火焰附加 I 4 秒、II 起 3 秒（下限 60 刻）。`Shared/Rules/SkilletRules.cookingTicks` 逐位照抄（含 Mth.clamp 的取法，`tests/test_skillet_rules.py`）。

- 物品 JSON（`netease_items_beh/arris_skillet_item.json`）：`custom_item_type: weapon` 才会读 `netease:weapon`（以前没写，攻击 / 附魔能力 / 修复都没生效），
  `max_damage` 250（基岩版"损伤 > 最大耐久才坏"，与小刀、原版基岩工具同一个约定，不再减一）、`enchantment` 14、`level` 2（网易文档：铁砧用铁锭修）、
  `attack_damage` 7（取 JE 的修饰符，按"加在玩家基础 1 上"理解，实际 8，待实机核）、提示改成 JE 的"潜行可放置"。
- 放置：`SkilletItem.OnUseSkilletItem`（`ServerItemUseOnEvent`，优先级 98.5）只有潜行才放，不潜行直接拦下（不让 ItemToBlock 当普通方块物品放，也不取消引擎的 `ret`，
  右键箱子照样开箱）。放置本身仍调 `ItemToBlock.OnPlaceItemAsBlock`；放好后把那件煎锅（`SkilletRules.storeItem`：名字、附加值、耐久、附魔、提示、额外 ID、用户数据，
  元组换列表、py2 的 unicode 换 str）记进方块实体数据 `skilletItem`，方块实体还没建好就先挂在待办里，等 `ServerPlaceBlockEntityEvent` 再写。
- 拆掉：方块的战利品表改成空的（`air_loot.json`），`Skillet.OnSkilletRemove`（`BlockRemoveServerEvent`）调 `SkilletItem.dropStored` 掉出存着的那件；
  创造模式在 `ServerPlayerTryDestroyBlockEvent` 记一笔（`SkilletRules.BreakMarks`，按位置、5 秒过期），方块真没了时认这笔记录不掉煎锅；
  没存过的（/setblock、旧存档）掉一把新的。方块的火焰附加读 `skilletItem`，`Skillet._timerStart` 换成倒计时起点（秒数 + 1）。
- 含水的煎锅（液体层 `GetLiquidBlock` 有水）：放食物提示"被水泡着可没法烹饪啊……"，锅里已有的东西浮出来（JE `cookingTick`）；
  放非食物仍是"这东西可不能被烹饪……"（JE 先查配方，所以泡着水也先报这句；锅里有东西时同样报）。
- 手持烹饪（`SkilletHand`）：基岩版没有"按住使用"的服务端事件，由客户端在主手拿着煎锅时报告右键：`RightClickBeforeClientEvent` 报一次，按住期间 `OnScriptTickClient`
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

1. 主手煎锅副手生牛肉站在营火旁：按住右键 6 秒后副手少 1 个、背包多 1 个熟牛肉；中途松手什么都没变；松手后不按右键不会自己煎；火焰附加 I / II 是 4 / 3 秒；
   `RightClickBeforeClientEvent` / `RightClickReleaseClientEvent` / 每 0.2 秒的上报确实到服务端（手柄、触屏"新交互键"也算，经典触屏的长按可能要另外接 `HoldBeforeClientEvent` / `TapOrHoldReleaseClientEvent`）。
2. 潜行右键方块放出煎锅，不潜行右键不放；放完不会在炉灶边冒"用另一只手拿着原料！"；站在炉灶 / 营火旁右键箱子仍然开箱。
3. 带附魔、磨损过的煎锅放下再拆，掉出来的还是那一把（耐久、附魔、改名都在）；创造模式拆不掉煎锅；爆炸 / 命令拆会掉。
4. 煎锅物品的数值：新煎锅打僵尸一下掉 8 点血（`attack_damage` 7 加玩家基础 1；若掉 7 点就改成 8）；打一下耐久只少 1；铁砧用铁锭能修；附魔台能出火焰附加 / 锋利等；
   3D 手持模型（`attachables/skillet_item.json`）在变成武器类物品后姿势没变。
5. 放下的煎锅：火焰附加 I / II 煎一件 4 / 3 秒；水能不能流进煎锅所在的格（`GetLiquidBlock` 读到水）——能的话放食物提示、锅里的东西浮出来。
6. 打人音效：连点是轻击、隔 1 秒再打是重击。

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
- dolorContainer：`test_dolor_vendor.py`（库文件与编译产物的哈希、界面文件登记、导入闭包；随库装入，不手改）、`test_rpc_caller_id.py`
  （客户端可调的服务端端点只用注入的玩家 ID；随库装入）、`test_cooking_pot_book.py` / `test_cooking_pot_menu.py`（厨锅的食谱书规则与
  界面模型，用库的纯逻辑部分在内存里跑，py2 与 py3 都跑）。
- 场景交互前置包（`diegesisBp/arrisDiegesisScripts/`）的测试也在这里：`dgtest.py`（导入 + 假的引擎端口 FakeWorld）、
  `dgkit.py` / `dgfixtures.py`（内核测试的断言与站点夹具），`test_diegesis_*.py`。`test_architecture.py` 同时守两个包。
- 合成：`test_recipe_rules.py`（配方 JSON 的静态检查、生成的 `CraftReturns` 表是否最新）、`test_recipe_parity.py`（对照 JE 的做法 / 摆法 / 剩余物）、
  `test_crafting_rules.py`（`Shared/Rules/Crafting.py` 和 `Server/CraftReturns.py`，`fakeengine.py` 的假合成格驱动）；背刺：`test_backstabbing.py`。
- 游戏内自检：`Server/Debug/McdkSelfTest.py`（`mcdk_test_run()` / 约 15 秒后 `mcdk_test_collect()`），含切菜板站点用例
  （直接驱动前置包的 Manager，与客户端点击走同一条校验路径；前置没装时跳过）。同目录还有 `McdkDishTest`（砧板摆盘、一桶水揉一叠面团）、
  `McdkBookTest`（食谱书放料）、`McdkPotTest` / `McdkPanTest` / `McdkGrillTest`（三个站点的烹饪）、`McdkCraftTest`（工作台合成：摆格子、
  点结果格、核对剩余物和拦截，要用 mc_input 点）、`McdkBackstabTest`（背刺），调用方法写在各文件头。几个自检别同时跑（共用玩家脚边的位置）。
- 直接用 `python` 跑单个测试文件会在包目录里留下 `.pyc`；用 `tools/run_tests.py`（它设了 `PYTHONDONTWRITEBYTECODE`）。
