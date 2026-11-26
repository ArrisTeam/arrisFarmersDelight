# AGENTS.md：棱花 Arris · 网易版农夫乐事（arrisFarmersDelight）

给在这个仓库里干活的编码代理和贡献者看的。细节在 `docs/`，这里只写开工前必须知道的事。

## 1. 这是什么

- 把 Java 版模组 **Farmer's Delight**（1.3.4 / MC 1.20.1）移植到**网易版我的世界基岩版**的 AddOn：行为包 `bp/` + 资源包 `rp/`，用 MC Studio 或 MCDK 导入、启动。
- 脚本跑在网易引擎内嵌的 **Python 2.7** 上（不是基岩版的 Script API）。服务端和客户端是两套系统，经 QuModLibs 的 RPC（`@AllowCall` / `Call`）通信。
- 内容命名空间是 `arris:`。移植的基准是 JE 的行为：改玩法前先对 JE 源码，哪里有意不一样、哪里做不到，逐条记在 `docs/ARCHITECTURE.md`「和 JE 的出入」。JE 没有的内容不往里加。
- 可选的联动（都是没装就不生效、不报错）：沉浸式交互前置（arrisDiegesis，亲手做菜的站点，对应 JE 的 Hands-On Delight）、arrisJei、机械动力（arrisCreate）、成就系统（arrisAdvancements）。**没装前置包时这就是原样的农夫乐事**，站点的代码一行都不跑。

## 2. 运行、测试、发版

- 进游戏：MC Studio / MCDK 打包 `bp/` + `rp/` 启动。新的方块、物品、附魔、标签文件、着色器 / 材质 / 模型 / 贴图 / 粒子 / 界面 JSON 要完整重启；配方 JSON 重进世界；只改 Python 可以重载脚本。
- 离线测试：`py -3 tools/run_tests.py`（可以带**一个**文件名过滤词，如 `py -3 tools/run_tests.py item_tags`）。每个 `tests/test_*.py` 第 2 行写 `# runner: py2|py3|both`，py2 是和引擎同版本的 Python 2.7，纯规则的测试写 `both`。不要直接运行测试文件（会在包里留下 `.pyc`）。
  - 需要前置包源码的测试找旁边的 `../arrisDiegesis`（或环境变量 `FD_PREREQ_DIR`），找不到就跳过；对原版资源的检查找本机的游戏目录（`FD_GAME_DIR`），找不到也跳过。
  - 网易机审的代码检查是 Python 2 的 pylint 1.9.5，已经在全量里（`tests/test_review_lint.py`，依赖见 `tools/requirements-pylint-py2.txt`）。
- 离线测试全绿不等于能用：引擎的标准库是删减过的、很多接口只在自己那一端的线程里答得出。动了和引擎打交道的代码，要进游戏跑对应的自检（`Server/Debug/Mcdk*Test.py`、`Client/Debug/Mcdk*Test.py`，每个文件开头写着怎么调），并看错误日志。
- 生成的文件别手改，改源头再跑生成器（测试会核对是不是最新的）：

  | 改了什么 | 跑什么 |
  | --- | --- |
  | `bp/recipes/**` | `py -3 tools/gen_crafts.py`、`py -3 tools/gen_dishes.py` |
  | `Shared/Data/Tags.py`、厨锅配方的 `Slots`、`CuttingTagDict` | `py -3 tools/gen_tags.py`（写 `bp/netease_tags/` 和 `docs/TAGS.md`） |
  | 榻榻米贴图 | `py -3 tools/gen_tatami.py` |
  | 游戏更新后原版交易表变了 | `py -3 tools/gen_vanilla_overrides.py` |
- 发版：改版本号用 `py -3 tools/version.py bump --new-uuid`（每次发版都换 UUID、升版本号），提交后打 `vX.Y.Z` 的 tag，`.github/workflows/release.yml` 核对、跑测试、出包。打 tag 和推送由仓库所有者来做。

## 3. 目录

脚本根是 `bp/arrisFarmersDelightScripts/`（下面写作 `S/`）：

| 路径 | 是什么 |
| --- | --- |
| `S/modMain.py` | 入口：登记两端的模块 |
| `S/Shared/Data/` | 玩法数据表（配方、可煎烤的东西、热源、作物、标签词表……） |
| `S/Shared/Rules/` | 纯规则，不碰引擎，离线可测 |
| `S/Server/` | 服务端。`ModServer.py` 是唯一挂引擎事件监听的地方，分发到 `EventRegistry`；功能模块用 `@registerHandler(事件, match=…, priority=…)` |
| `S/Client/` | 客户端：服务端调的端点、方块实体的显示、输入、界面 |
| `S/Api/` | 对外接口：`LegacyModAttr.py`（旧联动契约）、`ExtensionApi/`（新联动接口） |
| `S/Compat/` | 联动：`Diegesis/`（前置包的站点）、`Jei/`、`Create/`、`Advancements/` |
| `S/QuModLibs/`、`S/dolorContainer/`、`S/dolorLayouts.py` | 拷进来的第三方库，**只读**；要更新就整份重新拷 |
| `bp/recipes/`、`bp/netease_tags/`、`bp/netease_blocks/`、`bp/netease_items_beh/`、`bp/loot_tables/`、`bp/trading/` | 数据驱动的内容 |
| `S/Server/Debug/`、`S/Client/Debug/` | 游戏内自检（`Mcdk*Test.py`），不进发布包，正式模块不许导入它们 |
| `tests/`、`tools/`、`docs/` | 测试、生成器和发版工具、文档 |

文档：`docs/ARCHITECTURE.md`（每个模块管什么、事件处理的先后、站点怎么接、和 JE 的出入、踩过的引擎坑；很长，按标题找）、`docs/EXTENSION-API.md` / `RECIPE-JSON.md` / `COMPATIBILITY.md` / `API-CHANGELOG.md`（新联动接口）、`docs/TAGS.md`（标签词表和 JE 的对照）、`linkage.md`（旧联动契约）、`README.md`（给玩家和下游开发者的介绍）。

## 4. 分层和硬规矩（`tests/test_architecture.py` 守着）

- `Shared` 不导入引擎、框架和两端；`Server` 和 `Client` 互不导入，也不导入 `Compat`；入口模块和联动的步骤表不在顶层导入站点模块。
- 不许 `import sys`、`__import__`、`namedtuple`、`eval` / `exec`、`pickle.loads`、星号导入；相对导入必须解析得到。
- 引擎的 Python 标准库是删减过的（没有 `numbers`、`fractions`、`decimal`、`unicodedata`……），能用的白名单在 `tests/test_architecture.py`；白名单外的模块先在游戏里 import 试过再用。
- 服务端的 `@AllowCall` 端点必须同时 `@InjectHttpPlayerId`；客户端传来的玩家 ID、坐标、维度、格号一律不信。
- 文件不超过 250 行（数据表除外），函数不超过 120 行。
- Python 2.7 语法且能被 Python 3 解析：不用 f-string 和类型注解，`print("…")` 只给一个参数，文件头 `# -*- coding: utf-8 -*-`。新模块用 PascalCase 文件名，docstring 第一行写 `模块名 - 说明（端）`。

## 5. 对外的东西（改之前想清楚谁在用）

- **旧联动契约** `S/Api/LegacyModAttr.py`：三个函数 + 白名单里的 25 张表，下游的乐事附属包拿的是表的活引用。只加不改，`tests/test_legacy_modattr_contract.py` 必须是绿的，新东西不往这里加。
- **新联动接口** `S/Api/ExtensionApi/`：农夫乐事加载完广播 ready 事件，交出 `ext`（配方的登记 / 查询 / 覆盖 / 删除、刀 / 热源 / 炉灶 / 堆肥的登记口、标签查询）；别的行为包还可以放 `farmersdelight_recipes/**.json`（JE 农夫乐事写法的配方）。文档 `docs/EXTENSION-API.md`、`RECIPE-JSON.md`、`COMPATIBILITY.md`、`API-CHANGELOG.md`；能力名只在实现、测试、文档都齐了才加（`tests/test_extension_docs.py` 核对文档和代码）。
- **标签**（`bp/netease_tags/`，词表 `S/Shared/Data/Tags.py`，说明 `docs/TAGS.md`）：`common:` 的名字照 JE 1.21 的 `c:` 约定取最后一段，嵌套照 JE 用 `#` 引用；农夫乐事自己的用 JE 原名 `farmersdelight:`。凡是"按标签认"的判断都走 `S/Shared/Rules/ItemTags.py`。
- **配方存在契约表里**：厨锅的一行可以带 `Id`、`Slots`、`Disabled`（墓碑）；行只打墓碑、不删除，行号就是身份。表由 `Server/TableSync.py` 同步给客户端。
- 存档里的东西（方块实体数据的键、方块状态名、物品名）改名等于丢档，别改。

## 6. 容易踩的坑

- **方块实体数据不是字典**：不能 `.get()`，缺的键读出 `None`；读到的是缓存，**只有赋值才落盘**，改了嵌套的字典 / 列表要整个赋回去；键必须是 `str`。`/setblock`、结构放出来的方块不走放置事件，读的地方要给缺省值。
- 事件取消的字段不一样：`ServerBlockUseEvent` 用 `cancel`，`ServerItemUseOnEvent` 用 `ret`。点一下会同时来 ItemUseOn 和 BlockUse，按住右键每刻都来：交互的处理函数都过 `Helpers.Player.SetPlayerUsedCD`（0.2 秒），先处理的占住。
- 物品在数据表里是 `(物品名, aux)`，运行时的物品字典用 `newItemName` / `newAuxValue` / `count`。创造模式别自己扣数量，用 `SetNotCreateItem`；给物品用 `GiveOrDropItem`（背包满了不丢东西）。
- **单机时两端共用一份 `Shared` 模块**，而有些引擎接口跨线程调会静默返回 `None`：装在 `Shared` 里的引擎"口"要按端各存一个、挨个问、第一个不是 `None` 的算数，缓存只记真问到的答案。实机核对时先在客户端线程问、再在服务端线程问。
- 显示名在登记的时候问不到（自定义物品那时还只有语言键），显示的时候再问。联机时两端问到的名字可能不一样：凡是"客户端选了哪一个"都按身份（行号、ID）传，不按过滤后的序号。
- **不整文件覆盖原版实体**：给原版动物加喂食 / 驯服物品走 `Server/AnimalFood.py`（读生效的实体定义，`AddActorComponent` 动态加组件，和别的模组的改动合并）。
- 有序合成配方的容器写在 `result` 数组里；无序配方的由 `Server/CraftReturns.py` 补还，一次合成最多还一次、认不出配方就不还——动这条线先想清楚会不会刷物品。
- 完整不透明的方块才写吸光 15，其余写 0（网易缺省是不透明）；`tests/test_block_light.py` 里有表。
- 给玩家看的字放 `rp/texts/*.lang`，有官方中文翻译的照 JE 的翻译；标签写 `%` 要写成 `%%`。
- `arris:item_display` / `arris:corpse_display` 这两个展示实体由 `Server/DisplayGuard.py` 护着，别拆。

## 7. 提交

- 提交信息 `type: 中文说明`（feat / fix / refactor / perf / test / docs / chore），一个提交一件事，写清改了什么、为什么。
- 提交前全量测试要绿；暂存按文件名来，不要 `git add -A`（工作区里有本机的配置文件）。
- 仓库里不放交接记录、过程文档：长期有效的事实写进 `docs/ARCHITECTURE.md` 或本文件。
- `studio.json`、`work.mcscfg`、`world_*` 和所有点开头的目录是本机文件，不入库。
