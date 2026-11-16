# 农夫乐事脚本架构

行为包脚本根：`bp/arrisFarmersDelightScripts/`（Python 2.7，网易 ModSDK + QuModLibs）。

```
modMain.py              入口：dolorContainer 两端服务 + MOD.Server("Server.ModServer") / MOD.Client("Client.ModClient") + 各联动入口
QuModLibs/              框架（arrisCreate kit 的加固精简版），只读，不改
dolorContainer/         容器界面库：团队自有，由 dolorContainer 仓库的 tools/vendor.py 原样拷入（dolor.lock 记哈希），只读，不改
dolorLayouts.py         布局的绑定表：vendor 时从仓库根 layouts/*.json 编译生成，不手改
Shared/                 双端共用；不导入引擎、QuModLibs、Server、Client —— 离线可测
  Data/                 纯数据表：Cooking  Cutting  CookingPotRecipes  Farming  Food  Blocks  Effects  Mobs  GuideBook
                        Dishes（砧板摆盘的菜谱，tools/gen_dishes.py 从合成配方生成）
  Rules/                纯规则：CookingPot（配方匹配 / 出料结算） CropGrowth（催熟阶段表） Placement（朝向 / 放置位置） Ticks（错峰 / 概率）
                        CookingPotBook（厨锅食谱书：容器格号、搜索、详情格、补食材的计划）
                        CuttingStation（切菜板站点：FD 配方 -> 刀口计划、工具判定、整批产物）
                        PotStation（厨锅站点：份数、放料、按配方把料摆进几格、取回、徽章与提示文字）
                        PanStation（煎锅站点：能煎什么、蛋只煎一面、一面多久、徽章与提示文字）
                        GrillStation（炉灶站点：六个烤位在哪、一面多久、该翻的那件、提示文字）
                        DishStation（砧板摆盘：哪些菜搬到砧板、什么能打底、下一层、做成哪道、做几份）
                        BlockDisplay（砧板 / 煎锅 / 炉灶上的物品怎么摆） ItemPose（客户端掉落物姿态换算，实机标定）
    HandsOn/            Hands-On Delight 规则内核的移植：搅锅评星、批量烹饪、刀口、煎锅 / 灶台两面、摆盘（MIT）
  Menus/                dolorContainer 的界面模型（两端各建一份）：CookingPot（厨锅）
Api/
  LegacyModAttr.py      对外联动契约 v1（linkage.md 的三个函数，显式白名单）
Server/                 服务端
  ModServer.py          导入全部玩法模块；26 个引擎事件各只挂一次 @Listen，转给 EventRegistry
  EventRegistry.py      registerHandler / dispatch：按方块 / 物品名匹配、优先级、短路、异常隔离
  Helpers/              Engine（引擎入口唯一出处）Player Fx Heat Items Placement BlockItems（方块上的物品：广播 + 清理旧展示实体）
                        PotContainer（厨锅容器格与预览槽的读写：出一份、加份数、装碗转出）
                        BoardDish（砧板摆盘的存档：叠着的层、做好的那叠；经典右键还回、拆板掉落）
  CookingPot Skillet Stove CuttingBoard ItemToBlock Crops BoneMeal RichSoil WildCrops
  HandCooking           每口锅的烹饪计时（HoD PotClock）：FD 原样一份一份煮，或厨师搅着整批煮、按星多送
  HandFrying            煎锅手放的一批（HoD Frying）：先煎贴锅面、等颠锅翻面、两面熟了留在锅里；右键放的照 FD 原样
  HandGrill             炉灶手放的每一件（HoD Grill）：逐件两面分开烤、等翻面、烤好留在灶台上；右键放的照 FD 原样
  CookingPotHost        厨锅接入 dolorContainer：容器类型 + 方块宿主 + 界面数据读数
  FoodBlocks Storage RopeAndNet FoodEffects Livestock Tools DisplayGuard PlayerSession LegacyApi
Client/                 客户端
  ModClient.py          入口：query 变量、指南书界面
  Engine.py             compFactory 等 + unwrap（客户端方块实体数据的 __value__ 解包）
  Endpoints.py          服务端调用的 4 个客户端端点
  BlockEntityRestore.py BlockItems.py（方块上的物品用客户端掉落物渲染） Input.py
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
                        DishBoard + BoardTools（服务端，砧板站点的摆盘与刀具）、DishCrafts（工作台不再出砧板菜）；
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

## 引擎坑（踩过的）

- 方块实体数据（`GetBlockEntityData`）是引擎对象，不是 dict：没有 `.get()`，缺键读出来是 `None`，用 `data["k"] or 缺省值`。
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
- QuMod 的 RPC 端点按裸函数名注册：服务端端点一律 `@AllowCall` + `@InjectHttpPlayerId`，玩家身份只认注入的，坐标、维度、背包下标都要校验。

## 新增内容的清单

新食物 / 方块 / 配方需要同时改：
1. `Shared/Data/` 对应的表（厨锅配方、砧板配方、可烹饪食物、作物阶段……）；
2. `bp/netease_items_beh/`、`bp/netease_blocks/`、`bp/recipes/`、`bp/loot_tables/` 的定义；
3. `rp/` 的贴图、模型、`netease_items_res`、`blocks.json`。

Python 只管运行时行为，物品 / 方块是否存在由 JSON 决定。

## 测试

```
py -3 tools/run_tests.py           跑全部（按每个文件第 2 行的 "# runner: py2|py3|both" 选解释器）
py -3 tools/run_tests.py cooking   只跑文件名含 cooking 的
```

`tests/` 只测不依赖引擎的部分（`Shared/`、`Api/`、`Server/EventRegistry.py`）和静态结构；
与引擎交互的部分用 Strata 的 `script_inspect` / `script_run`（沙箱加载、按剧本驱动事件）和游戏内实测。

- `fdtest.py`：农夫乐事包的导入与用例收集；`test_handson_*.py` 是 HoD 规则内核的测试。
- dolorContainer：`test_dolor_vendor.py`（库文件与编译产物的哈希、界面文件登记、导入闭包；随库装入，不手改）、`test_rpc_caller_id.py`
  （客户端可调的服务端端点只用注入的玩家 ID；随库装入）、`test_cooking_pot_book.py` / `test_cooking_pot_menu.py`（厨锅的食谱书规则与
  界面模型，用库的纯逻辑部分在内存里跑，py2 与 py3 都跑）。
- 场景交互前置包（`diegesisBp/arrisDiegesisScripts/`）的测试也在这里：`dgtest.py`（导入 + 假的引擎端口 FakeWorld）、
  `dgkit.py` / `dgfixtures.py`（内核测试的断言与站点夹具），`test_diegesis_*.py`。`test_architecture.py` 同时守两个包。
- 游戏内自检：`Server/Debug/McdkSelfTest.py`（`mcdk_test_run()` / 约 15 秒后 `mcdk_test_collect()`），含切菜板站点用例
  （直接驱动前置包的 Manager，与客户端点击走同一条校验路径；前置没装时跳过）。
- 直接用 `python` 跑单个测试文件会在包目录里留下 `.pyc`；用 `tools/run_tests.py`（它设了 `PYTHONDONTWRITEBYTECODE`）。
