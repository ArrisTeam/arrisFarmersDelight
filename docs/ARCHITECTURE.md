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
                        FoodColors  BrothColors（按贴图算的颜色：FoodColors 是厨锅汤色用的图标加权平均；BrothColors 里有汤色、碎料色、倒进锅里的液体色，和砧板碎屑、煎锅 / 炉灶上东西朝上那面的熟色用的主色 MainColors，tools/gen_food_colors.py / gen_broth_colors.py 生成）
                        Fishes（JE 的物品标签 minecraft:fishes：煎着的东西朝上那面"肉和鱼"多带一点焦色的鱼那一半）
                        BiomeWater（各群系的水色，tools/gen_biome_water.py 按原版资源包每个群系的 water_appearance 生成；厨锅里的清水取它）
                        PotSunk（下锅就沉的料：倒的、打的、化的）  PotPieceTraits（配料切成碎料时算谷物 / 意面 / 肉，还是煮完拣出来）
                        HandsOnConfig（HoD 的配置表：四个站点的开关、工作台合成、搅拌、食谱书、三种烹饪倍率，缺省同 JE；整合包作者改它，不经联动契约；读法在 Rules/HandsOnOptions）
                        Tips（服务端提示说的每一句：(语言文件的键, 中文)，客户端按玩家的语言查，见「砧板和站点的几处补齐」）
  Rules/                纯规则：CookingPot（厨锅配方匹配 / 出料结算，公共函数都在这里） CropGrowth（催熟阶段表） Placement（朝向 / 放置位置；`directionOfAux` 是读方块 aux 的唯一一处） Ticks（错峰 / 概率）
                        PotSlots（厨锅配方的格子：选项的写法、逐格配对、种类的各种摆法、展开成写法）  PotRecipeTable（厨锅配方表的索引和记着的答案，只有 CookingPot 用）
                        RecipeJson（JE 写法的配方 JSON 读成规整的配方：厨锅、砧板、营火烹饪；新联动接口和行为包配方 JSON 共用）
                        CookingPotBook（厨锅经典界面的食谱：容器格号、搜索与食谱格（按搜索词记着，表变了重算）、详情格与写法轮换、补食材的计划与试写法的先后）
                        CuttingStation（切菜板站点：FD 配方 -> 刀口计划、工具判定、整批产物）
                        PotStation（厨锅站点：槽位声明、什么能放、什么用得上、盛这道菜的容器）  PotLayout（按哪道菜摆料、照书放料的计划）
                        PotLookState（厨锅"看上去是什么样"的广播怎么读）  PotModelMath（方块朝向、勺子骨骼的位移和欧拉角）
                        PotPiecesLook（汤里的碎料交给着色器的数：配料槽、出现 / 缩走的钟）  PotItem（拆下来的锅带着菜）
                        PotSupport（厨锅的支架：没有 / 托盘 / 吊把手，放下时点的是不是方块的下面、两个旗读成哪种、切换的声音）
                        PotWater（厨锅里清水的颜色：锅所在区块里 5x5 列的群系水色取平均，群系名由客户端 Compat/Diegesis/PotBiome 问来）
                        PanStation（煎锅站点：能煎什么、哪些只煎一面 / 哪些是蛋、一面多久、徽章与提示文字）  PanLookState（煎锅"看上去是什么样"的广播怎么读）
                        GrillStation（炉灶站点：能放什么、一面多久、这一下右键开不开）  StoveCover（炉灶上面盖没盖东西：锅、煎锅、砧板、别的方块）
                        GrillBlocks（灶方块 = 点着的 `StoveList` + 熄着的孪生方块 `arris:stove_extinguish`：isLit / isGrill / twinOf、前置包登记站点用的活容器 `GRILL_BLOCKS`（只读，`in`、长度、下标、遍历都行：原来的 `STOVE_BLOCKS` 就是 `StoveList` 这个列表）、
                        熄着时 FD 的件怎么冷却 `cooledTimer`、什么点得着 / 灭得了炉灶 `useOf`）
                        StoveFacing（炉灶的朝向：方块的 aux -> 站点朝向，炉灶自己的坐标 / 姿态 -> 世界，六件跟着炉灶转）
                        StoveLookState（炉灶"看上去是什么样"：广播和方块实体里存的那份怎么读）  EggLook（煎锅 / 炉灶里的蛋从生到熟的三档专用图标）
                        FryingTint（煎锅 / 炉灶上一件朝上那面的熟色：JE 的 fryingTint 用哪两张主色、哪些算肉和鱼，叠层粒子的颜色和不透明度）
                        TopOverlay（叠在一件平躺的掉落物朝上那面上的图标粒子摆在哪、SetRot 转多少、多大，掉落物停稳了没有）
                        DishStation（砧板摆盘：哪些菜搬到砧板、什么能打底、下一层、做成哪道、做几份）
                        StationBooks（四个站点旁的食谱书页：厨锅、砧板摆盘 + 切、煎锅、炉灶；服务端放料挑写法、凑份数；页脚的秒数带着配置的倍率）
                        HandsOnOptions（HoD 配置表的读法：JE 的缺省、read / readTime 的兜法、倍率夹进 0.1..10、派生规则、scaled；每次现读表，两端共用；没联动时说 HoD 不在）
                        HandsOnMode（沉浸式交互前置联动了没有：每端一个运行模式 pending / linked / outdated / standalone，linked() 问整个进程，whenDecided；只有 Compat/Diegesis/Presence 往里写）
                        SyncTables  TableWire  TableDiff  TableMerge（下游在服务端追加的表怎么发给客户端：登记哪些表 / 编码 / 算差异 / 并表，见"联动契约与客户端的表"）
                        TipWire（服务端提示发给那个玩家的客户端的写法：哪一句、填什么）
                        FoodEffects（吃喝之后的追加结算：牛奶瓶 / 热可可 / 西瓜汁 / 冰棒 / 原版汤；只返回动作，Server/FoodEffects 执行）
                        BlockDisplay（砧板 / 煎锅 / 炉灶上的物品怎么摆） ItemPose（客户端掉落物姿态换算，实机标定）
                        BoardSupport（砧板下面撑不撑得住：JE 的 canSurvive，下面那格的顶面要盖住正中 2x2 像素——按引擎给的碰撞盒判，包围盒说不准的按名字）
                        MobLoot（刀杀死生物的额外掉落、洋葱掉落的概率结算） Slicing（刀切派 / 蛋糕 / 南瓜：剩几片、切片单） Eating（吃一份食物的饥饿 / 饱和度）
                        Livestock（马饲料 / 狗粮喂给谁、有什么效果） ChestLoot（战利品箱追加物品的掷骰）
                        AnimalFood（原版六种动物认本包的食物：生效的实体定义 -> 每个组件每个出处追加以后的 JSON、换组的事件、定义栈折成现在该下发哪几个）
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
                        StoveFlame（点着的炉灶自己的火：火口的火星 / 烟 / 噼啪声、灶上每件东西冒烟的概率和位置，JE 的 animateTick / particleTick）
                        TatamiMat（长榻榻米垫两格怎么摆、另一半在哪、脚下没了方块） RopeFence（绳栅栏门的开关、朝向、声音）
                        TatamiPair（榻榻米方块两两配对：放下时和谁配、另一半没了拆开；方块态 arris:tatami_facing / arris:paired 的取值）
                        SoundMix（JE 的音量 / 音调换成交给引擎的数：定义里自带音量 / 音调的声音要把那份除掉）
                        ItemDrops（东西从方块里掉出来 / 弹出去的位置和初速，照 JE 的 Containers.dropItemStack / ItemUtils.spawnItemEntity；砧板切出来、煎锅煎好的往方块侧面弹：boardPop / panPop）
    HandsOn/            Hands-On Delight 规则内核的移植：搅锅评星、批量烹饪、刀口、煎锅 / 灶台两面、摆盘（MIT）；
                        厨锅的表现也在这里（纯计算，Pot 开头的那些）：汤面（水位、汤色、沸腾）、勺子的手感、漂着的料、碎料、
                        出锅的收尾、声音日程、徽章、盛汤和倒 / 打 / 抖的手部动作；
                        砧板的表现也在这里（Board 开头的）：板上东西的动作（落下 / 拿走 / 融掉 / 弹出）、刀口、手倒液体和磕蛋，
                        以及做成一道菜之前的十种收尾（BoardFinishKit 常量 + Plan，BoardFinishGroup / BoardFinishPlace 各种怎么演，BoardFinish.plan 入口）
  Menus/                dolorContainer 的界面模型（两端各建一份）：CookingPot（厨锅），PotRecipes（厨锅界面的食谱格：算出的内容、触屏抬起才选中的手势），
                        PotFill（厨锅界面的"添加食材"：挑写法、找来源、整体搬）
Api/
  LegacyModAttr.py      对外联动契约 v1（linkage.md 的三个函数，显式白名单）
  ExtensionApi/         新联动接口（照机械动力的 ready 事件 + 门面 ext；对外文档 docs/EXTENSION-API.md，内部见「新联动接口与配方的登记」）：
                        Events（命名空间 arrisFarmersDelight、系统名 ExtensionApi、两端的 ready 事件、接口版本、两端的能力名）、
                        Version（主包版本号 HOST_VERSION，tools/version.py 和 manifest 一起改）、Facade（ext：每端一个）、
                        Ready（每端广播一次，别的模组的处理函数出错不连累农夫乐事）；广播用的系统在 Server/ExtensionSystem、Client/ExtensionSystem；
                        Recipes（ext.recipes）+ RecipeBuilder（一句一句写成 JE 写法的 JSON）+ RecipeTables（配方存进那几张契约表、覆盖、删、写成 JE 写法）+
                        RecipeIds（配方 ID 的规矩、旧接口追加的配方的 legacy: 派生 ID）+ RecipeFiles（行为包里 farmersdelight_recipes/ 的文件定 ID、登记）；
                        Registries（registerKnife / HeatSource / Stove / Compostable 和 ext.tags）
Server/                 服务端
  ModServer.py          导入全部玩法模块；37 个引擎事件各只挂一次 @Listen，转给 EventRegistry
  ExtensionReady        LoadServerAddonScriptsAfter：发新联动接口的服务端 ready 事件（ExtensionSystem 是广播用的系统，要广播时才注册），
                        再读全部行为包里的 farmersdelight_recipes/（Helpers/PackJson 跨包读文件），最后调一次 onRecipesChanged 的处理函数
  EventRegistry.py      registerHandler / dispatch：按方块 / 物品名匹配、优先级、短路、异常隔离
  Helpers/              Engine（引擎入口唯一出处）Player Fx Heat Items Placement BlockItems（方块上的物品：广播 + 清理旧展示实体）
                        Drops（东西从方块里掉出来 / 弹出去：位置照 JE 的 dropItemStack，初速经 SetMotion 给；PopFromBoard / PopFromPan 读方块朝向往侧面弹）
                        PotContainer（厨锅容器格与预览槽的读写：出一份、加份数、装碗转出）
                        BoardDish（砧板摆盘的存档：叠着的层、做好的那叠；经典右键还回、拆板掉落）
                        PackJson（读全部行为包里某个目录下的 JSON：引擎内部的 server_resource，经 traceback.sys.modules 取，只在这里碰它；2026-11-26 游戏里核过）
  CookingPot Skillet Stove CuttingBoard ItemToBlock Crops BoneMeal RichSoil WildCrops
  SkilletItem           煎锅物品：潜行才放成方块、方块实体里记着放下的那件煎锅（耐久 / 附魔 / 名字）、拆掉原样掉回、打一下只磨损 1 点
  SkilletHand           手持煎锅烹饪：一只手煎锅、另一只手原料，热源旁按住右键煎好一件（SkilletHold 是客户端右键上报的 RPC 端点）
  HeatConduct           下面是漏斗的厨锅 / 煎锅：热源在漏斗再下面一格，那一格变了没有邻居事件，每 0.5 秒自己重算、变了交给原来的邻居事件处理函数（热源规则在 Helpers/Heat，见"厨锅 / 煎锅下面的热源"）
  CropTicks FarmWorld   作物随机刻（照 JE 的生长概率）与它读写世界的那一层；OrganicCompost MushroomColony Straw 同属种植
  HandCooking           每口锅的烹饪计时（HoD PotClock）：FD 原样一份一份煮，或厨师搅着整批煮、按星多送；料换了菜进度从头来（Shared/Rules/PotRecipeMemory），有人开着经典界面也按 FD 原样
  PotLook               厨锅的世界外观广播：锅里有什么、勺子在哪、煮到哪，发给 32 格内的人，静态部分写进方块实体数据
  PotServe              盛菜：取一份、记"做过几份"、给经验；主手拿着容器右键直接盛
  HandFrying            煎锅手放的一批（HoD Frying）：先煎贴锅面、等颠锅翻面、两面熟了留在锅里；右键放的照 FD 原样
  HandGrill             炉灶手放的每一件（HoD Grill）：逐件两面分开烤、等翻面、烤好留在灶台上；右键放的照 FD 原样
  StoveSwap StoveFire   炉灶点火 / 灭火：点着的是 `arris:stove`、熄着的是 `arris:stove_extinguish`，换方块名等于换方块实体，StoveSwap 换之前拍炉灶自己的键（六个烤位、
                        handGrill）和朝向的快照、换完写回（事件先后两种都兜；5 秒还写不上把东西丢在地上；旧方块的移除事件用 claims 挡住；换完一秒里重发世界外观），
                        StoveFire 是 `ServerItemUseOnEvent` 优先级 11 的处理：打火石、火焰弹点着，铲子、水桶熄灭（JE 的 AbstractStoveBlock.use），用上了就认领，不再放食物
  PanLook StoveLook     煎锅 / 炉灶的世界外观广播：东西、两面烤到哪、翻面 / 取走 / 放不进 / 烤好的一次性事件，发给 32 格内的人（站点开不开着都一样），
                        新走进 32 格的人单发一份当前的、样子没变时每 5 秒再单发一份（广播丢了就这么补）、开站那一刻单发给开站的人
                        （Helpers/LookWatch：玩家位置快照 + 每口锅 / 灶一份"已经收到当前样子的人和时刻"）
  CookingPotHost        厨锅接入 dolorContainer：容器类型 + 方块宿主 + 界面数据读数；宿主的 onViewers 告诉烹饪谁开着界面
  CookingPotItem        厨锅拆下来带着锅里的菜、放回去菜还在（JE 的 copy_meal；规则在 Shared/Rules/PotItem.py）
  PotSupport            厨锅的支架：挂在天花板下面放下就是吊把手（放置前事件记点的面），潜行空手右键在吊把手和托盘 / 没有之间切（见"厨锅的支架"）
  FoodBlocks Storage RopeAndNet FoodEffects Livestock Tools DisplayGuard PlayerSession LegacyApi
  AnimalFood            原版猫 / 鸡 / 猪 / 兔子 / 鹦鹉 / 狼认本包的食物：读生效的实体定义、实体出现和换组以后晚一拍 AddActorComponent（见"战利品、刀与喂养"）
  TableSync             下游在服务端追加的表发给客户端：玩家进服发一次累计的差异，之后每 5 秒看表变没变、补发（客户端的站点表现读的是客户端那一份表）
  Basket                篮子吸掉落物（事件 + 每 0.25 秒轮询，由 Storage 导入来登记）；RopeAndNet 另管卷绳子、安全网弹跳，Stove 另管站上去的烫伤
  KnifeSlicing          刀切蛋糕、用刀拆派 / 蛋糕 / 南瓜掉切片（拆的时候先记切片单、方块真没了才兑现）
  ChestLoot             战利品箱第一次打开时追加 FD 的物品（JE 的 add_loot_table），原版战利品表一个字不动
  CraftReturns          工作台合成后补还无序配方的剩余物（读合成格，照 JE 放回原格 / 进背包）
  Backstabbing          背刺魔咒：玩家从背后打中目标时在 DamageEvent 里加伤害
  TatamiMats            长榻榻米垫两格一起放、一起拆（只掉一个）、长短垫脚下没了方块就碎；RopeFences  绳栅栏门右键开关
  TatamiPairs           榻榻米方块两两配对：放下（EntityPlaceBlockAfterServerEvent）时写两块的方块态，另一半没了拆开；样子全在方块 JSON 的 permutations 里
Client/                 客户端
  ModClient.py          入口：query 变量、指南书界面
  ExtensionReady.py     LoadClientAddonScriptsAfter：发新联动接口的客户端 ready 事件（ExtensionSystem.py 是广播用的系统）
  Engine.py             compFactory 等 + unwrap（客户端方块实体数据的 __value__ 解包）
  Endpoints.py          服务端调用的 6 个客户端端点：放声音（可带音量 / 音调）、砧板切一件的碎屑、粒子、方块实体 molang、挥手、提示（OnTip：按玩家的语言查出那一句再弹）
  TableSync.py          客户端端点 OnTableSync：把服务端发来的"下游追加的表内容"并进本端自己的表，重算依赖它的缓存
  Texts.py              站点界面上我们自己写的字按玩家的语言给：of(键, 缺省中文) / fill(键, 缺省, 值)，查 rp/texts 的语言文件，见「砧板和站点的几处补齐」
  BlockEntityRestore.py BlockItems.py（方块上的物品用客户端掉落物渲染）
  Input.py              跳跃键、指南书、对着方块拿原版南瓜派不吃、主手煎锅时右键的按住 / 松开上报
  BlockSparkle.py       闪亮沙拉的闪光：收到 BlockAnimateRandomTickEvent 就放 arris:sparkle 粒子
  StoveFlame.py         点着的炉灶自己的火：BlockAnimateRandomTickEvent 在火口放烟和火、1/10 的概率噼啪；ModBlockEntityTickClientEvent 让灶上每件东西冒烟（炉灶站点在场时不放）
  CookingPotUi.py       厨锅的 dolor 界面：登记界面模型、导入方块宿主的客户端一半和食谱格的控件（按行回收的 scroll_grid）
  Ui/                   GuideBook；CookingPotProxy + CookingPotScreen 是厨锅的旧原生界面（只在 DOLOR_SCREEN 关掉时用）
Compat/
  Jei/                  arrisJei 配方页（未安装则不做任何事）；BoardAssembly = 联动着、砧板站点开着时多出的"砧板摆盘"分类，并把被拦的工作台配方藏起来；
                        CookPages = 煎锅、炉灶两个分类共用的分页（StationBooks.cookGroups：三种蛋一页）和配方页；厨锅、砧板的配方页轮换标签格的成员
  Create/               机械动力配方（未安装则不做任何事）
  Diegesis/             沉浸式交互前置（diegesisBp）在场时的亲手做菜站点：ServerBoot / ClientBoot 只挂 Presence（找前置包的接口、定本端的运行模式、跑步骤表，Steps 是执行器），
                        ServerSteps / ClientSteps 是步骤表（只放数据）、每个站点一步，步骤的实现是 BoardServerLink / PotServerLink / PanServerLink / GrillServerLink 和
                        BoardClientLink / PotClientLink / PanClientLink / GrillClientLink（调站点的 register，登记上了再开连带的东西）；站点模块在步骤里才导入，见「联动（沉浸式交互前置）」，
                        BoardLogic + BoardSlots / BoardGive / BoardChop / BoardAssemble / BoardTools / BoardEmit（服务端）+ BoardView + BoardDraw /
                        BoardDrawEvents / BoardThing / BoardFinishPlay（做成一道菜之前的十种收尾）/ BoardHandDraw（液体层倒、蛋层磕的那只手）/ BoardCutter + BoardMarkLine（刀口虚线，半透明粒子）+ BoardSeams（切过的缝，暗色半透明粒子）+ BoardStand（立着的刀 / 工具，
                        借来的半透明粒子）/ BoardEffects / BoardFx / BoardInv / BoardGlow（客户端）= 切菜板站点（切、摆盘、插工具），
                        声音按 Shared/Rules/BoardSounds，旁边没开站点的人由 Server/BoardLook 广播 + BoardWatch（客户端）补上声音；
                        PotLogic + PotSync + PotScoop（服务端）+ PotView + PotPick + PotHud + PotOffer（客户端，开着站点的人：点击、拾取盒和
                        拿着东西点下去怎么办（盛 / 点锅口放进去，松手才发）、勺子在手里时的 busy() 和冻住的悬停、徽章和提示、悬着的容器和它浸汤的动作）= 厨锅站点；
                        PotScenes + PotScene + PotProps + PotSceneFx + PotModel + PotFx + PotHands + PotBiome（客户端）= 谁都看得见的锅里场景：开盖、
                        汤面（清水按所在群系取色）、漂着的料、碎料、勺子、气泡蒸汽和声音、倒 / 磕 / 抖进锅的手部动作（docs/diegesis/DESIGN.md §10）；
                        PanLogic（服务端）+ PanView（客户端，开着站点的人）+ PanScenes / PanScene / PanModel / PanFx（客户端，谁都看得见的
                        锅里场景：食物落进来、颠锅、油膜热气）= 煎锅站点，世界外观由 Server/PanLook 广播；
                        GrillLogic（服务端）+ GrillView（客户端，开着站点的人：机位、托盘、命中盒、点击变动作）+ StoveScenes / StoveScene /
                        StoveWorld / GrillPieces / GrillSpace / GrillGhosts / GrillFx（客户端，谁都看得见的烤架场景：东西、落下 / 翻面 / 取走的动作、
                        热浪蒸汽和该翻了的烟、声音）= 炉灶站点，世界外观由 Server/StoveLook 广播；
                        FryTints（客户端，两个场景共用：朝上那面半熟的件上叠一颗熟色粒子，见「煎锅 / 炉灶上东西朝上那面的熟色」）；
                        DishCrafts（工作台摆出砧板菜的配方时拦下）；三个站点照 JE 的做法见 docs/diegesis/DESIGN.md §11；
                        TableHooksLink（服务端，前置包的原版工作台站点上登本包的补还剩余物和砧板菜否决，table / board 两步调它）+ TableServerLink / TableClientLink（table 步骤；客户端那一步给前置包配方书的登记口登砧板菜不进书）；
                        TouchFeel（客户端，四个站点共用：触屏的轻震、双击间隔、点选的东西飞上站点，问前置包的 view.buzz / view.doubleSeconds / view.flyIn，老版本没有就算了，
                        docs/diegesis/DESIGN.md §9；砧板、煎锅、炉灶在发 place 的地方调 flyIn，只在照客户端的状态放得上去时调，厨锅走内核自己的点击）；
                        FlatSprites（客户端，纯逻辑，四个站点的表现类共用：答前置包的可选钩子 flatSprite，手上拿着的方块物品里哪些引擎画成一张平面图——查 Shared/Data/FlatBlockItems；
                        前置包没有 FLAT_SPRITES 就不挂，docs/diegesis/DESIGN.md §9；同一个模块还答 shownAs：蘑菇丛在手上画成它那件只用来显示的平面物品，前置包没有 SHOWN_AS 就不挂）；
                        HoldMenu + PotHold / BoardHold / PanHold / GrillHold（客户端，触屏长按菜单：前置包的可选钩子 onHold 的条目和各站点的判断，只给和点一下不一样的右键 /
                        Shift 点击变体，老版本的前置包没有 HOLD_MENU 就永远不会被问，docs/diegesis/DESIGN.md §9）；
                        四个站点的开关、搅拌、食谱书、烹饪倍率读 Shared/Data/HandsOnConfig（docs/diegesis/DESIGN.md §4.1）：每个站点的 register 在配置里关了返回 None
                        （服务端、客户端同一个条件），各站点的步骤看返回值连带广播、场景、旁观声音、DishCrafts（返回 False 的步骤记成 skipped）；
                        BookSources（客户端，把各站点的食谱书交给前置包）+ BookFill（服务端，照书从背包放料）；
                        未安装（或前置包太旧）则不做任何事：除了两个入口、Presence、Steps、两张步骤表，这里的模块一个也不会被导入
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
  联动的入口、判定和步骤表（`ServerBoot` / `ClientBoot` / `Presence` / `Steps` / `ServerSteps` / `ClientSteps`）规则表里带一份"只许导入"的清单（QuModLibs、它们自己这一组、`Shared/Rules/HandsOnMode`、
  客户端入口提醒用的 `Client/Engine`），站点模块只能在步骤里才导入（见「联动（沉浸式交互前置）」）。
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

**联动契约原有的 21 个名字一个字没动**（`tests/test_legacy_modattr_contract.py` 锁着；同步登记的容器必须就是契约交出去的那个对象，`tests/test_table_sync.py` 逐个核对）。
2026-11-19 往白名单里加了三个给站点用的名字（只加不改，`tests/test_contract_station_tables.py`）：`DishList`、`OneSidedList`、`NotOnGrillList`——HoD 里后两样是物品标签（`KitchenTags.ONE_SIDED / NOT_ON_GRILL`）、
摆盘的菜是配方，数据包都能加；我们这边原来是规则里写死的 frozenset 和不在白名单里的生成表，下游够不着。
2026-11-26 又加了一个（只加不改）：`CuttingTagDict`，原料是一个物品标签的砧板配方（`{标签名: 和 CuttingBoardDict 一样的值}`，JE 的 `cutting/tag_dough` 还原在这里）；
契约表里不放 `#` 开头的假物品名，所以单开一张。查配方一律经 `Shared/Rules/CuttingStation.recipeOf`（精确的先，再按标签名的顺序看标签）。
同步是旁路：服务端在模块导入时记下各张表的样子，下游追加完之后把"现在 - 基线"发给客户端，客户端并进它自己的表。

**同步哪些表**（表名即契约的变量名，`Shared/Rules/SyncTables.py` 登记；客户端真有地方读的才同步，`OneSidedList` 例外，见它那一行）：

| 表 | 下游怎么改 | 客户端哪里读 |
|---|---|---|
| `CuttingBoardDict`（键 `(物品名, aux)`） | 追加键；`tool` 引用 `knifeList` / `axeList` | 砧板 `BoardStation.Env` 的 `recipeOf / cuttable / cutsWith / isToolItem / usable / shiftPlaces`（托盘亮不亮、借哪把刀、Shift 放不放、点板是落刀还是敲一声，`BoardView.py:68-101,125-130,179`）、`BoardDraw.kindOf`（问 `Env.isCarving`：板上是不是插着的工具，没开站时 `Client/BlockItems` 问同一个）、`StationBooks.boardPages / boardCurrent`（食谱书"切"的页） |
| `CuttingTagDict`（键是标签名） | 追加键 | 同上：`CuttingStation.recipeOf` 在精确的查不到时看它；食谱书的 `c:#标签名` 那一页、JEI 按标签的成员登记 |
| `knifeList`、`axeList` | 追加名字（`append`） | `Client/BlockItems.isKnife`（站点和没开站时的展示都问它）、`CuttingStation.isKnifeRecipe / fitsTool`、`BoardStation._tools`（全部配方的工具名）、`GrillStation.opens`（手里拿刀开不开炉灶，`GrillStation.py:78`） |
| `CanCookedFoodDict` | 追加键 | 都经 `Shared/Rules/Grilling`（先查这张表，查不到问引擎的营火配方）：煎锅 `PanStation.usable / canFry / friedOf / acceptsFryable`（`PanView.py:112,123`）、炉灶 `GrillStation.usable / canGrill / mayPlace / opens`（`GrillView.py:46,49,69`）、手持煎锅"煎还是吃"（`Client/Input.py:42`）；`StationBooks.panPages / grillPages`（`cookGroups`：三种蛋一页）和 JEI 的煎锅 / 炉灶页只列这张表 |
| `StoveList`、`CanProvideHeatBlockList` | 追加名字 | `GrillStation.STOVE_BLOCKS`（`GrillBlocks.GRILL_BLOCKS`：每次按 `StoveList`（还是那个列表对象）加上熄着的孪生方块现判，`GrillView.py` 交给前置包按"方块名 in 它"认站点方块：客户端先判再请求开站）、`StoveScenes`（哪些方块有场景）、`Client/BlockItems.kindOf`（灶上的东西怎么摆）、`Client/Input._nearHeat`（手持煎锅身边有没有热源，读 `CanProvideHeatBlockList`）。熄着的方块不进这两张表（不烤、不烫脚、不给锅热） |
| `CookingPotRecipeList`（按下标对应） | `interface` 追加配方；`AddCookingPotRecipe` 给已有配方的 `Recipe` 列表就地加一种写法 | 厨锅索引 `CookingPot.rebuildIndex`（`PotStation.usable / mayPlace / isIngredient / isVessel`，`PotView.py:62,65`；`PotLayout`、`vesselOf`、`cookSecondsOf`）、`PotScenes.opensStation`（`:49`，读 `Vessel`）、`StationBooks.potPages / potRecipe / potCurrent`（书页的键就是下标）、dolor 经典界面的食谱格与它的客户端预测（`CookingPotBook` 按搜索词记着过滤结果，表的长度或 `CookingPot.revision`（重建索引的次数）变了就重算：并表之后的 `rebuildIndex` 让它跟上） |
| `platePackagedFoodDict` | 追加键 | `BoardInv.typeOf`（盘装的盛宴当食物，和服务端 `GetItemType` 一致） |
| `DishList`（按下标对应） | `interface` 追加一行或几行（写法同 `Shared/Data/Dishes.py`：`result` (物品名, aux)、`count`、`ingredients` 1 到 9 个 (物品名, aux)、`extras`、`keeps`；写坏的行整批拒绝，返回 False） | 摆盘菜的索引 `DishStation.rebuildIndex`（契约追加后服务端当场重建，客户端并表后重建）：托盘里哪些亮、层接不接得上、做成哪道、食谱书的页、工作台拦哪些菜 |
| `OneSidedList` | 追加名字 | 客户端眼下没有地方读，照旧同步（下游在用这张契约表，两端一样）。服务端的煎法 `PanStation.isOneSided`（`ONE_SIDED` 就是这个列表）：煎锅 / 炉灶站点上只煎一面、不用翻。不管样子：蛋看 `PanStation.isCracked`（`PotSunk.CRACKED`，HoD 的 `cracked`），追加进来的照样画它自己、照染；也不管书上的秒数（`SkilletBook` / `StoveBook` 都写两面的时间，`StationBooks._cookPages`） |
| `NotOnGrillList` | 追加名字 | `GrillStation.canGrill`（`NOT_ON_GRILL` 就是这个列表）：炉灶站点的烤架不收，托盘里不亮 |

没有同步的（`SyncTables.NOT_SYNCED` 逐个写着原因，测试核对"白名单 = 同步的 + 这里的"，新增变量时会红）：`ComposterItemDict`、`itemChangeBlockDict`、`shapedRecipeContainerDict`、`pieList`、
`canClimbList`、`cabinetList`、`WildCropDict`、`cropsDict`、`negativeEffect`、`horseComponentsDict`、`wolfComponentsDict`（只有服务端读），`uiGuideBookPath / Screen`（字符串常量，契约没法往里追加）。
联动契约之外的表（`BrothColors / FoodColors / ItemMasks`、`Remainders`……）下游本来就够不到，没有"追加"可同步：下游的菜用兜底汤色，没有刀口遮罩。

**怎么同步**（纯规则在 `Shared/Rules/`，服务端和客户端各一个薄模块）：
- **基线与差异**（`TableDiff.Syncer`，服务端）：`Server/TableSync.py` 导入时建一个，记下各表那一刻的编码——下游在 `LoadServerAddonScriptsAfter` 里才追加，晚于任何模块的导入，
  客户端导入后的表也是这个样子。发的是**累计**的"现在 - 基线"，只含新增和改动：名字列表是基线里没有的名字；字典是键不在基线里、或值不一样的条目；
  厨锅配方按下标，新增的行和被 `AddCookingPotRecipe` 加了写法的行（带基线的行数 `base`）。字典表（砧板、按标签的砧板、能煎烤的东西……）**删掉的键也同步**（2026-11-26）：基线里有的、或者曾经发出去过的键现在没有了，发 `{"k": 键, "gone": true}`，客户端照删；删了又加回来的再发一次（哪怕和基线一样）。名字列表照旧只加不删；厨锅配方删配方是打墓碑（`Disabled`，一行变了）。
- **编码**（`TableWire.Codec`）：Call 载荷的规矩是键 `str`、列表元素类型一致、没有 `unicode`、元组到对端变列表（前置包 `Shared/Wire.py` 记着同一组，两个包互不导入，
  测试用它的 `wireProblem` 核对每条消息），所以数据表里的值要换写法：`(物品名, aux)` 压成 `{"$pair": "名字|aux"}`，别的元组 `{"$tuple": …}`，类型混着的列表 `{"$mixed": {"0": …}}`；
  **就是** `knifeList` / `axeList` 等登记过的那个列表对象的，写成 `{"$ref": "knifeList"}`，客户端换回它自己的那一个——砧板配方的 `tool` 和服务端一样是引用，之后追加的刀对所有配方一起生效。
  py2 的 `unicode` 两端各换一次 `str`。传不了的值（自定义对象、集合、键不是 `str` 的嵌套字典、嵌套超过 16 层）：**那一条跳过并记日志**（`[arrisFarmersDelight] 表同步：…`），别的照发；
  厨锅配方新增的那一行编不了时放一个空行占着下标（书页的键、书里放料发的键都是下标，后面几行不能错位）。deepcopy 不认的东西让"变没变"的快速检查退成每次重算，同步不会停。
- **并表**（`TableMerge.apply`，客户端）：就地改、不换对象（前置包拿着的容器每次按 `StoveList` 这个列表对象判）；幂等（本端已经有一样的东西就不动它：重复收、晚收都一样，
  单机联机两端共用一份表时也不会把下游手里的配方字典换成副本）；厨锅配方里本端已有的行就地合并（行字典、`Recipe` 列表都原地换内容，不换对象；每格的选项是行里的 `Slots` 键，照常过线）；
  一条条隔离，换不回来的条目记日志跳过，消息本身不对（版本、表名、种类，或 `base` 比本端的表还长：两端不是同一版）整条不理；
  并进去有变化的表重算缓存：厨锅配方索引（`CookingPot.rebuildIndex`）和砧板的工具表（`BoardStation.invalidate`，它的缓存键现在也看 `knifeList` / `axeList` 的长度）。其它站点读表都是现读的，没有缓存。
- **什么时候发**（`Server/TableSync.py`）：① 玩家进服（`ClientLoadAddonsFinishServerEvent`：客户端刚加载完 Addon、端点已经登记好；dolorContainer 也在这时把绑定的方块名告诉客户端）
  发一次累计的差异——必须在他开任何站点之前，而且"这一下右键开不开站点"是客户端先判的（`StoveList` 里没有的方块客户端根本不会去请求开站），**所以不能等开站时再发**；
  ② 之后每 5 秒看一眼表变没变（下游可以随时追加，也可以不经接口直接改 `obtain` 拿到的对象，没有事件可听；一次检查是几张表和上次的深拷贝在 C 层比一下，开发机上不到 0.1 毫秒），
  变了就把新的一版补发给进过服的人，每张表记着自己的版本（`rev`），补发只要他没收过的那几张；没进服的人（客户端还没加载完）和走了的人不发。没有任何追加时什么都不发。
  两条路都要：万一某个环境里 `ClientLoadAddonsFinishServerEvent` 比下游的 `LoadServerAddonScriptsAfter` 还早，定时那条 5 秒内补上。热重载脚本之后进过服的名单是空的、
  也不会再有进服事件，调试时用 `TableSync.step(everyone=True)`（游戏内自检的追加函数里就是它）。
- 客户端端点 `OnTableSync`（`Client/TableSync.py`；`status()` 给调试看收了几条、改了几张、跳过几个）。

**限制**：名字列表（刀、炉灶……）只同步新增，下游从列表里删的名字客户端留着（多认一个不会坏事）；只靠标签认的刀（`arris:knife` / `common:knife`，不在 `knifeList` 里），
客户端经 ItemTags 问客户端的口（`Client/BlockItems.isKnife` → `Shared/Rules/Knives`，见「标签（netease_tags）」）；JEI 联动（`Compat/Jei`，界面就绪时一次性登记）读的是登记那一刻的客户端表，晚到的下游内容不在 JEI 里；站点开着时表又变了，托盘亮不亮等下次开站才按新表算
（`BoardView._usable` 每次开站建一份）；已经加载好的下游炉灶方块，场景要等下次加载 / 广播才建。

## 标签（netease_tags）

网易 3.10 的 `netease_tags`：农夫乐事登记一套 `common:` 词表，别的模组往同名的标签里放自己的东西，双方就认得对方的番茄、刀、热源（对外文档 docs/TAGS.md）。

- **词表**：`Shared/Data/Tags.py` 一张表说了算（标签名常量、`ITEM_TAGS` / `BLOCK_TAGS` 的成员、原版自带的 `VANILLA_TAGS`、JE 标签名的对照 `JE_NAMES`）；
  `py -3 tools/gen_tags.py` 从它生成 `bp/netease_tags/`（一个标签一个文件）和 docs/TAGS.md 里的词表，`tests/test_netease_tags.py` 核对是不是最新。
- **查询**一律经 `Shared/Rules/ItemTags`（`has` / `itemsOf` / `tagsOf` / `blockHas` / `blocksOf` / `generation` / `refresh`），不直接调引擎。
  引擎口是 `Shared/Rules/TagPort.EnginePort`，两端的 `Tags` 模块（`Server/Helpers/Tags.py`、`Client/Tags.py`）装上它，由两端入口最先导入；
  单机时两端在一个进程里，两个口都在用服务端的。
- **准备好之前**（客户端进世界之前读不全）：枚举（`itemsOf` / `blocksOf`）只给静态表；按单件问的（`tagsOf`、`has` 里按物品问的那一半）照样问引擎、
  并上静态表，但不缓存。**准备好**（有反查接口时，反查 `common:raw_beef` 里出现了原版的 `minecraft:beef`；3.10 以前按物品问得出原版物品的标签）之后：
  静态表 ∪ 引擎的答案，按标签 / 物品缓存；准备好的那一刻、装卸口、`refresh()` 时换代（`generation` 加一），按标签建了索引的地方据此重建
  （厨锅的 `PotRecipeTable` 准备好之前一个答案都不记，见下一节）。
- **判断点**：`Shared/Rules/Knives`（是不是刀：`knifeList` ∪ `arris:knife` ∪ `common:knife`）、`HeatSources`（热源方块：`CanProvideHeatBlockList` ∪
  `common:heat_source` ∪ 点着的 `common:heat_source_lit`）、`Grilling`（能煎烤什么：先查 `CanCookedFoodDict`，查不到问引擎的营火配方，自己也有一个口）；
  厨锅的标签格、砧板按标签的配方也问 `ItemTags`（见下一节）。
- **自检**：两端的 `McdkTagsTest`（`Server/Debug`、`Client/Debug`：口准备好没有、词表每个标签引擎反查到的成员和静态表比、刀、营火配方的原始返回值和解析、
  热源标签；怎么调写在文件头）。

## 新联动接口与配方的登记

对外文档：docs/EXTENSION-API.md（接口）、docs/RECIPE-JSON.md（配方 JSON）、docs/COMPATIBILITY.md（兼容承诺）、docs/API-CHANGELOG.md（变更记录）。
兼容入口（linkage.md 的 ModAttr 三个函数，`Api/LegacyModAttr.py`）照旧，新接口和它读写同一份数据。

**ready 和门面**（`Api/ExtensionApi/`）：服务端 `Server/ExtensionReady.py` 在 `LoadServerAddonScriptsAfter`（经 ModServer → EventRegistry）、客户端
`Client/ExtensionReady.py` 在 `LoadClientAddonScriptsAfter` 调 `Ready.publish(side, 系统)`：每端只播一次，载荷 `{"extension": ext, "side", "apiVersion"}`，
广播用的系统 `("arrisFarmersDelight", "ExtensionApi")` 到要广播时才注册（`Server/ExtensionSystem.py`、`Client/ExtensionSystem.py`），拿不到系统只打日志、
别的模组的处理函数抛了异常接住打一次调用栈。门面 `Facade.getExtensionApi(side)` 每端一个；能力名在 `Events.SERVER_CAPABILITIES / CLIENT_CAPABILITIES`
（`tests/test_extension_docs.py` 核对和 EXTENSION-API.md §3 的表一样）。`Api/` 只导入 `Shared/`：服务端要做的引擎的事（`syncToClients` 时现在就同步）
由 `Server/ExtensionReady` 在广播之前经 `Recipes.provide(syncNow=…)` 交进去。服务端广播之后接着读行为包里的 `farmersdelight_recipes/**.json`
（`Api/ExtensionApi/RecipeFiles.py` 定 ID、登记；跨包读文件的 `Server/Helpers/PackJson.py` 用引擎内部的 `server_resource`，经 `traceback.sys.modules` 取，
2026-11-26 在游戏里核过：探针包里不写 id 的 JSON 读到了，能力名 `recipe_json_files` 因此登记，`Events.RECIPE_JSON_FILES_VERIFIED`），再调一次 `onRecipesChanged` 的处理函数；
`ExtensionReady.scanReport()` 给自检读这一次读了什么。

**配方存在哪**：不另起存储，还是联动契约的那几张表（表同步、六个下游包、十几个读表的地方都建在上面），只加可选的键：
- 厨锅：`CookingPotRecipeList` 的一行多 `Id`（配方 ID）、`Slots`（每格的选项：`"ns:name"`、`(名, aux)`、`"#标签"`）、`Disabled`（墓碑）。
  农夫乐事自己的 28 道照 JE 写 `Id`（`farmersdelight:cooking/<JE 文件名>`）和 `Slots`（JE 的 forge: 标签换成词表名，`tests/test_cooking_pot_data.py`
  在 `.refs` 在场时逐格核对），`Recipe` 照旧是原来那 170 种写法（`CookingPotRecipes._dish` 由同一份格子展开：标签按词表里农夫乐事登记的成员，蛋只展开普通鸡蛋）。
  新接口登记的那一行，`Recipe` 是按登记那一刻标签的成员展开的快照（最多 64 种，`RecipeTables.SNAPSHOT_WAYS`），只给只认物品写法的旧读者看。
  下标是身份（书页的键、`PotRecipeMemory`、站点），所以同 ID 覆盖是原地换内容、删除是打墓碑，都不挪下标。
- 砧板：原料是物品的在 `CuttingBoardDict`，是一个标签的在 `CuttingTagDict`（键是标签名，不带 `#`；联动契约白名单第 25 个名字）；查配方一律经
  `CuttingStation.recipeOf / recipeKeyOf`（精确的先，再按标签名排序看 `ItemTags.has`）。新接口登记的条目多一个 `"id"`（随表同步，两端按 ID 查到的一样）。
- 营火：`CanCookedFoodDict[原料] = 成品名`，值的形状不变；登记用的 ID 只在服务端的 `RecipeTables._ids / _keys` 里，客户端查到的是派生 ID。
- 配方 ID 的规矩和旧接口追加的配方的派生 ID（`legacy:…`，厨锅同一成品按表的先后加 `_2`、`_3`）在 `RecipeIds.py`；
  JE 写法的 JSON → 规整的配方在 `Shared/Rules/RecipeJson.py`（Builder 写出来的就是同一份 JSON，`registerFromJson` 和 `register()` 走同一条路）。

**厨锅怎么配**（`Shared/Rules/CookingPot.py` 是公共函数，索引和记着的答案在 `PotRecipeTable.py`，格子在 `PotSlots.py`）：照 JE 的 `RecipeMatcher.findMatches`，
一条配方有 `Slots` 形（锅里每件东西分给一个收它的格、格子正好用完：二分图完美匹配，最多 6 格）和 `Recipe` 里每种旧写法（多重集合相等）两种形，
几条都配得上时表里靠前的赢；墓碑和坏行哪里都不认。配上的是旧写法时余料照那种写法算（和原来一样）。按排好序的输入记答案；`rebuildIndex()` 只作废、
下次用到时重算（登记一条不再整张重建），`ItemTags.generation()` 变了清掉记着的答案，引擎口准备好之前不记。站点的候选摆法 `candidatesFor` /
`partsFor` 在旧写法之外加上格子能给的摆法（`PotSlots.partsOf`）。读格子的地方：经典界面的详情轮换（`CookingPot.framesOf`）、"添加食材"
（`waysWith`：按锅里和背包里有的料把格子具体化成写法）、站点的食谱书（`optionsOf`）、JEI（`usesOf`）、汤里漂的碎料（第一帧）。

**表同步**：新键都是 `str` / `list` / `tuple` / `dict`，照常过线（`tests/test_table_sync.py` 核对并表后 `Slots` 还在）；字典表删掉的键也同步
（见上面「联动契约与客户端的表」），所以新接口删砧板、营火配方客户端跟着删；厨锅删配方是墓碑（一行变了）。
不冻结：表一直是活的，ready 之后再登记照样生效、5 秒内同步，`syncToClients()` 现在就发（`TableSync.step()`）。

**测试**：`test_extension_api`（协议、门面、ready、接线）、`test_extension_recipes`（三类配方、ID、覆盖、删除、客户端）、`test_extension_registries`、
`test_recipe_files`（行为包 JSON、PackJson、先广播再读再通知）、`test_extension_docs`（能力名和文档一致）、`test_pot_slots`、`test_cooking_pot_data`、
`test_cooking_pot_match`（和原来的索引逐种写法同一结果）、`test_pot_slot_readers`、`test_cutting_tags`、`test_table_sync_deletions`。
游戏内自检 `Server/Debug/McdkExtApiTest.py`（文件头写着怎么调）。

## 联动（沉浸式交互前置）

亲手做菜的站点（Hands-On Delight 的移植）要装单独的作品「沉浸式交互前置」才有；本包不依赖它：没装时就是原样的农夫乐事，Hands-On Delight 的东西一样也不跑。
本文里写的 `docs/diegesis/DESIGN.md`（前置包内核和四个站点照 JE 怎么做的、实机量到的事实）是**前置包工程里的文档**，不在本仓库、不随本仓库上传（2026-11-18 起）：
前置包是独立工程 arrisDiegesis（`ArrisTeam/netease-diegesis`，2026-11-25 从本目录搬出去），开发机上在旁边的 `../arrisDiegesis/docs/diegesis/DESIGN.md`。
联动的做法照机械动力系列的附属包（无中生有等）：运行模式每端判定一次、记在一个地方，注册写成步骤表，业务模块在自己的步骤里才导入，一步出错不拦别的步骤。
不一样的只有怎么发现前置包：不用联动 SDK 的 ready 事件，照旧 `ImportModule("arrisDiegesisScripts.Api.Server" / ".Api.Client")` 取接口模块、读 `API_VERSION`，可选功能读接口上的功能旗。

- **运行模式**（`Shared/Rules/HandsOnMode.py`，纯逻辑）：每端一个——`pending`（加载期到判定点之前）、`linked`（接口够新，步骤表在跑或跑完了，个别步骤可能失败或跳过）、
  `outdated`（前置包在，接口比本包要的老，一步不跑）、`standalone`（判定点到了还是没有前置包）。`mode(side)`；`linked()` 问"这个进程里联动了没有"——服务端的代码和 Shared 的规则不知道自己在哪一端，
  一个进程又只联动它自己跑的那一端（单机两端同进程，两端都联动），所以任何一端联动了就是联动了；`whenDecided(side, callback)` 判定好了才调、已经判定了马上调、之后模式又变了带着新模式再调一次；
  `decide(side, 模式)` 只有 `Presence` 调。判定之前一律当没联动。
- **判定**（`Compat/Diegesis/Presence.py`，两端共用、不碰引擎）：入口 `ServerBoot` / `ClientBoot` 在 `modMain.py` 里登记，导入时 `Presence.attach(side, 步骤表, listen=, find=, load=)`，
  引擎的 `Listen`、找前置包接口用的 `ImportModule`（没有是 `None`）和步骤导入本包自己的模块用的 QuModLibs `ImportModule` 由入口交进去。
  - 接口在、`API_VERSION` 不低于 `Presence.REQUIRED_API_VERSION`（3；前置包没有发过更低的版本，原来按站点分的 1 / 2 / 3 三个门槛并成这一个）：**先把模式拨到 `linked`，再跑步骤表**——
    站点自己的 `register` 问 `HandsOnOptions`，没联动时它说 HoD 不在（站点开关是假），不先拨的话每个站点都登记成"关了"；
  - 接口在、版本比它低：`outdated`，一步不跑；
  - 找不到：服务端导入时找一次（前置包的服务端接口是纯 Python，早于它的系统导入也安全），`LoadServerAddonScriptsAfter` 里再找最后一次（前置包比本包后加载时）；客户端只在
    `LoadClientAddonScriptsAfter` 里找（前置包的客户端接口会带进它自己的 QuModLibs，更早导入不安全）；最后一次还没有就是 `standalone`；
  - 接口模块导入出错（装坏了、版本混了）记一条日志、当它没装；判定只做一次，步骤也只跑一次。
- **步骤表**（`ServerSteps.py` / `ClientSteps.py`，只放数据，`Steps.py` 执行）：一项 `(步骤名, "相对脚本根的模块路径:函数名", 条件或 None)`，一个站点一步，顺序是原来登记的顺序
  （砧板 `board`、厨锅 `pot`、煎锅 `pan`、炉灶 `grill`），最后一步 `table` 不是本包的站点（见“合成与合成剩余物”最后一段：前置包的原版工作台站点上登记本包的规则）；
  条件是接口上的可选功能旗（炉灶要 `FACING_HOOK`），接口没有这一步就 `skipped`、连模块都不导入。步骤函数（`BoardServerLink.link(ctx)` 这一类）
  做原来入口里这个站点做的全部：调站点自己的 `register(ctx.api)`，返回 `None`（配置里关了这个站点）就返回 `False`、这一步记成 `skipped`，登记上了再开连带的东西——`pot` 开 `PotLook`、`pan` 开 `PanLook`、
  `grill` 开 `StoveLook`（客户端还让出灶上东西的烟）、`board` 开 `BoardLook`（客户端 `BoardWatch`）并在 `remove_crafting_recipes` 开着时登记 `DishCrafts`；客户端的步骤同时开场景
  （`PotScenes` / `PanScenes` / `StoveScenes`）。步骤抛异常记成 `failed`、打印 traceback，别的步骤照常跑。`ctx`（`Steps.Context`）有 `side`、握过手的前置包接口 `api`、它的 `apiVersion`。
- **没联动时关掉了什么**：入口只导入 QuModLibs、`Presence`、`Steps`、`HandsOnMode`、步骤表（客户端入口还有提醒用的 `Client/Engine`），**站点模块在步骤里才导入**——所以没装（或太旧）时 `Compat/Diegesis` 里别的模块一个也不存在，
  它们的 `@Listen`（每帧的 `GameRenderTickEvent`、方块实体的加载 / 卸载）和 `@AllowCall`（`OnPotLook`、`OnPanLook`、`OnStoveLook`、`OnBoardLook`）也都不存在
  （`tests/test_presence_standalone.py` 核对 `sys.modules` 和假加载器记下的监听 / 端点；`tests/test_architecture.py` 规则表里的 `only` 清单守着入口、判定和步骤表不导入站点模块）。
  核心（`Server/`、`Client/`）里和 HoD 沾边的几处也不再看配置：`HandsOnOptions` 的取值函数没联动时一律说 HoD 不在（站点开关假、不要搅拌、没有食谱书、三个倍率 1.0），所以厨锅按配方自己的时间煮、
  不看 `cooking_pot_time`，手放的厨锅料（存档里留着的）不等勺子，存档里留着手放的煎锅 / 炉灶（以前装过前置包）交还给农夫乐事原样煎 / 烤；`HandCooking.addMade` 没联动时不往玩家数据里写
  "做过几份"。四个世界外观广播（`PotLook` 等）本来就默认关着、由步骤打开。砧板 / 煎锅 / 炉灶上东西的世界展示（`Shared/Rules/BlockDisplay` + `Client/BlockItems`）没联动时是 FD 自己的渲染器（`CuttingBoardRenderer` / `SkilletRenderer` / `DefaultStoveRenderer`：位置、高度、大小、错开、朝向、一叠几张逐项对过 Java，
  `tests/test_classic_block_display.py`），联动着但配置里关了砧板站点时一样；只有砧板站点在场（`HandsOnOptions.cuttingBoard()`）时板上的东西才摆成站点里的样子（HoD 的 `BoardScene`），开站、关站不跳。
  煎锅、炉灶不分模式：站点在场时场景接管、这份展示收起来。
- **前置包太旧的提醒**（`ClientBoot`）：客户端的模式是 `outdated` 时，本地玩家进了世界（`OnLocalPlayerStopLoading`）在左上角（`CreateTextNotifyClient(levelId).SetLeftCornerNotify`，文字是 `str`）
  提醒"前置模组沉浸式交互前置版本过旧，亲手做菜的站点不会启用，请更新"，隔 8 秒再提醒，共三次。没装前置包（`standalone`）不提醒、不打扰玩家；服务端没有这个提醒（日志里有一行）。
- **看现在的状况**：每次判定在日志里留一行（`[arrisFarmersDelight] 联动（server 端）：linked，前置包接口 3，board=ok，pot=ok，pan=ok，grill=ok`）；游戏里用 `execute_code`
  （`is_client` 为假是服务端、为真是客户端）：`from arrisFarmersDelightScripts.Compat.Diegesis import Presence as P; return P.report("server")`（客户端写 `"client"`），
  返回本端的模式、`linked`（整个进程）、前置包接口版本和每一步的 `[步骤名, 状态, 说明]`（状态是 `ok` / `skipped` / `failed`）。
- **QuModLibs 的监听对晚导入的模块照常生效**：`@Listen` → `LoaderSystem.REG_STATIC_LISTEN_FUNC` → `nativeStaticListen`，只是把"向引擎挂监听"排进加载器系统的 `_callQueue`，系统每个 tick 的 `Update` 清一遍队列
  （两端相同；`@AllowCall` 是立刻写进 `_QCustomAPI` 的），所以步骤在 `LoadClientAddonScriptsAfter` 里才导入的场景模块，监听最迟下一个 tick 挂上。监听按"模块名.函数名"去重，
  所以 `Presence` 两端的事件处理函数是两个不同名字的函数（`onServerLoaded` / `onClientLoaded`）。
- **玩家自己的站点开关**（客户端最后一步 `settings`，只有客户端有；`Compat/Diegesis/SettingsClientLink.py`，规则 `Shared/Rules/StationSwitches.py`，条件是接口的 `SETTINGS`）：
  往前置包的设置界面（站点上的齿轮）和网易"通用设置"页里登一组 `farmersdelight`（页签"农夫乐事"）：总开关"全部厨具" + 这一端登记成功的站点各一项（厨锅、砧板、煎锅、炉灶；
  配置里关了的、没登上的不出现，四个都没登上不登、记 `skipped`），每项管着那个站点登记用的站点 id（各站点 `*Station.STATION_ID`）。关了的站点内核在右键时说不开站、不取消，
  方块照农夫乐事原样用（厨锅是经典界面）；开关存在这个玩家的客户端，服务端不知道。字是 `rp/texts` 两份语言文件里的 `arris_fd.settings.*`。
  老的前置包没有 `SETTINGS`：这一步 `skipped`，什么都不登、不报，一切照旧。
- **砧板那一项要告诉服务端**：联动着、`remove_crafting_recipes` 开着时，工作台上的砧板菜对所有人否决（`DishCrafts`、`TableHooksLink.dishVeto`），前置包工作台的配方书里也藏掉
  （`TableClientLink`）；关了砧板（或总开关）的玩家开不了砧板站点，这些菜就没处做。照 HoD 的"没有砧板站点就不拿掉合成"（`HandsOnOptions.removeCraftingRecipes`）按玩家延伸：
  "砧板站点对我开不开" = 总开关 and 砧板那一项（`StationSwitches.boardOn`）。客户端登记完自己算一遍、报一次（登记时内核不调 `onChange`；设置存在本机、哪个存档都一样，
  所以每次进世界都报），之后总开关或砧板那一项改了再报，本地玩家进了世界（`OnLocalPlayerStopLoading`）再报一次同样的值；同一个值管书里藏不藏（`TableClientLink.hidden` 现读）。
  服务端 `Compat/Diegesis/BoardSwitch.py`：端点 `BoardSwitchReport`（`@AllowCall` + `@InjectHttpPlayerId`，值只当布尔用），按玩家只记关着的（`StationSwitches.Choices`），
  缺省开着（刚进服还没报到、前置包太旧没有设置时否决照旧），玩家下线清掉（`DelServerPlayerEvent`，`ModServer` 为它多挂了这一个监听）；跟着否决在 `board` 那一步开（`BoardSwitch.enable`），
  没登否决时不收。已知的一瞬间：拨开关那一下客户端已经不藏、服务端还没收到，这时点"照配方做"会被否决一次。
  测试：`tests/test_station_switches.py`（规则、两份语言文件）、`test_settings_link.py`（客户端登了什么、什么时候报）、`test_board_switch.py`（服务端两处否决、下线）、`test_settings_kernel.py`（放进前置包真的设置表：内核拦的和报给服务端的是同一个答案）。

## 厨锅界面（dolorContainer）

右键厨锅开的是 dolorContainer 的界面，不是 `netease:block_container` 的原生界面（阶段 A：只换界面，存储和烹饪逻辑不动）。

- 存储不变：8 个引擎容器格（`netease:block_container`，0-5 食材、6 容器、7 成品）；烹饪、热源、预览槽仍由 `Server/CookingPot.py` 在
  方块实体数据里推进，dolor 只接管界面、格子操作和食谱书。
- 打开：`Server/CookingPotHost.py` 登记容器类型 `arris:cooking_pot` 与方块宿主（库的 `Std/Block/Server.Host`）。宿主自己监听
  `ServerBlockUseEvent` / `ServerItemUseOnEvent`：对着厨锅使用时打开界面（潜行并拿着东西时放过；潜行空手右键是切吊把手、不开界面，见"厨锅的支架"；按住不重复开）。登记时库在运行期
  让引擎报厨锅的移除，所以方块 JSON 里**不能**再写 `netease:listen_block_remove`（两处同时开，方块和物品图标都不画）；
  `OnCookingPotRemove` 照常经 `BlockRemoveServerEvent` 收到事件。客户端那一半（`Std/Block/Client.py`）在 `Client/CookingPotUi.py` 里导入。
- 界面模型 `Shared/Menus/CookingPot.py` 两端各建一份：格子类型、Shift 点击的去向、界面数据、动作；服务端权威，客户端只预测。
  热源 / 进度 / 预览由 `CookingPotHost.readState` 从方块实体数据读，开着界面时每 4 刻重读（`dataEvery`）。手动放东西什么格子都收（与旧界面一致，
  成品格除外）；Shift 点击时容器格与食材格各挑自己收的：只当容器的碗、玻璃瓶进容器格、不会落进食材格，既是容器又是食材的卷心菜叶当食材
  （容器格里已经是它时才续上）。联机时客户端按自己的食谱表预测 Shift 点击；下游模组只在服务端追加的配方，经 `Server/TableSync` 进服时发给客户端、并进它的表
  （见"联动契约与客户端的表"），预测用的是同一批，没同步到的（条目传不了被跳过、消息还没到）仍以服务端为准。
- 样子照旧原生界面（`rp/ui/arrisCookingPot.json`，2026-11-22 照它重做）：三块并排、顶对齐、都高 175，整体在屏幕正中——
  左边**食谱选择**（83 宽，底图 `tutorial_book_screen_ui` 原样拉伸：浅色边框 + 深色凹槽）：顶上搜索框（74 × 20，提示字是键，
  右边一个放大镜图），下面是**食谱格**：4 列、一格 18、一格一道菜的成品，照食谱表的顺序；
  中间是厨锅本体与玩家物品栏（176 宽，原样没动）；右边**选中食谱的详情**（83 宽，原版对话框的底，摆法照旧界面的 `cookbook_bg`）：
  标题（22 高的一条，长名字折成两行，裁在这一条里、压不到下面）、3 × 2 食材格、朝下的白箭头、勺子 + 容器格、锅形预览框里的成品
  （框底的小三角裁掉）、常亮的火焰示意、"+"按钮和下面一行"添加食材"（后两样选了食谱才有）。背后垫一张 `recipe_back_panel`
  （196 × 168，比中间那块左右各多 10），侧栏各压进去 7，三块之间露出 3 宽的深色折缝；折缝和侧栏的空白处吃掉点击，不算点在界面外面。
- **食谱格**是算出的格子：集合 `recipes`（`Shared/Menus/PotRecipes.py`：库的 `Std/Slots.Choice`，原版切石机的配方按钮），落在 4096 格的
  虚拟容器上（点得到的格号上限 `MAX_PICK` 一样大），内容由部件 `RecipeGrid` 按这位查看者的搜索词算（`CookingPotBook.gridCells`；显示几格
  `shownCount`）。点一格发可预测的 `pick(格号)`：键鼠左右键、Shift、手柄照 Choice 按下就选；触屏改成抬起才选（`TapToPick`：手指拖动过、
  被滚动视图接走、松开在别的格子上都不算，不然拖着滚食谱格时会把开始按到的那道选上；旧界面的配方按钮也是抬起才算）。
  选中的那格底格换成 `recipe_book_touch_cell_selected`、一直留着，
  别的是 `recipe_book_item_bg`（旧界面配方按钮平时与按下的两张）；悬停写成品的悬停文本。布局用按行回收的 `scroll_grid_classic`
  （12 个行控件 × 4 格，控件数不随食谱数变；客户端导入库的 `Std/Windowed/Client`），列数固定 4，放不下才出现滚动条（格子右边、压在侧栏的
  边框上），不画滚动面板的底；28 道正好 7 行，不用滚。界面每画一格都问一遍内容，所以过滤结果按搜索词记着（同一个字典），
  表的长度或 `CookingPot.revision`（重建索引的次数）变了才重算。
- 动作：`search(字)`（边打边提交，可预测：客户端的食谱格当场跟着字变；字变了才清掉选中，输入结束时那一次同样的字不动它）、
  `pick(格号)`（按过滤后的个数核对，记下选中的时刻 `pickedAt`）、`addFood`。搜索词、选中项、选中的时刻是每位查看者的状态。
  客户端不传位置、玩家、背包下标；`addFood` 在会话的工作副本上从玩家背包搬运，整体成功或整体不做。
- **写法轮换**（照旧界面的 `FoodRecipeTimerSwitch`）：选中的食谱有几种写法时，详情的食材格每 `CookingPotBook.VARIANT_SECONDS`（1 秒）
  换下一种，从第一种开始（刚选中先完整显示第一种一个周期，再点一次从头来）。服务端在 `viewerValues` 里按钟算（`shownVariant`；
  钟是 `CookingPot.setClock` 注入的，缺省 `time.time`），开着的界面每 `dataEvery`（4 刻）重算一次，变了才发；只有一种写法的一条更新都不多发。
  详情的数据：`book`（0-5 食材、6 容器，`BOOK_CELLS` = 7）、`bookResult`（成品，画在预览框里）、`bookTitle`。
- **"添加食材"挑写法**（`Shared/Menus/PotFill.py`）：不认正在显示的那一种，而是把这道食谱的各种写法按"锅里 6 个食材格已经放着的、这种写法
  要的件数"从多到少排（一样多的照表里的先后）依次试：空格不够的跳过，必须放进空格的食材在背包里找不齐的跳过，第一种排得出来的就用它；
  它一件都挪不了（锅里已经齐了、背包里也没有可再加的）就拒绝 `nothing`，不再往后试（不把另一种写法的料混进锅）。全都不行时：
  有因为缺食材跳过的拒绝 `missing`，否则 `no_room`。格子里已经有配方要的食材时只在放得下时再加一个（反复点就是备多份料，`planFill`）。
- 布局：仓库根的 `layouts/cooking_pot.json`（手写）经 `tools/vendor.py` 编译成 `rp/ui/dolor_layout_*.json` 与 `dolorLayouts.py`。
  经典版与携带版**共用一个内容模板**（`content`），携带版只多一个 `$dc_dim`（照原版压暗背后；携带版的底座缺省不画背景）。
  携带版的物品栏同样是快捷栏 + 主背包两个格子区（`player_inventory_classic`），所以界面模型两种界面档的去向表、收集顺序一样
  （`routes()`；原来携带版那份按合并背包写）。触屏的物品详情照库的缺省离底边 16（面板在屏幕正中，详情在面板下面）。
  "添加食材"那一行和搜索框的提示写语言文件的键（`arris_fd.pot_screen.*`，见「砧板和站点的几处补齐」），不写字；"+"按钮没有字（画在贴图上）。
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
4. 热源、进度箭头、预览框随烹饪变化；食谱的搜索、选中、写法每秒轮换、"添加食材"（食材或空格不够时什么都不动）。
5. 携带版（压暗的背景、物品栏两个格子区的 Shift 与双击）与手柄焦点；活塞推动的厨锅、`/setblock` 出来的厨锅、断热源、成品格满了。
6. 2026-11-22 照旧界面重做之后（只在 Strata 里出过图）：食谱格选中的底格在游戏里认不认得出（脚本换底格对带九宫格说明的 `recipe_book_*`
   贴图是不是照样九宫格）、滚动条压在侧栏边框上的样子、标题折成两行时的高度、`rotate_angle` 转的箭头、触屏下食谱格的滑动；
   携带版里拿放时飞的那一下（0.3 秒）会不会被别的格子的图标盖住：库的携带版根把物品飞行渲染器放在第 12 层（经典版 21），
   共用的经典样式内容里格子图标累计的层数比 12 高（面板 1、body 5、图标 9 起）。

## 厨锅物品带着菜（对照 JE）

JE 的厨锅拆下来菜还在锅里：战利品表的 `copy_meal` 把"盛出格里那叠菜"写进厨锅物品的 `BlockEntityTag`，放回去照样在；食材格、容器格、
成品格里的东西照常掉出来；创造模式拆不出物品；物品堆叠 1；方块 `strength(0.5F, 6.0F)`。这边（`Server/CookingPotItem.py` + `Shared/Rules/PotItem.py`）：

- 方块的战利品表是空的（`air_loot.json`），厨锅物品由脚本在 `BlockRemoveServerEvent` 里掉：预览槽里煮好还没装碗的那叠菜记进物品字典的 `extraId`
  （`arris_pot_meal|物品名|aux|份数`），悬停文字写进 `customTips`（JE 的"装有 N 份：" + 菜名，前面留着 `%name%%category%…` 那几个占位符）。
  玩家是创造模式时（`ServerPlayerTryDestroyBlockEvent` 记一笔）不掉；那一格这时是移动中的方块（活塞推着走）不算拆。
  和煎锅一样，命令 / 脚本把厨锅换掉也会掉一口锅（方块没了的事件里分不出是谁拆的）。
- 拆锅时煮过几份还没领的经验在锅心（方块中心）弹出来（`OnCookingPotRemove` -> `PotContainer.awardExperience`，FD 的 `onRemove` 里 `getUsedRecipesAndPopExperience`）：
  不看是谁拆的，创造模式拆也弹；那一格是移动中的方块（活塞推着走）不算拆，记着的份数留着。
- 放置：引擎放方块的时候看不到物品，所以放置前（`ServerEntityTryPlaceBlockEvent`，`ModServer` 新挂的监听）读手里那口锅的 `extraId` 记一笔，
  方块实体建好（`ServerPlaceBlockEntityEvent`）时写进预览槽；记录按位置、5 秒过期（放置被取消就作废）。
- 实机核对过（3.10）：装着 3 份番茄酱的厨锅拆掉，背包里是一口带 `extraId` 和"装有3份：番茄酱"的厨锅，没有散落的番茄酱、没有多掉一口锅；
  右键放回去预览槽里还是 3 份。没核对的：活塞推厨锅（脚本摆的活塞没伸出来，没测成）、爆炸、悬停文字在界面里的样子。
- 没做：JE 的 `FoodServingRecipe`（带着菜的厨锅和碗一起放进合成格直接盛出一份）——基岩版的合成结果由客户端按配方 JSON 算，按物品数据变的配方写不出来；
  物品上的份数条（`isBarVisible`）；空锅的悬停文字"空"（方块物品没有地方写缺省的悬停文字）。

## 厨锅 / 煎锅下面的热源（对照 JE）

JE 的厨锅和煎锅都是 `HeatableBlockEntity`（FD 的 `isHeated`，java:15-36）：正下方一格是热源就热——标签 `heat_sources` = 岩浆块、熔岩炼药锅、炉灶、`tray_heat_sources`（熔岩、营火、火），
带 `LIT` 状态的要点着；正下方是 `heat_conductors`（漏斗；`create:chute` 是可选项，这个引擎上没有对应的方块名）时改看再下面一格，只往下看一格。
托盘（`SUPPORT = TRAY`，这边是方块实体模型的 `variable.mod_shelf`）只看正下方是不是 `tray_heat_sources`（`CookingPotBlock.getTrayState`、`SkilletBlock`），所以漏斗下面的火烧得热锅、不画托盘；
厨锅挂着吊把手时下面是什么都不画托盘（见"厨锅的支架"）。
这边（`Server/Helpers/Heat.py`，厨锅和煎锅经典 / 站点共用，`RefreshHeat` 把结果存进方块实体数据 `heatEnable`，站点和世界外观都读那份存着的）：

- 热源表还是对外联动契约的 `CanProvideHeatBlockList`（一个字没改：岩浆块是 `minecraft:magma`，营火看 `extinguished` 状态，点着的 `arris:stove` 在表里、熄着的孪生方块不在）；
  传热方块表 `HeatConductorList`（`Shared/Data/Cooking.py`，只有 `minecraft:hopper`）是新的，不在联动白名单里。
- 熔岩炼药锅：引擎里没有 `lava_cauldron` 这个方块（Strata 知识库的方块表：`minecraft:cauldron` 有 `fill_level` 0..6 和 `cauldron_liquid` = water / lava / powder_snow；`lava_cauldron` 只剩在原版资源包的
  `blocks.json` 和旧版方块号 465 里），所以不能按名字进表，`IsHeatSource` 读状态：`cauldron_liquid` 是 lava 且 `fill_level` 大于 0（倒空了的不算）。
  **手持煎锅（`SkilletHand`、`Client/Input._nearHeat`）仍认不出它**：那条路只读方块名，客户端又读不到方块状态（`GetBlockStates` 只有服务端有），
  只改服务端会让客户端放过"吃"、服务端却在煎，所以没做。
- 状态变了怎么知道：邻居事件只来自相邻的方块，正下方变了（放漏斗、拆漏斗、点着 / 熄灭正下方的营火）有原来的处理函数（`OnCookingPotNeighborChanged`、`OnSkilletNeighborChanged`）；
  热源在漏斗再下面一格时那一格变了没有事件，`Server/HeatConduct.py` 对"正下方是漏斗"的锅 / 煎锅每 0.5 秒（真实时间，`Pacer`）重算一次，
  和存着的不一样就把一个"正下方变了"的 `BlockNeighborChangedServerEvent` 交给那两个处理函数（存状态、同步客户端、煎锅断热时重置计时，一个字不抄）。下面不是漏斗的什么都不查。
- 测试：`tests/test_heat_sources.py`（JE 标签里每一种热源、看着像但不热的、漏斗传热、托盘只看正下方）、`tests/test_heat_conduct.py`（真的 `Skillet` / `CookingPot` 处理函数 + 假引擎）。

待实机验证（离线 + 假引擎核对过，没进过游戏）：

1. 熔岩炼药锅：往炼药锅里倒一桶熔岩，上面放厨锅 / 煎锅，要热；用桶把熔岩舀走（炼药锅变空），要凉。方块状态的名字和值（`cauldron_liquid` = lava、`fill_level` 6）是 Strata 知识库的方块表给的，
   没在游戏里读过；如果游戏里熔岩炼药锅是别的名字（比如还有 `minecraft:lava_cauldron`），`Heat._holdsLava` / `IsHeatSource` 一处改。
2. 漏斗：营火 / 炉灶 / 熔岩 / 岩浆块 / 熔岩炼药锅 → 漏斗 → 厨锅（再换煎锅），锅热、没有托盘；用水浇灭营火、铲子熄炉灶、拆掉火，约半秒内锅凉；再点着又热。
   一格一格读的自检：`Server/Debug/McdkHeatTest.mcdk_test_heat_probe(x, y, z)`（方块名、状态、`IsHeatSource`、`IsHeated`；锅 / 煎锅那一格再给存着的 `heatEnable` / `shelfEnable`，
   和 `Heat.IsHeated` 现算的对照），用法在文件开头的说明里。

## 厨锅的支架：吊把手、托盘（对照 JE）

JE 的 `CookingPotBlock` 有方块状态 `support`：`none` / `tray` / `handle`（`CookingPotSupport`）。
- 放下时（`getStateForPlacement`，java:117-120）：点的是方块的**下面**（锅挂在天花板下面）是吊把手，否则正下方是托盘热源（`tray_heat_sources`：熔岩、营火类、火）是托盘，不是就没有；
- 邻居变了（`updateShape`，java:128-130）：吊把手不动，别的按正下方重算（所以挂着的锅下面有火也不画托盘，但照样被烧热：`isHeated` 不看支架）；
- 潜行 + **空手**右键（`use`，java:71-74）：吊把手切回按正下方算的托盘 / 没有，别的切成吊把手，响一声挂灯（`LANTERN_PLACE` 0.7 / 1.0）；不开界面、不盛菜。
  原版潜行时任何一只手拿着东西，方块的 `use` 根本不调（`ServerPlayerGameMode.useItemOn` 的 `isSecondaryUseActive && 手里有东西`），手里的东西照常用出去；
  HoD 的 `CookingPotStation.opens` 对潜行一律返回假（"Sneaking keeps the pot's handle toggle"），所以装了 HoD 潜行右键也只是切把手。

**玩家看到的变化**：厨锅挂在天花板下面放（点方块的下面）会带吊把手；潜行空手右键锅，吊把手和托盘 / 没有来回切（响挂灯声）。**潜行空手右键不再开经典界面**
（原来前置包在场时是那样开的）：装了前置包，经典界面只剩 HoD 配置里关了 `cooking_pot` 站点一条路，和 JE + HoD 一样；没装前置包时普通右键照旧开它。
潜行并拿着东西（含副手）右键没有变：手里的东西照常用（放方块……），不盛、不开界面。

这边（规则 `Shared/Rules/PotSupport.py`，服务端 `Server/PotSupport.py`）：
- **状态**存在方块实体数据：`handleEnable`（1.0 挂着 / 0.0 没挂；没有这个键 = 没有吊把手：`/setblock`、结构放出的锅没有放置事件）和 `shelfEnable`（托盘，`Helpers/Heat.RefreshHeat` 按正下方和 `handleEnable` 算，
  挂着时恒为 0）。没有新的方块状态，方块 JSON 没动。
- **放置**：`ServerEntityTryPlaceBlockEvent` 的 `face`（`Facing.Down` = 0 = 点的是方块的下面）在放置前由 `OnTryPlacePotAgainst` 按位置记一笔（5 秒过期；同一格放置失败又换个面再放，用最后一次的），
  方块实体建好（`ServerPlaceBlockEntityEvent`，`CookingPot.OnServerCookingPotCreate`）时 `PotSupport.attach` 取走；没有记录的（活塞推来的带着旗，别的方式放的没有）不改已有的旗。
- **切换**：`Server/CookingPotHost.use`（dolorContainer 方块宿主，库在 `ServerBlockUseEvent` 里先问宿主）：潜行时调 `PotSupport.toggle`，主手副手都空着才切（库的缺省规则 `sneakPasses` 已经把主手有东西的放过，
  副手有东西的 JE 也不调 `use`，这里返回放过）；共用 0.2 秒的交互冷却（JE 按住右键也是每 4 刻一次），创造模式也切。
- **模型**（`rp/models/entity/cooking_pot.geo.json` 的 `handle` 骨骼）：FD 的 `cooking_pot_handle.json` 那一组（hoop、两片侧面、顶上一条，贴图 `cooking_pot_handle.png` 贴在 `cooking_pot.png` 的 (0, 40) 起 16 x 16 处），
  `variable.mod_handle > 0.5` 才画（渲染控制器的 `part_visibility`），实体 JSON 初始化为 0。托盘 `shelf` 骨骼和 `mod_shelf` 不变。
- **同步给客户端**：变的时候 `RefreshHeat` 直接推 `mod_shelf` / `mod_heat` / `mod_handle`（有 `handleEnable` 这个键才推，煎锅没有）；方块实体加载时 `Client/BlockEntityRestore` 按存档补；
  世界外观广播（`Server/PotLook`，前置包在场时）带 `support`（`PotSupport.NONE / TRAY / HANDLE` = 0 / 1 / 2，进 `potLook` 镜像时 0 不写），客户端 `PotScene` 每帧交给 `PotModel.support`，
  所以方块实体被引擎无事件重建（进世界十来秒后会有一次，变量回到初始值）时，`PotModel.check()` 发现后吊把手和托盘跟着别的值一起重推。没有前置包时没有场景，重建后要等下一次邻居事件 / 加载才补。
- **测试**：`tests/test_pot_support.py`（放置、邻居、切换、冷却、手里有东西、世界外观）、`tests/test_pot_support_model.py`（模型文件、场景推给模型、重建后重推、加载时补）、
  `tests/test_pot_support_open.py`（站点登记保留潜行不开站）。
- **没做**：JE 托盘状态的碰撞盒（`SHAPE_WITH_TRAY`：方块下面多一块 1 像素的板）——自定义方块的碰撞盒不能伸到方块外面，托盘只是画出来；吊把手的描边（悬停描边只有勺子有）。

待实机验证（离线 + 假引擎核对过，没进过游戏；改了几何 / 实体 / 渲染控制器 / 贴图，要完整重启）：

1. 对着天花板（方块下面）放厨锅：长出吊把手（一个 14 像素宽的框、顶上一条横梁，穿过锅口中间）；对着地面 / 侧面放没有。
2. 潜行空手右键：把手出现 / 消失，响挂灯声，不开界面；锅放在营火 / 熔岩 / 火上：切回来是托盘，再切又是把手（把手盖着托盘）；拿着东西潜行右键什么都不切、手里的东西照常用。
3. 站点开着时（前置包在场）把手也在，镜头看锅口不被它挡得太多；别的玩家从远处走近、重进世界、进世界十来秒后都还有把手（`PotModel.check` 重推）。
4. 创造模式、按住右键（每 0.2 秒切一次）。

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

前置包的原版工作台站点（它的内容包 `Vanilla/`：桌上摆料、脚本合成）不发引擎的合成事件，上面两条（补还剩余物、拦砧板菜）挂不上去，所以登到它的接口上
（`Compat/Diegesis/TableHooksLink.py`，`serverApi.ImportModule("arrisDiegesisScripts.Vanilla.Server.TableHooks")`，接口说明在前置包的那个模块里，`API_VERSION` 1）：
- `table` 步骤（`TableServerLink`）登 `addRemainder(returns)`：成品对上 `Shared/Data/CraftReturns.py` 的无序配方就按 `Crafting.entryFor / returnsOf` 每份每格还一件、放回原格
  （前置包那边放不回进背包、再掉脚下），下游包在 `Food.shapedRecipeContainerDict` 登记的成品每份还一个（进背包）。
- `board` 步骤在登 `DishCrafts` 的同一个条件下（砧板站点登上了、`remove_crafting_recipes` 开着）登 `addVeto(dishVeto)`：九格是砧板菜的某条配方就拒，
  给玩家看的话是 `Tips.DISH_ON_BOARD`（语言键 + 中文，前置包的客户端按玩家的语言查本包语言文件里的键；`rp/texts` 的中、英两份都有这个键）。
- 那张工作台的配方书在客户端，不知道服务端拦了什么（前置包第 6 轮实机：砧板菜照样列出来，点了做才被拒）：客户端的 `table` 步骤（`TableClientLink`）
  用同一个条件——这一端 `board` 那一步登上了（步骤执行器的 `ctx.done`）、`remove_crafting_recipes` 开着——给它客户端的登记口
  （`clientApi.ImportModule("arrisDiegesisScripts.Vanilla.Client.TableBookHooks")`，`API_VERSION` 1）登 `addHidden(hidden)`：书给每条配方的成品 + 每格能放的几种，
  `DishStation.isDishRecipe` 判是不是砧板菜的某条配方（料一件对一格、只看名字，和 `isDishCraft` 同一张表；拦配方不拦成品，切片拼回整个派照列）。
- 接口不在（前置包太旧、没装它的内容包）或版本不够：都不登，那一端的 `table` 记成 `skipped`；接口在、条件不满足：什么都不登，记 `ok`。
  九格是前置包给的配方朝向的物品字典或 `None`，这两条规则只看有哪些原料。
  测试：`tests/test_table_hooks_link.py`、`tests/test_table_client_link.py`（规则）、`tests/test_presence_boots.py`（哪一步登什么）。

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
- 原版动物认农夫乐事的东西（JE `CommonSetup` / `RabbitsEatCabbageMixin` / 猫的 `TEMPT_INGREDIENT` / 狼吃 isMeat）：猫（两种鱼片）的吸引 / 驯服 / 繁殖 /
  喂小崽 / 治疗（一片回 1 点），鸡（两种种子、稻米）、猪（卷心菜、番茄）、兔子（卷心菜、卷心菜叶）的吸引 / 繁殖 / 喂小崽，鹦鹉（三种种子）的驯服，
  狼（十种肉）的繁殖 / 喂小崽 / 治疗（治疗量照原版狼 = 饱食度 × 2）。2026-11-26 起**不覆盖原版实体文件**，照森罗物语（厨房）的做法运行时加组件
  （`Server/AnimalFood.py`，规则 `Shared/Rules/AnimalFood.py`，数据 `Shared/Data/Mobs.ANIMAL_FOOD`；离线 `tests/test_animal_food.py`，实机 `Server/Debug/McdkAnimalsTest.py`）：
  - 读哪份定义：经 `Server/Helpers/PackJson.read`（引擎内部的 `server_resource`）读 `entities/<短名>.json`，几个包都有这个路径时是包栈里优先级最高的那份
    [推断：照 `LoadServerFile` 的反编译，没实测两份同路径]；identifier 对不上（别的包在这个路径放了别的实体）时退一步列 `entities/`（子目录也进）找。
    第一次碰到这种动物时读、按类型记着，读不到 / 看不懂这只动物不做，记一次日志不再试。去掉注释和对象 / 数组末尾多余的逗号再解析。
  - 补什么：定义里凡是带这个组件的地方（顶层 `components` 或哪个组件组）都在列表末尾追加本包的条目（已经有的不重复加），别的字段原样；
    组件在哪、哪些事件会加减这些组件组（连 `trigger` 转过去的）都从定义里读，不写死。
  - 什么时候打：实体出现（`AddEntityServerEvent`，读档、区块加载也来）之后、定义里那些换组事件（`EntityDefinitionsEventServerEvent`：出生、长大、驯服……）之后，
    都晚一拍（`AddTimer(0)`）——加减组件组下一帧才生效，换组以后组件回到定义里的值（森罗物语实机复现过）。打的时候读 `GetEntityDefinitions` 的定义栈，
    照引擎的折法（后加的组盖掉同名组件；减组拿掉组里有的组件，连顶层同名的一起）只下发实体**现在真有**的组件、用它现在那个出处的值：
    给成年的加 `ageable` 会让它重新能长大，野猫的 `tempt` 用驯服猫那组的值也不对。定义栈读不懂时只下发顶层的。
  - 和别的包怎么共存：别的包整份覆盖了这只动物（同路径），我们读到的就是它那份，在它上面追加；别的包用别的文件名覆盖同一个 identifier 时，
    我们读到的还是 `entities/<短名>.json`（多半是原版），下发的几个组件会盖掉那个包对这几个组件的改动。两个模组都用 `AddActorComponent` 改同一个组件时，
    引擎按组件名替换（官方文档："重复添加会覆盖原有的值"），后打的赢——和森罗物语（它补鸡的 tempt / ageable / breedable）同时装时，鸡只认后打的那一家的种子 [没实测]。
  - 代价：每次下发 `behavior.tempt` 这种 AI 目标组件，实体的 AI 目标整套重建（Strata 引擎研究 GOAL_ENGINE §7）；重新加上的组件状态清零（ENT-04）。
    读档 / 区块加载每次都重打（照森罗物语）；`AddActorComponent` 加的组件随存档存进 `neteaseComponents`，读档以后要不要重打没实测。
  马、驴、骡被马饲料吸引、狼的讨食和马 / 狼的喂食记号还是 `Shared/Data/Mobs.py` 里写死的 JSON 串、在实体出现时加（`horseComponentsDict` / `wolfComponentsDict` 是联动契约）。
  村民没做：拾取（`shareables`）是数据，但要整份覆盖很大的 `villager_v2.json`，JE 的 `FOOD_POINTS`（作物算几点繁殖食物）在基岩没找到对应的数据。
- 覆盖原版文件（农民与流浪商人的交易表）：附加包里同路径的文件整份替换原版、不合并，所以是"原版整份拷来，只在列表末尾追加"，
  由 `tools/gen_vanilla_overrides.py` 生成；`tests/test_vanilla_overrides.py` 找得到本机原版行为包时逐字比对，游戏升级后原版变了就失败，重新生成即可。
  整份覆盖的两个风险：玩家的游戏比开发机新时，原版的改动被旧拷贝盖住，要等农夫乐事重新生成、重新出包；别的包也覆盖同一个原版文件时只有一份生效（按包的先后）。
  不覆盖文件给村民加交易的路没找到：网易没有加交易的接口；`AddActorComponent("minecraft:economy_trade_table", …)` 引擎会当场加载那张表
  （Strata 引擎研究 11_entities §8.2），但那是换整张表（还得是我们自己的一整份拷贝）、换职业的组件组时又被盖回去，不比覆盖文件好。
- 时运（`Server/FortuneDrops.py`，规则 `Shared/Rules/FortuneBonus.py`）：基岩的战利品表没有时运，方块被玩家打掉（`DestroyBlockEvent`）时按手上工具的时运等级
  （`enchantData` 编号 18）在方块中心补掉。JE 那 11 张表照搬：熟卷心菜的种子、熟洋葱 binomial（补"等级"次、每次 4/7），熟番茄 / 番茄藤 0..等级 个，
  六种野生作物和沙地灌木 0..2×等级 个；剪刀（原版剪刀或引擎说 itemType 是 shears 的）打野生作物不补，沙地灌木只在真掉了种子时补，创造模式不补。
  沃土上的原版作物照基岩原版作物的时运——2026-11-26 实机量的，不是 JE 的公式：小麦种子、甜菜种子每级多掷 1 次，胡萝卜、土豆每级多掷 2 次，每次 8/15。
- 战利品箱：JE 的 `add_loot_table` 在基岩版没有对应物，同路径文件又是整份替换，所以 `ChestLoot.py` 在 `OnContainerFillLoottableServerEvent` 里追加；
  表名是基岩版原版文件名（`shipwrecksupply` 不是 `shipwreck_supply`）。JE 里菜刀和煎锅的 `set_damage` 没搬（掉出来是满耐久）。
- 离线测试服务端模块：`tests/fakeengine.py` 把 `Server/Helpers/Engine.py` 换成假的，真正的 Helpers 和玩法模块跑在它上面。

待实机验证（写完这一版时没进过游戏）：

1. 右键驯服的马 / 驴 / 骡 / 羊驼 / 骷髅马 / 僵尸马拿马饲料、右键驯服的狼拿狗粮：回满血、状态效果各 5 分钟、扣一个（狗粮还碗）；
   对着驯服的狼右键时玩家不会开始吃狗粮（`bribeable` 记号是否让引擎当作"可用"，按钮写"喂食"）。不行的话右键事件根本不来，需要换记号组件。
2. 用刀右键原版蛋糕：不再吃蛋糕、掉一片蛋糕片，`bite_counter` 读写正常；插蜡烛的蛋糕变成少一片的蛋糕并掉出蜡烛。用刀拆派 / 蛋糕 / 南瓜掉的切片数。
3. 用刀杀着火的猪 / 疣猪兽掉烟熏火腿；抢夺等级是否读得到。
4. `OnContainerFillLoottableServerEvent` 的 `loottable` 字符串长什么样（`Rules.ChestLoot.tableKey` 兼容几种写法）、追加的物品进了箱子。
5. 引擎采用了两张交易表（农民收洋葱、流浪商人卖种子）；六种动物运行时加的组件生效（`Server/Debug/McdkAnimalsTest.py`：读到定义没有、
   定义栈长什么样、`GetComponents` 里带没带本包的物品、真喂一次繁殖 / 驯服 / 长大 / 回血、长大以后再读）。
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
  `attack_damage` 7（`netease:weapon.attack_damage` 加在玩家基础 1 点之上，实际 8 = JE；2026-11-26 实机：铁刀写 4 时打猪掉 5 点、空手掉 1 点，
  五把刀因此各减 1：燧石 2、铁 3、金 1、钻石 4、下界合金 5，总伤害是 JE 2.5 / 3.5 / 1.5 / 4.5 / 5.5 向上取整，`tests/test_knife_values.py` 钉着）、提示改成 JE 的"潜行可放置"
  （`netease:customtips` 是整段悬停文字的格式串，所以后面补了 `%enchanting%%attack_damage%`，不然附魔和攻击伤害两行可能被盖掉）。
- 放置：`SkilletItem.OnUseSkilletItem`（`ServerItemUseOnEvent`，优先级 98.5）只有潜行才放，不潜行直接拦下（不让 ItemToBlock 当普通方块物品放，也不取消引擎的 `ret`，
  右键箱子照样开箱）。放置本身仍调 `ItemToBlock.OnPlaceItemAsBlock`；放好后把那件煎锅（`SkilletRules.storeItem`：名字、附加值、耐久、附魔、提示、额外 ID、用户数据，
  元组换列表、py2 的 unicode 换 str）记进方块实体数据 `skilletItem`，方块实体还没建好就先挂在待办里，等 `ServerPlaceBlockEntityEvent` 再写。
- 拆掉：方块的战利品表改成空的（`air_loot.json`），`Skillet.OnSkilletRemove`（`BlockRemoveServerEvent`）调 `SkilletItem.dropStored` 掉出存着的那件；
  创造模式在 `ServerPlayerTryDestroyBlockEvent` 记一笔（`SkilletRules.BreakMarks`，按位置、5 秒过期），方块真没了时认这笔记录不掉煎锅；
  没存过的（/setblock、旧存档）掉一把新的。方块的火焰附加读 `skilletItem`，`Skillet._timerStart` 换成倒计时起点（秒数 + 1）。
- 含水的煎锅（液体层 `GetLiquidBlock` 有水）：放食物提示"被水泡着可没法烹饪啊……"，锅里已有的东西浮出来（JE `cookingTick`）；
  放非食物仍是"这东西可不能被烹饪……"（JE 先查配方，所以泡着水也先报这句；锅里有东西时同样报）。
- 放下的煎锅（经典玩法）自己的嗞嗞声、蒸汽、火焰附加的星星（`Client/SkilletSteam.py`，概率和位置在 `Shared/Rules/SkilletSteam.py`，和炉灶的火同一种做法）：
  JE 的 `SkilletBlock.animateTick` 只有 `isCooking()`（加热着**而且锅里有东西**）才每次 1/10 响一声 `block.skillet.sizzle`（音量 0.4、音调 0.9~1.1），
  `SkilletBlockEntity.animationTick` 同样条件下每刻 20% 放一颗 FD 的蒸汽、带火焰附加每刻 `level * 5%` 放一颗 `ENCHANTED_HIT`（x、z 在方块中心 ±0.2，y + 0.1）。
  基岩版：方块 JSON 写 `netease:block_animate_random_tick`（trigger_rate 1，嗞嗞声）和 `netease:block_entity.client_tick`（每秒 20 次，蒸汽 / 星星；
  client_tick 是方块实体的标志，**这一版之前放下的煎锅要重新放才有蒸汽**，嗞嗞声是方块级的组件、旧锅也有）；"加热着"读方块实体模型的 `mod_heat`、
  "锅里有东西"读 `Client/BlockItems` 记着的内容、火焰附加读方块实体数据里记着的那件煎锅；场景接管（`mod_scene` 为 1）时不放，声音和烟是煎锅场景画的。
  粒子 `arris:skillet_steam`（FD 的 `SteamParticle`：半边长 0.2~0.4、活 4~6.45 秒、每秒升 0.1~0.34 格、alpha 0.6 最后 1.5 秒淡掉）和 `arris:skillet_spark`
  （`CritParticle` 的附魔色：速度 0.4 倍、摩擦 0.7 每刻、重力 0.02 格每二次方刻）是本包自己的（经典厨锅的蒸汽 `arris:steam` 是同一个 `SteamParticle`，见下一条）。
  原来实体定义里的嗞嗞动画（只要在热源上就每 15 秒响一声，空锅也响、没有蒸汽）删了。
- 经典厨锅（没有站点）的蒸汽：实体动画 `animation.cooking_pot.smoke` 每秒（JE `CookingPotBlockEntity.animationTick` 每刻 5%，平均每秒一颗）在模型的 `steam` 定位点（方块中心、离底面 8 像素 = JE 的 `pos.y + 0.5`）放一颗 `arris:steam`。
  它和煎锅的蒸汽是同一个 FD `SteamParticle`（速度、寿命、大小、渐隐、重力、挑图、光照一样，`tests/test_pot_steam.py` 逐项对），只有起点不同：锅的 x、z ±0.2 和 Factory 的 +0.3 写在粒子里，煎锅的 x、z 由脚本掷。
  JE 在 `steam.json` 的 12 张图里每颗随机挑一张（`pickSprite`）：十二张图叠成一张 `rp/textures/particle/arris_steam.png`（16 x 192，和 JE 的 `steam_0` 到 `steam_11` 逐像素一样），
  UV 的纵向写 `math.floor(variable.particle_random_2 * 12) * 16`（原版营火烟也这么挑图；大小用随机数 1，两个量各掷各的，和 JE 一样）。JE 的蒸汽有碰撞（`Particle.move`，`hasPhysics` 缺省为真，`setSize(0.25, 0.25)`）：顶到方块就停在下面、到寿命才淡掉。
  2026-11-19 起两种蒸汽（`arris:steam`、`arris:skillet_steam`）用引擎的粒子碰撞 `minecraft:particle_motion_collision`（半径 0.125、不弹、`collision_drag` 10 即碰上很快停住、不因为碰到而消失），
  原来是「离开锅和空气就消失」（`particle_expire_if_not_in_blocks`）：锅上面盖着方块时蒸汽一进去就没了。起点减去半径在锅的碰撞盒顶上面，不会一出来就卡住（`tests/test_pot_steam.py`）。
  没做的：横向每刻的随机游走（走完一生约 0.07 格）。实机（2026-11-19，3.10.0.467018）只核过改完的两个粒子建得出来、日志没有报错；停在方块下面的样子没看。
- 经典厨锅（没有站点）的气泡：同一个 `animationTick`（`CookingPotBlockEntity.java:244-251`）只看加热着，每刻 20% 的概率在方块中心 x、z 各 ±0.3、`pos.y + 0.7` 放一颗原版的 `ParticleTypes.BUBBLE_POP`、初速 0。
  实体动画 `animation.cooking_pot.bubble` 每 0.25 秒（每秒 4 颗 = 每秒 20 刻 x 20%）在定位点 `blister`（11.2 像素 = `y + 0.7`）放一颗 `arris:bubble_pop`（`rp/particles/arris_bubble_pop.json`），
  x、z 的 ±0.3 在粒子里每颗各掷。基岩版的粒子没有按刻掷骰的办法，所以和 JE 差在节奏：平均一样，这里间隔是匀的；条件同蒸汽（`mod_heat` 加盖着、没有站点场景接管，站点里的气泡是它自己的）。
  粒子是原版 `BubblePopParticle` 的样子（1.20.1 的字节码核对过）：活 4 刻、看得见 5 刻，五张图各一刻（原版 `bubble_pop_0` 到 `4`，叠成 `rp/textures/particle/arris_bubble_pop.png` 16 x 80，
  `tests/test_pot_bubble.py` 在有 JE 客户端 jar 时逐像素对），每刻先加重力 0.008 再动、没有摩擦（连续写法：初速 0.08 向下、加速度 3.2，每一刻的位置和 JE 对上），
  半边长 0.1~0.2（`SingleQuadParticle` 的构造）、不透明（`PARTICLE_SHEET_OPAQUE`，所以材质是 `particles_alpha`）、跟着方块所在的光照。原来的 `arris:bubble`（老贴图集里的水泡，飘 2~3 秒、
  每两秒放一秒、一秒 5 颗）和它独占的贴图集删了。没做的：气泡碰到方块停住（`Particle.move` 的碰撞；它从锅沿上方 0.075 格放、只落 0.08 格，看不出）。粒子、实体动画、模型、贴图都改了，没进过游戏，要完整重启后看。
- 手持烹饪（`SkilletHand`）：JE 的 `SkilletItem.use` 两只手都认（煎锅在哪只手，原料就在另一只手）。**基岩版的副手只收引擎允许的那几种物品，生肉放不进去**（实测 `SetEntityItem(OFFHAND, 生牛肉)` 返回 False），所以这边常用的是反过来拿：煎锅放副手（物品 JSON 开了 `netease:allow_offhand`）、原料拿主手，这时在热源旁按住右键是煎不是吃——客户端在 `ClientItemTryUseEvent` 里取消"吃"（`SkilletHandRules.cooksInsteadOfEating`：副手煎锅、主手有营火配方、身边 3x3x3 有热源；JE 里饿着的时候主手的食物会先被吃掉，这里改成有热源就煎，不然基岩版饿着就没法手持煎东西了）。下面说的"副手食物"换成这种拿法就是主手的那件。
  基岩版没有"按住使用"的服务端事件，由客户端在主手或副手拿着煎锅时报告右键：`RightClickBeforeClientEvent` 报一次，按住期间 `OnScriptTickClient`
  每 0.2 秒报一次，`RightClickReleaseClientEvent` 报松开（`Client/Input.py` + `SkilletHandRules.HoldReporter`，RPC `SkilletUseHeld`）；服务端按最后一次"按着"的时间判断还按不按着
  （超过 0.8 秒没消息就当松手）。每次"按着"没有在煎的话就是 JE 的 `use()`：主手煎锅，着火或脚下 3x3x3 有热源（只看方块名，不看营火 / 炉灶点没点着，与 JE 一致），
  副手食物在 `CanCookedFoodDict`（= JE 营火配方 16 条，补上了海带），头没泡在水里（脚 + 1.62 那一格的液体层）→ 开始；副手没食物 / 不能煎提示"用另一只手拿着原料！"，
  泡在水里提示"在水里可没法煎啊……"，没热源什么都不说；潜行时不提示（潜行右键方块是放煎锅，JE 那一下不走 `use()`）。按满 6 / 4 / 3 秒做好：副手少 1 件（创造模式也扣，JE 就是这样）、
  成品进背包（`GiveOrDropItem`，满了掉脚下）、不磨损煎锅；中途松手、换主手物品、掉线什么都不做——食物到做好那一刻才从副手拿走，所以不会丢东西
  （JE 是开始就拿走、松手放回背包）。按住不放，下一次"按着"的报告接着煎下一件（JE 按住右键每 4 刻重新使用）。滋滋声每刻 1/50（每 0.25 步 9.6%），只发给自己（JE 是本地声音）。
  **翻面**（`SkilletItem` 的 `FLIP_TIME = 12`、`FlipSkilletMessage`、`KeybindEvents`）：按住右键煎的时候点一下左键，客户端（`Client/Input.OnLeftClickDown`，只在右键按着、手里拿着煎锅时）报一个
  `SkilletFlip`（`Server/SkilletHold`，玩家是注入的），服务端（`SkilletHand.onFlip`）核对真在煎、不在翻（JE 的 `FlipTimeStamp` 记着时再点不算），13 刻（0.65 秒）后
  响一声下料（`ambient.skillet.addfood`，音量 0.4、音调 0.9~1.1、位置是玩家脚下 x / z 各加 0.5、`Call(*)` 所有人听得到，JE 是服务端放的声音）；翻的过程中松手、做好了就不响（JE 的 `onUseTick` 只在使用中才走）。
  JE 的 `Flipped` 记号只管手里那只锅的画面，这里没有对应的东西，不记。
- 耐久：`ItemDurabilityChangedServerEvent`（`ModServer` 新挂的监听）里 `SkilletRules.wearAfter`：一次磨损超过 1 点就改回 1（基岩版自定义武器打一下磨损 2 点，原版剑 1 点），
  修复不动，引擎说不能改（`canChange` 假）时不动。**挖方块不另外扣**：引擎对自定义物品挖方块是扣 0 点还是 2 点这里没法核实，加一道脚本扣可能重复，
  所以交给引擎（扣 2 点时上面的夹取会把它压成 1 点）。
- 打人：JE 的攻击速度 0.9 次 / 秒、冷却不够伤害变小、击退 +1，基岩版都没有（没有攻击冷却；`DamageEvent` 只能开关击退，`SetMobKnockback` 的方向约定离线核不了，所以没做击退）。
  只保留 JE 的声音分档：`PlayerAttackEntityEvent` 里按距上次挥煎锅的时间挑 `attack_strong`（够 0.8 × 22.2 刻 ≈ 0.89 秒）或 `attack_weak`（音量 0.8、音调 0.9，
  `sound_definitions.json` 里补了定义）。JE 里切物品也会重置冷却，这里不管。
- 没做：JE 的进度条（客户端物品装饰，基岩版画不了）、翻面的画面（手里的锅翻一下，物品模型是静态的；翻面的**声音**做了，见上）、煎锅里的食物在手上的渲染、同种食物往锅里叠加（`ItemStackHandler.insertItem`，现在锅里有东西就不收了）、
  手持煎锅认不出熔岩炼药锅（基岩版是 `cauldron` 加 `cauldron_liquid` 状态，手持这条路只读方块名、客户端读不到方块状态；放下的煎锅 / 厨锅认得，见"厨锅 / 煎锅下面的热源"）、含水放置（现在只往空气里放）。

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

## 煎锅 / 炉灶上东西朝上那面的熟色（联动时，对照 HoD）

JE 依据：Hands-On Delight 的 `SkilletBehavior.drawPiece`（327 行）/ `StoveBehavior.draw`（206 行）给整件 `node.setTint(KitchenLooks.fryingTint(shown, cooked(shown), shownUp, SEARED, SEAR))`，
Diegesis 的 `TintedConsumer` 把整件体素模型每个顶点的颜色乘上它；朝上那面每 1/12 才重画（`look`）。朝上那面没熟时画生的图、从白往"熟的主色 / 生的主色"走
（逐通道相除、封顶 1），肉和鱼（`food.isMeat() || ItemTags.FISHES`）先往焦色 `0xB8875C` 走 4 成，最多走到七成（`SEAR` 0.7）；熟了（up >= 1）换成熟的图、不染。
两面食材只有厨师没等贴锅 / 贴灶那面熟透就翻过来时，朝上那面才是半熟；蛋（HoD 的 `cracked`，`PanStation.isCracked` 认 `PotSunk.CRACKED`）是从透亮清成白，
这边早就做成了预染色的显示物品（`Shared/Rules/EggLook`），不归这一节。只煎一面（`one_sided`，`OneSidedList`）的不一定是蛋：下游追加进去的从下往上煎透，朝上那面跟着熟，照这一节染。

这边（只在联动时，场景模块本来就只在联动时导入）：
- 颜色：`Shared/Rules/FryingTint.tintOf`——生熟两张图的主色查 `Shared/Data/BrothColors.MainColors`（JE 的 `FoodColors.main`：色相分 12 份取最大一族，
  不是砧板碎屑 / 汤色用的 `FoodColors.sample` 加权平均；`tools/gen_broth_colors.py` 把营火配方的每件和它煎熟的样子都收进来，原来缺海带），
  肉是 `Shared/Data/PotPieceTraits.MEAT`（JE 的 isMeat），鱼是新表 `Shared/Data/Fishes`（JE 1.20.1 原版标签 `minecraft:fishes`：生熟鳕鱼、生熟鲑鱼、河豚、热带鱼；
  农夫乐事的鱼片不是肉也不在这个标签里，所以 JE 里鱼片不带焦色，这边一样）。下游经联动契约往 `CanCookedFoodDict` 追加的东西 JE 运行时从图标现算，这边没有贴图、
  表里没有：不染。
- 画法：客户端掉落物本身染不了色。每件要染的、躺着不动的食物，在它朝上那面上叠一颗粒子 `arris:fry_tint`（`rp/particles/arris_fry_tint.json`：平躺的
  `emitter_transform_xz`、`particles_blend`、贴图 `atlas.items`，图标在图集里的位置由 `GetIconInfo` 给，颜色 / 不透明度 / 半边长 / UV 是变量，带
  `particle_appearance_lighting` 跟环境光），一颗活到被删（前置包影子 `Client/Shade.py` 的做法）。整件乘上 c 用普通的 alpha 混合近似（`FryingTint.overlay`）：
  不透明度 a = 1 - min(c)、颜色 q = (c - min(c)) / a，叠出来 (1 - a) + a·q = c；c 是白时什么都不画，偏差只和染的深浅成正比。
- 摆法（`Shared/Rules/TopOverlay`）：粒子的轴和掉落物的轴一一对上（图标右 = 掉落物的 -X、图标上 = +Y、法线 = 正面 -Z，发射器朝向 E = M·P，SetRot 按
  `Rz·Ry·Rx` 分解；平躺朝上时只转 y），位置在贴图正中沿法线抬 `TOP_FACE`·缩放 + `LIFT_MARGIN`，半边长 = 7.2 像素·缩放 / 2。掉落物的厚度照 Strata 引擎知识库
  ITEM_RENDER_ENGINE §3–§4：逐像素挤出一个贴图像素厚、从轴心平面往正面那边挤，所以平躺朝上时顶面在中心平面上方 7.2 / 16 像素·缩放；`LIFT_MARGIN` 0.1 像素
  （不能是 0，见下面的实机）。受光：物品材质按法线算明暗，朝上的面系数正好是 1（实体着色器的 `_lightIntensity`），和带 `particle_appearance_lighting` 的粒子
  乘的是同一处的光。只给平躺朝上的件：锅里、烤架上停着的件都平躺朝上，斜着的只在半路上（那时收着）。
- 什么时候亮（`TopOverlay.Stillness`、客户端 `Compat/Diegesis/FryTints`）：掉落物的位置按游戏刻插值、晚到一两帧，粒子不晚，所以掉落物的样子一变（落下、颠起、
  翻面、挪位、换大小）粒子就收着（不透明度 0），连着 0.1 秒（两个游戏刻）没变才摆好、亮出来；熟了换成熟的图、朝上那面还生、件拿走、换了东西、场景收掉
  （方块没了、重建、炉灶转向、换维度）就删。`PanScene.frame` / `StoveScene.frame` 每帧把要染的件交给 `FryTints.TopTints`；没变的不碰引擎（歇着的锅照样只剩核对）。
  进世界头几秒 `GetIconInfo` 回 None、`Create` 回 0：那时不画，之后再试；老引擎没有 `GetIconInfo` 一件都不染；物品类型是方块的不叠。
- 和 JE 不一样的：只染朝上那面的顶面（JE 连底面、四边一起乘）——染得深的档看得出来：鸡肉朝上 11/12（a ≈ 0.42）时挤出来的侧面还是生肉的粉色；
  动着的时候不染（JE 飞着、翻着也染着）；斜着看时叠层远边比顶面多出一圈很细的视差边（那 0.1 像素的余量）。
  `tests/test_frying_tint.py`（颜色）、`tests/test_top_overlay.py`（摆法、停稳、余量不为 0）、`tests/test_fry_tints.py`（接线、假引擎）守着。
- 实机（2026-11-22，自己的会话 tint，3.10.0.467018；检查脚本 `d:/tmp/mcdk-multi/checks/tint_*.py`，截图 `shots-1122/tint_*.jpg`）：
  - 引擎认 `arris:fry_tint`（`Create` 回非 0）；营火配方 32 件（生的、熟的）`GetIconInfo` 都有（宽高 1/64）；`itemType` 食物是 `food`，蛋和海带是空串
    （海带不是方块物品，掉落物就是普通的平面贴图，照染）。
  - 对齐：凉锅里的生牛肉、黑叠层（a 0.6）俯视、斜 30° 看都和顶面严丝合缝；斜 30° 时叠层远边比顶面多出 6 像素，按机位换算正好高出 0.10 像素 = `LIFT_MARGIN`，
    顶面就在 `TOP_FACE` 上（知识库推的挤出方向实测成立）。余量 0 不行：一块翻过面的牛肉上叠层整块被顶面吃掉；0.1 在试过的姿态都不被吃；视差边宽度和余量成正比
    （1.4 格外俯 30°、夸张的黑叠层：0.1 约 7 像素、0.05 约 4、0.02 约 2），真实颜色下几乎看不出，远处的深度精度没量成（`SetFov` 最小 30°），所以不往下压。
    炉灶四个朝向（aux 0–3，场景朝向 180 / 270 / 0 / 90）都盖得严；斜 30°、60° 的牛肉上按 `emitterEuler` 转的叠层盖住 99.1% / 96.5%：带俯仰 / 侧倾的 `SetRot` 就是 `Rz·Ry·Rx`。
  - 颜色和受光：生牛肉朝上 1/2 顶面被压到 (0.917, 0.938, 0.902)（c = 0.914, 0.933, 0.910），鸡肉 11/12 (0.878, 0.740, 0.583)（c = 0.874, 0.737, 0.577）：
    `particles_blend` 是普通的 alpha 混合。白叠层（q = 1、a = 0.6）叠上去的比值，白天、夜里只有天光（光照 4）、两座点着的炉灶照着、火把旁都是 1.000：粒子和掉落物顶面受一样的光。
  - 动：颠锅那一刻两颗一起收起（不透明度 0），落回去、停稳 0.1 秒后同一颗粒子按翻上来那面（0.6）的颜色再亮，转角跟着贴图转了 180°（`ItemPose.steadied`）；
    炉灶翻一件只收那一件，0.4 秒后按翻上来那面再亮。热锅里叠层和烟、油星一起画没有杂像；错误日志一条都没有。

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
- 拿绳子点绳子（`RopeAndNet.OnPlaceRopeOnRope`，`Shared/Rules/RopeExtend.py`，ServerItemUseOnEvent 优先级 98），照 RopeItem.updatePlacementContext：
  点到的格子（点到绳子就是它；点到实心方块是外侧那一格，草、水这些能顶替的就是它自己、和绳子无关）是绳子时，不潜行一律顺着绳子往下，
  第一格能顶替的（空气、水、草）放下，碰到岩浆或实心方块不放；潜行照点到的面放一格（朝下的面也顺着往下走，别的方向碰到绳子不放）。
  "点到实心方块、外侧那一格是绳子"只在潜行时认：JE 不潜行时先调点到的方块的 `use`（箱子、门、按钮……），这边没有"哪些方块自己会处理右键"的表，
  不潜行就照引擎原样；潜行时 JE 本来就不调方块的 `use`。认了的时候引擎自己那一格（点到的面外侧）一律取消；放下响 `dig.cloth`。
- 绳上的番茄藤（`Crops.OnCropNeighborChanged` / `OnVineRemoved`，`Shared/Rules/TomatoVine.py`），照 HangingTomatoBlock：下面是地上那株第 3 级起或另一节藤才撑得住；
  藤没了在原地放回绳子——四个藤方块带 `netease:listen_block_remove`，`BlockRemoveServerEvent` 来了下一刻看那一格，空气 / 水才放（长一级、摘果子是换成另一节藤，不放）。
  JE 的亮度条件（亮度 ≥ 8 或看得见天）没做。
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
- 点着的炉灶自己的火（`Client/StoveFlame.py`，概率和位置在 `Shared/Rules/StoveFlame.py`），照 FD 的两段客户端代码：`StoveBlock.animateTick`（java:38-55）点着时每次在正面
  （FACING 那一侧 0.52 处）随机高度 0 ~ 6/16、另一个水平方向 ±0.3 放一颗烟一颗火，1/10 的概率响 `block.stove.crackle`（FD 的 `sounds.json` 指到原版 `block.campfire.crackle`，音量音调 1）；
  `StoveBlockEntity.addSmokeParticles`（java:24-46，客户端方块实体每刻）灶上每件东西每刻 20% 的概率在头上（y + 1，位置同 `DefaultStoveRenderer` 画它的）冒 3 颗烟，
  HoD 的 `StoveSmokeMixin` 在炉灶站点显示时取消这一段。基岩版：点着的 `arris_stove.json` 写 `netease:block_animate_random_tick`（`trigger_rate` 1.0：动画刻每次轮到这座炉灶都发
  `BlockAnimateRandomTickEvent`，JE 也是每次轮到都放）和 `netease:block_entity.client_tick`（`ModBlockEntityTickClientEvent` 每秒 20 次，对上 JE 每刻一次）；熄着的孪生方块两样都不写（JE 都只在 LIT 时）。
  正面朝哪读 `Shared/Rules/StoveFacing`（aux 只经 `Placement.directionOfAux` 读），灶上哪几格有东西读 `Client/BlockItems.itemsAt`（经典展示记着的最后一份内容），
  炉灶站点登记了（`GrillClientLink` 这一步调 `StoveFlame.muteItemSmoke`，和 `StoveScenes.enable` 同一处）就不放灶上东西的烟，火口的火星和噼啪照放（`animateTick` HoD 不碰）；粒子离玩家超过 32 格不放（JE 的 `addParticleInternal`）。
  粒子是自带的 `arris:stove_flame` / `arris:stove_smoke`（`rp/particles`，照原版 `basic_flame` / `basic_smoke` 的外观，改成放一次出一颗）。
  JE 的 `animateTick` 离得近的方块每秒大约被轮到两三次，引擎的 `trigger_rate` 最高 1.0 时官方文档说 16 格内"几乎每秒触发一次"，所以火口的火星和噼啪的频率可能比 JE 低，实机看了再定（要加密只能一次事件放几对，`trigger_rate` 已经是上限）。
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
5. 炉灶的火（要完整重启游戏：`arris_stove.json`、两个新粒子）：站在新放的点着的炉灶旁，火口那一侧（四个朝向都试，包括从背面看）有火星和烟往上飘、偶尔营火噼啪声，熄着的炉灶什么都没有；
   `BlockAnimateRandomTickEvent` 的 `auxData` 是不是方块的朝向状态；火口火星的疏密合不合手感（对照 JE）。没装前置包（或 HoD 配置里关了炉灶站点）时灶上放生肉，每件头上一阵阵黑烟；
   装了前置包时那圈黑烟没有。`client_tick` 要新放的炉灶才有（旧存档里的炉灶没有灶上东西的烟，点火 / 灭火换一次方块后有）。

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
- 榻榻米方块（JE `TatamiBlock`）像床一样**两两配对**，不是连成一片的连接纹理：一对拼成一张两格长的榻榻米（接缝没有边框、席纹接得上），两头是正方形的单块，
  没配对的六面都是单块；每块只看 FACING 那一格，没有对角、也不看别的邻格。方块态 `arris:tatami_facing`（网易 Facing 枚举 0 下 1 上 2 北 3 南 4 西 5 东，
  缺省 0 = JE 的缺省 DOWN）+ `arris:paired`，规则在 `Shared/Rules/TatamiPair.py`。放下（`Server/TatamiPairs.py`；`EntityPlaceBlockAfterServerEvent` 的 `face`
  是点的那一面）：FACING = 点的面的反方向；玩家没潜行、点的是没配对的榻榻米时两块配对、FACING 互指；另一半不再是榻榻米时剩下那块拆开（邻格变化，
  FACING 不变；活塞推着走、还在路上的 `minecraft:moving_block` 不算没了——JE 推一整对时先落地的那块会把自己拆开，是 JE 的毛病）。
  样子全靠 permutations：`tools/gen_tatami.py` 照抄 JE 的方块状态和模型（顶点 UV、面的 rotation、方块状态的 x / y 转动）算出 12 个状态六个面各贴哪张图、
  转几个直角，换到基岩 `full_block` 的面坐标（底面和 JE 差 180°），写 12 条互斥的 permutation、转出 9 张转角图（3 张原图的 4 个转角都用得到）；
  改了 JE 数据或贴图就重跑，`tests/test_tatami_gen.py` 查生成物是不是最新的、抄的 JE 数据和 `.refs` 里的原文件对不对，`tests/test_tatami_block_look.py`
  把一对两块同一面的图按基岩的面坐标拼起来逐像素比 JE 的整张长垫。方块 JSON 是 1.21.90 格式（几何 + 材质实例的新管线），`blocks.json` 只留声音；
  战利品表 `loot_tables/tatami.json` 掉一个 data 0 的榻榻米（不写时掉的物品带着方块态的 aux）。
  旧存档：自定义方块态按名字降序从低位排进 aux，`arris:tatami_facing` 占低 3 位、`arris:paired` 第 4 位（实机 `GetBlockAuxValueFromStates`：aux = 朝向 + 8 × 配对），
  改成方块态之前放下的榻榻米（aux 是 direction 0..3）读出来都是没配对的；假日创造者实验玩法的存档里 aux 8 / 12 的会读成"配了对"，旁边一有方块变化就理顺。
  /setblock、结构放出来的是缺省状态（朝下、没配对）。实机核过（2026-11-18）：竖着、南北、东西三种配对的样子（接缝处没有线）、真右键放置配对、潜行放置不配、
  第三块配不走已经配了对的、拆一半另一半拆开、掉落、创造模式中键取方块（都是 aux 0 的榻榻米）、重启后方块态原样。
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

## 砧板和站点的几处补齐（2026-11-19，对照 JE）

- **板上插着的工具照 FD 的 `IsItemCarved` 认**（`CuttingBoardBlockEntity.isItemCarvingBoard`：只有 `carveToolOnBoard` 置真，`removeItem` 清掉）。原来靠推断（板上有、切不了、却是能插的工具），
  平常放上去的工具也会立起来。现在是方块实体数据里的 `isItemCarved`（`BoardStation.CARVED_DATA`）：1 插着 / 0 躺着 / 没有 = 不知道（板空着，或加这个标记之前的老存档——只有这时才照老办法推断，
  `BoardStation.Env.isCarving(item, flag)`）；读写在 `Server/Helpers/BoardDish.carvedOf / setCarved`。放上去写 0、插进去写 1、取回和切完最后一件清掉。站点的数据和世界展示的载荷里是 `carved`
  （`BoardLogic.setBoard(item, carved)`、`Helpers/BlockItems.PublishBoard(.., carved)`，客户端 `Client/BlockItems`；HoD 的 `BoardPlace.Placed.carved` 只有 `carve` 是真）。
  经典玩法补上了 JE 的 `ToolCarvingEvent`（`Server/CuttingBoard._carveWhenSneaking` / `carve`）：潜行着拿能插的工具（有材质等级的工具、三叉戟、剪刀）对着**空**板使用就插进去，响插工具的那一声，
  创造模式手里的留着；潜行拿着东西时引擎不发方块使用，所以挂在 `ServerItemUseOnEvent` 上。插着工具的板拿着东西点它什么都不做（放不上去、也切不了，JE 的 `canAddItem` / `processStoredItemUsingTool` 开头就返回），空手取回。
  实机（3.10.0.467018，`d:/tmp/mcdk-multi/checks/chk_batch1119.py carve`、`chk_carve_input.py`）：投递的 Shift 按住 + 右键，铁刀插进空板——标记 1、创造模式手里的刀还在、客户端画一件立着的、没有开站点；
  取回后标记清掉；平常放上去的铁剑躺着（标记 0）；区块卸载再加载标记还在、空板重新加载不报错。
- **蘑菇丛在砧板上、手上照 JE 平躺**：JE 里蘑菇丛的物品是一张平面图（`item/generated`，贴图是 stage3 那张方块贴图），这里它是自定义几何的方块，掉落物是缩小的立体小模型。另做了两件只用来显示的平面物品
  `arris:brown_mushroom_colony_look` / `arris:red_mushroom_colony_look`（图标就是 `textures/blocks/<颜色>_mushroom_colony_stage3`，不进创造栏；`Shared/Data/FlatBlockItems.ShownAs` 是对照表），
  砧板上的那一件画成它（`BoardStation.shownItem`：站点里 `BoardThing`、世界里 `Client/BlockItems._layoutOf`），手上的经前置包的可选钩子 `shownAs`（`Compat/Diegesis/FlatSprites`）。板上存的、取回的仍是蘑菇丛本身。
  实机：红蘑菇丛放上板，客户端画的是那件平面物品（平躺的两片），取回后没有残留。`tests/test_colony_looks.py`。
- **JEI 里的"砧板摆盘"分类**（HoD 的 `HandsOnJeiPlugin` + `AssemblyCategory`；`Compat/Jei/BoardAssembly.py`，纯规则在 `Shared/Rules/DishJei.py`）：只在联动着、砧板站点开着时登记
  （`JeiClient` 用 `HandsOnMode.whenDecided("client", ...)` 等判定）。一道菜一页：打底的那一样躺在板上（提示多一行"先放在砧板上"），别的层三个一排，箭头，成品；只差一个位置的几行并成一页、那个位置轮着显示
  （JE 的 `Ingredient`；`Dishes.DishList` 的 86 行并成 48 页）。界面是 `rp/ui/jei_farmers_delight.json` 的 `jeiBoardAssemblyRecipe`，位置照 HoD 的 `AssemblyLayout`。
  被拦的工作台配方（`DishCrafts`，配置 `remove_crafting_recipes`）同时从 JEI 里藏起来：arrisJei 新加的 `hideRecipes(藏的人, 配方种类, 判断)`（能力标志 `HIDE_RECIPES`；那一版之前的 arrisJei 上只多出分类、工作台配方照旧显示）。
  实机：分类登记上了；鸡蛋三明治的工作台配方藏起来了（不藏时 1 条）；苹果派两条里留下派切片拼回去的那条；配方页的控件在 `AssemblyLayout` 的位置上。
  限制：登记只做一次，下游之后才追加的摆盘菜不在 JEI 里（「联动契约与客户端的表」一节的限制里说的同一件事）。`tests/test_dish_jei.py`、`tests/test_jei_board_assembly.py`。
- **站点界面上的字按玩家的语言给**（`Client/Texts.py`）：我们自己写的字——四个站点触屏长按轮盘的七条条目（`arris_fd.hold.*`，条目带 `"key"`，前置包替它查）、厨锅的提示（`arris_fd.pot.*` 和 HoD 的键
  `handson_delight.pot.ready / cooking`）、食谱书页脚的秒数（`handson_delight.book.seconds`）、JEI 分类的名字和提示（`handson_delight.assembly*`）——进了 `rp/texts/zh_CN.lang`，并新建 `rp/texts/en_US.lang`（只有这些界面字，
  物品和方块的英文名还没补）。`Texts.of(键, 缺省)` 用 `CreateGame(levelId).GetChinese` 查，查不到用代码里的缺省中文；`Texts.fill` 填占位（中文写 `%d` 的一格，数先换成整数：译文写 `%s` 也是同一个数，不会写成 6.0），译文的占位写坏了就退回缺省。
  实机（zh_CN）：这些键都查得到。`tests/test_station_texts.py`。服务端发的提示、经典厨锅界面和 JEI 另外四类上的字原来还是写死的中文，2026-11-21 也改了，见下面两条。
- **服务端的提示按玩家的语言给**（2026-11-21，`Shared/Data/Tips`、`Shared/Rules/TipWire`）：物品栏上方弹的那一行提示（砧板切不了 / 换工具 / 还剩几个、煎锅和炉灶放不进、手持煎锅、盘装菜要碗、稻米要种在水里……）
  原来是服务端拼好中文、`SetOneTipMessage` 发的，谁看都是中文：服务端不知道每个玩家用什么语言（服务端的 `GetChinese` 给的是服务端那边的语言），官方文档里 `SetOneTipMessage` 的 message 就是要显示的字、没有交值的地方。
  现在 `Server/Helpers/Engine.ShowTip(玩家, 句子, 值...)` 只把"哪一句、填什么"`Call` 给那一个玩家（载荷：键、那句中文、每个值包成一个字典——网易 Call 载荷的列表里只能有一种类型），
  客户端端点 `Client/Endpoints.OnTip` 用 `Texts.of / fill` 按自己的语言查出这一句和值里的词、填好，再用客户端的 `SetTipMessage` 弹（同一种提示）。中文跟着发过去：语言文件里没有这一句、
  或者那里的写法填不上值时显示中文，不丢、不露键名；客户端什么都不往回发。句子都在 `Shared/Data/Tips`：JE 有的用 JE 的键（`block.farmersdelight.*` / `item.farmersdelight.*`，英文照 JE 的 en_us.json，
  中文是我们原来的写法），移植加的用 `arris_fd.tip.*`；值可以是数、字，或者一个词 (键, 中文)——盘装菜那句照 JE 填盛菜容器的名字，传的是原版碗的键 `item.bowl.name`。
  **加一句提示**：在 `Shared/Data/Tips` 写 (键, 中文) 并列进 `SENTENCES`，`rp/texts/zh_CN.lang`（和代码里的中文一字不差）、`en_US.lang` 各加一行，调用处写 `ShowTip(玩家, Tips.某句, 值...)`；
  不在服务端拼字，不直接调 `SetOneTipMessage`。`tests/test_tips.py` 核对两个语言文件、JE 的键和英文、每一处 `ShowTip` 给的值和占位一样多、别处不再弹提示、载荷的规矩和客户端的回退。没进过游戏。
- **经典厨锅界面和 JEI 上的字**（2026-11-21）：厨锅界面的标题是 JE 的容器标题键 `container.farmersdelight.cooking_pot`（`CookingPotHost.TITLE`；原来的方块名键只有中文）；"+"按钮下面那一行"添加食材"和搜索框的提示
  在 `layouts/cooking_pot.json` 里写 `arris_fd.pot_screen.*` 的键（那一行由库在客户端查，搜索框的提示由引擎的文字控件查；改了要照「厨锅界面」一节重新 vendor）；食谱详情的标题 `bookTitle`
  是库的可本地化文字 `Data.Lang`，没选食谱时是键（`CookingPotBook.UNPICKED_TITLE`）。库和引擎查不到键时显示键名本身，所以这些键两个语言文件里都要有；英文挑了放得进的短写法
  （按默认字体估：那一行 79 宽、搜索框除去放大镜 53、标题 75）。2026-11-22 照旧界面重做时去掉了"换一种配方"和携带版的两个页签，它们的键两个语言文件里都删了。
  只在 `DOLOR_SCREEN` 关掉时用的旧原生界面换成同一组键。JEI 的厨锅、砧板、煎锅、炉灶四类的名字（`jei.farmersdelight.cooking / cutting`、`arris_fd.jei.skillet / stove`）和配方页的秒数
  （`handson_delight.book.seconds`；秒数和站点食谱书的页脚一样先经 `StationBooks.shownSeconds` 半数进位成整数）在客户端经 `Texts` 查。`tests/test_pot_screen_texts.py`、`tests/test_jei_texts.py`。没进过游戏。
- **触屏的数量档**（前置包的按钮，屏幕右下角 全部 / 单个）在场时，四个站点的长按轮盘不再给"放一个"：拿着一叠放多少归那个按钮管（`HoldMenu.tapMode(view)`：`view.tap` 不是 None）；
  炉灶的"只放这一格"在拿着不止一个时也让给它。老版本的前置包没有 `view.tap`，轮盘照旧。`tests/test_hold_tap_mode.py`。
- **按住直接做**（前置包的 `Protocol.HOLD_ACT`，2026-11-21）：这样一来四个站点的长按菜单处处只有一条，前置包不再为它弹一条臂的轮盘——按住到点当场在原落点补那一下右键 / Shift 点击，
  等的时候手指上方一个带进度的小标签写着条目的字，点一下这样的地方头几次在物品详情牌上教一句"按住：xx"（前置包仓库的 `docs/diegesis/DESIGN.md` §9）。
  条目和 `HoldMenu` 的写法一条没改（字本来就说这一下做什么），表现收到的还是平常的右键 / Shift 点击；老版本的前置包照旧弹一条臂的轮盘。
- **切开的缝**（`Compat/Diegesis/BoardSeams.py`）：HoD 每切一刀把食物沿刀口分开 0.8 像素（`ItemVoxels.build` 的 `gap`，0.12 秒张开），看得出切到哪了；这里板上的东西是掉落物、切不开，
  原来每一刀只有落刀、声音、碎屑和下一条虚线。现在每条切过的线上、食物顶面上方压一条 0.8 像素宽的黑色半透明细条（粒子 `arris:board_seam`，不透明度 0.4），只画在图标的实心像素那一段；
  切过几刀 = 服务端说的 + 本地刚落还没回话的；同一件东西又多切一刀，所有的缝从 0 重新张开（JE 的 `gap` 只有一个数）；方块类、插着的工具、摆着层的板不画。
  和 JE 不一样的：两半并不真的挪开，缝里是压暗的食物而不是板和切面；只有开着站点的人看得到。`tests/test_board_seams.py`。没进过游戏（新粒子要完整重启）。
- **借来的工具跟着环境光变暗**：砧板站点上借来的那把刀 / 工具（半透明粒子 `arris:board_tool`）加了 `minecraft:particle_appearance_lighting`——JE 是照物品画的（`SceneRenderer.java:848` 的 `renderStatic` 带着站点的光照），
  原来暗处也是满亮度。实机只核过粒子建得出来。

## 和 JE 的出入（2026-11-26 审计）

对照 FD 1.3.4 逐类核过一遍（方块属性、掉落、食物、效果、声音、提示、绳子、番茄、烂番茄……）。改掉的在各自的"对照 JE"一节或提交说明里；
剩下的分两种，一条一行。

做不到（引擎 / 附加包的限制，或者没找到接口）：
- 滋养期间"总能吃"（JE `NourishmentAlwaysEatMixin`）：`can_always_eat` 只能写死在物品 JSON 里，没找到按身上的效果临时放开的接口。
- 原版汤（蘑菇煲、甜菜汤、兔肉煲）叠到 16（JE `SoupItemMixin`）：附加包覆盖不了原版物品的定义（网易有没有改原版堆叠的接口没核实）。
- 村庄里的堆肥堆、村庄农田种上农夫乐事的作物（JE `VillageStructures`）：附加包加不进原版村庄的拼图池（网易有没有替代接口没核实）。
- 进度（JE 21 条 advancements）：附加包加不了原版进度（网易的自定义成就能不能用没核实）。
- 拿刀打人击退少 0.1（JE `KnifeItem`）：`DamageEvent` 只能开关击退，改不了大小（煎锅同一个问题，见"煎锅"一节）。
- 帆布地毯不画挖掘裂纹（JE `HideBlockBreakProgressMixin`）：引擎没有按方块关掉裂纹的开关。
- 滋养时饥饿条镀金、舒适时生命条滚动（JE 两个客户端叠层）：原版 HUD 的饥饿条 / 生命条附加包改不了。
- 原版汤 / 南瓜派的提示（滋养时长、"可放置"）：附加包改不了原版物品的提示；六种盛宴的物品是方块物品，没有物品 JSON 可写 `netease:customtips`。
- 刀的攻击伤害只能写整数（`netease:weapon.attack_damage` 是 int，加在玩家基础 1 点之上：总伤害取 JE 的向上取整）；发光浆果布丁的"发光"基岩没有；砧板拆解里的动力矿车基岩没有。

有意不做：
- 帆布告示牌整套（34 个物品、68 个方块、34 个配方、编辑界面）：量大，单独估工作量。
- 村庄结构（同上一节的限制以外，JE 的五种村庄房子也没搬）。
- 进度（同上）。
- 物品和方块的英文名（英文客户端里是中文）：等做英文版时一起补。

暂时和 JE 不一样、等用户定的：
- 下界合金刀：JE 只有锻造台这一条（下界合金升级锻造模板 + 钻石刀 + 下界合金锭，附魔和耐久跟着走）。这边两条都在：锻造台配方
  `bp/recipes/arris_netherite_knife_smithing.json`（`minecraft:recipe_smithing_transform`；2026-11-26 引擎收了，按原料、按成品都查得到，
  但还没在锻造台界面里真做过一次、附魔留不留没看），工作台那条"下界合金锭 + 木棍"（`arris_netherite_knife.json`）先留着，等在游戏里亲手做过一次再决定删不删。

2026-11-26 四轮实机量过、照着改了或核过的：刀打一下掉 1 点耐久（和 JE 一样）、拆方块掉 2 点（改回 1 点）、`attack_damage` 加在基础 1 点之上（五把刀各减 1）；
原版堆肥桶空桶第一件必成、7 层不收不扣（脚本堆肥照做）；原版成熟作物的掉落分布和时运（沃土上的原版作物照它改）；番茄藤放回绳子、舒适回血、
滋养清消耗度、鸡 / 猪 / 兔子认本包的东西、沃土作物的分布、农夫乐事作物的时运也核过，五份覆盖的实体文件加载没报错
（这几份覆盖文件当天晚些时候删了，六种动物改成运行时加组件，动物认本包食物的那几条要用 `McdkAnimalsTest` 重新量）。
第四轮又核了：狼和鹦鹉的喂食（脚本驯服的狼掉血后喂肉末、熟培根、火腿各扣 1 件、回了血，回多少被野狼 8 点的血量上限截住没量出来，野狼不收；
鹦鹉收番茄种子、卷心菜种子、稻米）；派、菌落、填馅南瓜、野生作物点堆肥桶（3 层入桶、不放成方块，7 层不扣不放，8 层取骨粉、不放）；
装了机械动力时七种土豆加农炮弹药两端都登记上了（没开炮）；锻造台配方引擎收了（没在锻造台界面里做）。
还要进游戏看的（写好了、离线测过）：真的右键驯服鹦鹉 / 喂狼、吃下的滋养不冒粒子、效果颜色、方块音效、提示、创造栏、可燃、真的右键（拿绳子点绳子、
熟番茄拿骨粉）、烂番茄的声音和飞行、土豆加农炮真的开炮；还有铁砧修刀、在锻造台界面里真升级一次下界合金刀（附魔留不留）、刀挖掘的速度、
橱柜 / 篮子 / 厨锅拆下来留不留名字。

## 引擎坑（踩过的）

- 方块实体数据（`GetBlockEntityData`）是引擎对象，不是 dict：没有 `.get()`，缺键读出来是 `None`，用 `data["k"] or 缺省值`。
- `netease:face_directional` 的缺省状态 `direction = 0` 会把网易方块模型转 180°（Strata 的 `render --block` 不给状态就是这样），玩家放置时官方文档保证 north 贴图面向玩家；
  所以模型照 JE 的朝向原样转，和 JE 对照出图时要加 `--state direction=2`（不转）。
- 旧写法 `minecraft:block_light_emission` 是 0~1 的小数，引擎 ×15 取整：写 0.8 / 0.6 / 0.4 / 0.2 这种乘 15 正好落在整数上的值，别靠取整的方向碰运气。
- 挡不挡光照 JE（`tests/test_block_light.py` 钉着表，并从 `.refs` 的 ModBlocks 反查）：整格不透明的方块（箱子、米袋、稻米捆、稻草捆、橱柜、炉灶、有机肥、沃土、榻榻米）
  挡住全部的光，写 15；别的写 0。旧写法是 `minecraft:block_light_absorption {"value": n}`（不写 = 不透光，所以每个方块都写），1.19.20 起的格式是 `minecraft:light_dampening n`。
  沃土耕地照原版耕地写 0：JE 的耕地只有整面的底面挡住往下的光，基岩版没有按面挡光。挡光的只能是整格、实心、不透明的立方体：引擎画整格方块的面取面外那一格的亮度，
  挡不挡光它自己看起来一样；网易模型、十字花草、薄片取自己那一格，挡光就画成黑的。2026-11-18 之前那些整格方块都写的 0，光直穿过去。
  实机（2026-11-18，四面和底都是石头、只从上面进光的竖井）：改前这些方块下面 15，改后 0，和原版橡木板一样；点着的炉灶下面 12（自己发的光照样往外传）；
  `GetBlockLightLevel` 读挡光方块自己那一格是 0（发光的也是）。28 种方块改前改后同机位截图逐像素比，没有差别；炉灶上的食物（掉落物）最低在顶面以上 0.019 格，熄着的炉灶上也照常亮。
- 它的读取走 Python 侧缓存，**只有赋值才会写进引擎、随存档落盘**，缓存在区块卸载时丢弃：
  改了取回来的字典 / 列表之后一定要整体赋值回去，否则区块卸载后恢复原值（煎锅曾因此刷熟食）。
  键必须是 `str`、列表元素类型要一致、值不能是 `unicode`，不满足时引擎只打日志不报错。
- `/setblock`、`/fill`、结构放出来的方块不走 `ServerPlaceBlockEntityEvent`，方块实体数据里没有初始化过的键，读取处要补默认值。
- `ServerBlockUseEvent` 的取消字段是 `cancel`；`ServerItemUseOnEvent` 的是 `ret`。
- `DestroyBlockEvent` / `BlockRemoveServerEvent` / `BlockRandomTickServerEvent` 的方块名字段是 `fullName`，其余事件是 `blockName`；
  `BlockRemoveServerEvent` 的维度字段是 `dimension`。
- 营火点燃 / 熄灭只改 `extinguished` 状态、名字不变：判断热源要读状态（`Helpers.Heat.IsHeatSource`）；熔岩炼药锅也是状态（`minecraft:cauldron` 的 `cauldron_liquid` = lava，没有 `lava_cauldron` 方块），
  方块状态只有服务端读得到。
- 原版的火焰 / 烟粒子（`minecraft:basic_flame_particle`、`basic_smoke_particle`、`campfire_smoke_particle`）都是 `emitter_rate_manual`：`Create` 返回非 0 的编号、却一颗粒子也不发，
  要再调 `EmitManually`，而且原版 JSON 的发射器寿命是 `expiration_expression: 0`（不会自己结束 [推断：没有在游戏里看过它被销毁]）；一次性的粒子在资源包里写自己的
  （`emitter_rate_instant` + `emitter_lifetime_once`，`rp/particles/arris_stove_flame.json`）。
- `netease:block_entity` 的 `client_tick` / `tick` 是方块实体的标志，存档里的方块实体会盖过方块 JSON（`ModBlockActor::load` 先照组件建、再拿存的 `_tick` / `_tickClient` 盖）：改了方块 JSON 里这两个开关，
  旧存档里已经放着的方块不受影响，要重新放（或换一次方块）。`netease:block_animate_random_tick` 是方块级的组件，旧存档里的方块也有。
- 客户端读方块实体数据拿到的是 NBT 形式，每个值包成 `{"__type__": …, "__value__": …}`（`Client.Engine.unwrap`）。
- 世界时间（`CreateTime().GetTime()`）会被 `/time set` 改、被 `doDaylightCycle false` 冻住，不能拿来做 tick 节拍：
  用 `Shared/Rules/Ticks.Pacer`（真实时间）。
- 客户端读方块实体数据时，服务端存的 None 读出来不是 None、也不是缺键：实机（3.10.0.467018）是 `{'__type__': 1, '__value__': 2}`，解包后是整数 2。
  所以物品先过 `BlockDisplay.isItem` 再用，开关只认 `in (0, 1)`（砧板的"插着"标记清掉以后曾被读成插着；取回过东西的空砧板，区块一重新加载客户端就报
  `'int' object has no attribute 'get'`——`Client/BlockItems._itemsFromExData`，`tests/test_block_items_exdata.py`）。
- 服务端 `SetBlockNew` 放的方块，客户端不发 `ModBlockEntityLoadedClientEvent`；这个事件也可能重复触发——客户端渲染要幂等，
  内容以服务端广播为准。
- 客户端掉落物（`AddDropItemToWorld`）：轴心在贴图底边中点，缩放 1 时贴图边长 **0.45 格 = 7.2 像素**（`ItemPose.ITEM_SPAN`；引擎是调用方缩放 0.3 x 物品变换 1.5，方块物品的小立方体 0.25 格）。2026-11-19 之前按半格 8 像素算，站点里和方块上摆着的东西都只有九成大、还朝贴图的底边偏 0.4 x 缩放 像素；实机重量过（蛋糕 7.1、虞美人 7.2），改完截图对过砧板上的蛋糕正好 10 像素见方。画成平面的方块物品（花、野生作物）另外被抬高 0.2 格、轴心在离底边 5/16 个边长处（`RAISED_PIVOT` = 2.25 像素）。经典摆法里 Java 的 `scale(s)`：立方体是掉落物缩放 `2 s`，贴图是 `16 / 7.2 x s`（`BlockDisplay.FD_SCALE / FD_SPRITE`）；`SetDropItemTransform` 的 `rot=(x,y,z)` 是
  R = Rz·Rx·Ry，"躺平后再绕竖轴转"要先拼矩阵再换算（`ItemPose.engineEuler`）。
- 新加的自定义魔咒（`netease_enchants/`）、方块、物品定义要**完整重启游戏**才登记，重进存档不够（配方 JSON 重进存档就生效）。
- 带方块态的自定义方块不写战利品表时，掉出来的物品带着方块的 aux（实机：配了对的榻榻米掉 `arris:tatami` aux 8，和普通的叠不到一起）：写战利品表 `set_data 0`。
  1.19.10 起的格式 `minecraft:loot` 直接写路径字符串，网易 1.10 格式是 `{"table": 路径}`。
- 自定义方块态按名字**降序**从低位往高位排进 aux（名字大的占低位；arrisCreate 枚举反推，榻榻米实机再验过），往已有方块加状态时按这条挑名字，旧存档的 aux 才解得对。
- 走新管线的方块（`minecraft:geometry` + `minecraft:material_instances`）在 `blocks.json` 里写 `textures` 引擎不认还报错，只留 `sound`；
  `minecraft:geometry.full_block` 的底面贴图右 = 西、上 = 北，比 JE / 旧管线转了 180°，其余五面和 JE 一样。
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
FD_GAME_DIR=<不存在的目录>         照 CI 的样子跑：当本机没装游戏（tools/vanilla_pack.py），对原版资源包的核对跳过或只比本包的
```

`tests/` 只测不依赖引擎的部分（`Shared/`、`Api/`、`Server/EventRegistry.py`）和静态结构；
与引擎交互的部分用 Strata 的 `script_inspect` / `script_run`（沙箱加载、按剧本驱动事件）和游戏内实测。

- `fdtest.py`：农夫乐事包的导入与用例收集（`tipText`：服务端的一句提示在中文的游戏里显示成什么，假引擎的 `ShowTip` 记它）；`test_handson_*.py` 是 HoD 规则内核的测试。
- 按玩家的语言给的字：`test_tips.py`（服务端提示：语言文件、JE 的键、每一处调用、载荷、真的 `ShowTip` / `OnTip`）、`test_pot_screen_texts.py`（经典厨锅界面）、`test_jei_texts.py`（JEI 四类），
  站点上的字在 `test_station_texts.py`（要前置包）。
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
  （客户端可调的服务端端点只用注入的玩家 ID；随库装入）、`test_cooking_pot_book.py` / `test_cooking_pot_menu.py`（厨锅经典界面的食谱规则与
  界面模型，用库的纯逻辑部分在内存里跑，py2 与 py3 都跑：食谱格按搜索过滤与选中的底格、写法按注入的钟轮换、添加食材挑写法的先后与三种拒绝、
  两种界面档的 Shift 点击与双击收集、两种界面档编译出的是同一个界面）。
- 沉浸式交互前置不在这个仓库里：它是单独的作品、单独的工程 arrisDiegesis（`ArrisTeam/netease-diegesis`，2026-11-25 从本目录搬出去，有自己的全套测试）。
  亲手做菜的站点要拿它的源码和测试小工具（它的 `tests/dg*.py`：`dgtest`、`dgstation`、`dgkit`……）一起测：在哪由 `tests/prereqdir.py` 找——环境变量 `FD_PREREQ_DIR`
  给了就只认它（指向不存在的目录 = 当作没有，在装着前置包的机器上照"只 clone 了本仓库"的样子跑），没给就找旁边的 `../arrisDiegesis`。
  用到它的用例先 `import prereq`（`tests/prereq.py`）：找到了把那边的 `tests/` 放进 `sys.path`，前置包里的路径用它的 `BP` / `RP` / `SCRIPTS` / `TESTS` / `DOCS`；
  找不到时以 77 退出，跑器记成跳过。"有它就多查一点"的用例（`test_flat_faces.py`、`test_pan_smoke_particle.py`）直接看 `prereqdir` 的路径，没有就只查本包的。
  只有本仓库时 `py -3 tools/run_tests.py` 的最后一行是「N 项，失败 0，跳过 M」；`test_architecture.py` 只守本包，
  「没装前置包时什么都不联动」由 `test_presence_*.py`、`test_handson_mode.py`、`test_handson_options_gate.py` 守着，它们不需要前置包。
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
  派生规则、`scaled`）、`bootkit.py` + `test_handson_options_boot.py`（真的 `ServerBoot` / `ClientBoot`（经 `Presence` 和步骤表）和站点模块，引擎换成"什么名字都给无害替身"的模块，前置包服务端 Api 和客户端 Registry 是真的：
  每个开关只关自己的站点（它的步骤是 `skipped`）和连带的东西、32 种组合两端一致、前置包 API 低于 3 整个不联动、没装前置包是 `standalone`）、`test_handson_options_pot.py` / `_pan.py` / `_skillet.py` / `_stove.py`（三种倍率对着 JE 的 `sideTicks` / `timeFor`、FD 右键放的不乘、站点关了的交还）、
  `test_handson_options_book.py`（食谱书开关）；`test_pot_view.py` 里还有拿着容器点锅的哪些节点算盛。
- 联动（沉浸式交互前置）：这几个只用本仓库的东西（`linkkit.py` 是它们的小工具：`link()` / `Modes` 拨联动状态、`install()` 装两端入口的假环境），旁边没有前置包也能跑——
  `test_handson_mode.py`（模式状态机、`linked()`、`whenDecided`）、`test_presence.py`（判定的各种先后：导入时就在 / 事件时才在 / 一直没有 / 太旧，客户端事件之前什么也不碰，模式先于步骤拨到 `linked`）、
  `test_presence_steps.py`（步骤执行器：出错 / 跳过 / 条件；两张表每个目标都存在）、`test_presence_boots.py`（真的入口和步骤模块，站点的 `register` 换成记账的：一个站点一步、连带的东西、关了的站点两端一致）、
  `test_presence_standalone.py`（没装 / 太旧时 `sys.modules` 里没有站点模块、没有它们的监听和端点；装了才有）、`test_presence_notice.py`（前置包太旧的提醒：三次、隔 8 秒、`str`）、
  `test_handson_options_gate.py`（没联动时每个取值函数说 HoD 不在、厨锅 / 煎锅 / 炉灶走农夫乐事原样、不写"做过几份"）。要站点和 HoD 配置照常生效的假引擎小工具（`optkit`、`potfake`、`panclient`、`boardclient`）开头 `linkkit.link()`。
- 煎锅 / 炉灶上东西朝上那面的熟色：`test_frying_tint.py`（`FryingTint`：表里真的颜色、肉和鱼、没有颜色不染、叠层的 (q, a) 叠回 c）、
  `test_top_overlay.py`（`TopOverlay`：粒子的轴和掉落物的轴对上、平躺只转 y、斜着扣着不给、`Rz·Ry·Rx` 分解、抬高的上下界、余量不为 0（实机：0 会被顶面整块吃掉）、
  停稳两个游戏刻），这两个不要前置包；
  `test_fry_tints.py`（接在 `PanScene` / `StoveScene` 上的 `FryTints`，`panclient.py` 的假引擎记粒子的 `Create` / `SetPos` / `SetRot` / `SetVariable` / `Remove` 和
  `GetIconInfo`：躺稳才亮、和掉落物朝上那面严丝合缝、颠 / 翻时收着、熟了 / 拿走 / 场景没了就删、蛋 / 没颜色 / 方块物品不叠、图集和粒子系统没好时再试、
  老引擎不染、歇着不碰引擎；要前置包）。
- 发版的工具和工作流：`test_release_tools.py`（在临时副本上跑 version 的各个命令（含 `--new-uuid`：四个 UUID 都换、依赖 rp 的跟着换、`3ca4eaf4-…` 不动）、
  tag 的核对（临时 git 仓库里和上一个发版 tag 比 UUID：没有上一个 tag、换了、漏换 header / module、上一版没有这个 manifest、两个仓库叠在一个目录里的老样子）、更新说明的截短和条数上限；真打一个 zip 查根目录、排除项、
  许可文件、注释；结构检查和导入检查各种写法的报错；工作流的触发、job、权限、钉住的 action、调到的参数和 Windows 上装的第三方库，没有 PyYAML 时只做文本断言）。
- 网易打包机审的代码检查：`test_review_lint.py`（跑法在 `tests/reviewlint.py`）。机审就是 Python 2 的 pylint 1.9.5（astroid 1.6.6），同一套版本在本机跑出来的错和机审报的一样（2026-11-22 两个包被打回的 43 处一处不差，arrisCreate 的 `tools/check_pack_audit.py` 也这么做）；查进 zip 的整个脚本根（自检目录不查），开全部 E 类，只去掉本机没有引擎的 `mod` 包才报的（E0401 / E0611 / E1101 / E1102 / E1103）和机审不查的（python3 检查器的 E16xx、E1111）。pylint 装在引擎同款的 Python 2.7 里：`python2 -m pip install --user -r tools/requirements-pylint-py2.txt`；没装时这一项跳过（环境变量 `FD_REVIEW_LINT=required` 时算失败）。常见的错和改法：模块级字典里初值写 None、之后对它取下标 / 写下标 / `in`（初值写空字典，读没读过另记）；对先是 None 的量取下标、迭代（`x or ()` / `x or {}`，或者分开几个变量记）；混入类里先读后赋、初值在别的类的 `__init__` 里的属性（混入类上写同样的类属性）；`lambda node=node:` 这种同名默认参数（pylint 1.9 的毛病：换个名字）。
- 直接用 `python` 跑单个测试文件会在包目录里留下 `.pyc`；用 `tools/run_tests.py`（它设了 `PYTHONDONTWRITEBYTECODE`）。

## 发版

```
release.json                    这一套的配置：版本号所在的 manifest（第一个是权威来源）、进 zip 的包文件夹、不进包的路径、额外放进包里的文件
py -3 tools/version.py show     第一行是版本号，下面逐处列出版本号和 UUID；另有 check [--tag vX.Y.Z]、notes（Release 的正文）
py -3 tools/version.py bump --new-uuid       发版的第一步：末位加一、header / module 的 UUID 都换新的（或 set X.Y.Z --new-uuid）
py -3 tools/release_zips.py --check [--version X.Y.Z]                         出包前的检查（工作流的 check job 跑它）
py -3 tools/release_zips.py --name arrisFarmersDelight --version X.Y.Z --out dist   本机出一个包看看（上传的只用工作流出的）
```

每次发版都要换 UUID、提升版本号（这个仓库一直的做法），工作流会核对。发一版：`py -3 tools/version.py bump --new-uuid`（或 `set X.Y.Z --new-uuid`；
同一套包之间的依赖跟着换，bp 对别的作品的那条依赖 `3ca4eaf4-…` 永远不动）→ 提交两个 manifest → `git tag vX.Y.Z` → 推送分支和 tag。推上去的 tag 形如 `vX.Y.Z` 就触发
`.github/workflows/release.yml`：`check`（ubuntu-22.04 自带的 Python 3.10：tag 等于版本号、各处一致；有上一个发版 tag 时取那一版的同名 manifest，
每个 header / module 的 UUID 都要和它的不一样，有一个没换就报错、写明该敲的命令；`release_zips.py --check`）→
`test`（windows-2022：python.org 的 Python 2.7.18 安装包核对 SHA256 后静默装上，加 3.13 和钉了版本的 Pillow，再往 2.7 里装机审复现用的 pylint（装不上不挡发版，那一项测试跳过），以 `tools/run_tests.py` 的退出码和最后一行为准）→
`release`（更新说明、来源信息、出包、`gh release create`）；在 Actions 页面手动运行照样检查、测试、出包，只列出 zip 里有什么，不建 Release。
zip 是 `arrisFarmersDelight_v<版本>.zip`：根目录只有 `bp/`、`rp/`（网易的要求）；源码原样（不去注释、不去 print）；不进包的是 `Server/Debug`、`Client/Debug`
（只给 MCDK 调试时手动调的游戏内自检：进包的模块一个也不导入它们，`--check` 守着）、`__pycache__` / `*.pyc`、点开头的文件、`.md` 开发文档；
`bp/` 下多一份 `LICENSE` 和 `THIRD_PARTY_NOTICES.md`。来源信息（仓库、commit、版本、这次运行的地址、包名）在 zip 注释里（7-Zip 或 `unzip -z`）。
前置包工程（arrisDiegesis）有它自己的一套：`tools/dg_version.py`、`tools/dg_release_zips.py`、`tools/dg_release.json`，当初照这里的两个工具写的、只差配置文件那一行；
搬成独立工程以后两边各管各的（它的 `docs/diegesis/DESIGN.md` §3）。
