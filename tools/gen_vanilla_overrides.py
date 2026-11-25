# -*- coding: utf-8 -*-
"""gen_vanilla_overrides - 从原版行为包生成"整份拷来、只加本模组内容"的覆盖文件（开发工具，py -3 运行）

引擎里附加包的同路径文件整份替换原版、不合并（LOOT_ENGINE / TRADING 里写的"取包栈里优先级最高的那一份完整文件"），
所以想在原版基础上加一点东西，只能把原版文件抄过来再改。本工具读本机游戏目录里的原版行为包，只做下面写明的加法：

    entities/cat.json                                    猫被鳕鱼片 / 鲑鱼片吸引、驯服、繁殖、长大、治疗（JE：Cat.TEMPT_INGREDIENT）
    entities/chicken.json、pig.json                      鸡认两种种子和稻米、猪认卷心菜和番茄：吸引、繁殖、喂小崽（JE：Chicken / Pig.FOOD_ITEMS）
    entities/rabbit.json                                 兔子拿卷心菜、卷心菜叶繁殖、喂小崽（JE：RabbitsEatCabbageMixin；吸引在 Shared/Data/Mobs.py）
    entities/parrot.json                                 鹦鹉拿两种种子和稻米驯服（JE：Parrot.TAME_FOOD）
    entities/wolf.json                                   狼吃十种肉：繁殖、喂小崽、治疗（JE：狼吃 isMeat 的食物；讨食在 Shared/Data/Mobs.py）
    trading/economy_trades/farmer_trades.json            农民收洋葱、番茄、卷心菜、稻米（JE：VillagerEvents.onVillagerTrades）
    trading/economy_trades/wandering_trader_trades.json  流浪商人卖卷心菜种子、番茄种子、稻米、洋葱（JE：onWandererTrades）

原版的内容一个字不改（解析后只在列表末尾追加）。游戏升级、原版文件变了就重新跑一遍；
tests/test_vanilla_overrides.py 在能找到游戏目录时比对，不一致就失败，提醒重新生成。

用法：py -3 tools/gen_vanilla_overrides.py [--vanilla 原版行为包目录]    生成 / 更新
      py -3 tools/gen_vanilla_overrides.py --check                        只比较，不一致时退出码 1
原版行为包目录缺省：环境变量 FD_VANILLA_BP，再找游戏目录（vanilla_pack.gameDir()，缺省 D:/MCStudioDownload/game/MinecraftPE_Netease）下的 */data/behavior_packs/vanilla。
"""
import collections
import glob
import io
import json
import os
import re
import sys

import vanilla_pack

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "bp")

CAT_SLICES = ("arris:cod_slice", "arris:salmon_slice")
# 猫吃一片鱼片回的血：JE 按食物的饱食度，两种鱼片都是 1（原版整条的鱼是 2）
CAT_SLICE_HEAL = 1


def strip_jsonc(text):
    """去掉 // 和 /* */ 注释、对象 / 数组末尾多余的逗号（原版实体文件有这些写法）。"""
    out = []
    i, n, inString = 0, len(text), False
    while i < n:
        c = text[i]
        if inString:
            out.append(c)
            if c == "\\":
                out.append(text[i + 1])
                i += 2
                continue
            inString = c != '"'
        elif c == '"':
            inString = True
            out.append(c)
        elif c == "/" and text[i:i + 2] == "//":
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif c == "/" and text[i:i + 2] == "/*":
            i = text.find("*/", i + 2)
            i = n if i < 0 else i + 2
            continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def load(text):
    return json.loads(strip_jsonc(text), object_pairs_hook=collections.OrderedDict)


def dump(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _append(container, key, values, anchors):
    """container[key] 是列表，且含有全部 anchors（原版现有的条目）才在末尾追加 values，否则说明原版改了结构。"""
    items = container[key]
    names = [item["item"] if isinstance(item, dict) else item for item in items]
    for anchor in anchors:
        if anchor not in names:
            raise SystemExit("原版文件结构变了：%s 里找不到 %s（现有 %s），请先看过原版再改本工具" % (key, anchor, names))
    items.extend(values)


def build_cat(vanilla):
    entity = vanilla["minecraft:entity"]
    groups, components = entity["component_groups"], entity["components"]
    fish = ("fish", "salmon")
    _append(groups["minecraft:cat_baby"]["minecraft:ageable"], "feed_items", list(CAT_SLICES), fish)
    _append(groups["minecraft:cat_adult"]["minecraft:breedable"], "breed_items", list(CAT_SLICES), fish)
    _append(groups["minecraft:cat_wild"]["minecraft:tameable"], "tame_items", list(CAT_SLICES), fish)
    _append(groups["minecraft:cat_wild"]["minecraft:behavior.tempt"], "items", list(CAT_SLICES), fish)
    _append(groups["minecraft:cat_tame"]["minecraft:behavior.tempt"], "items", list(CAT_SLICES), fish)
    heal = [collections.OrderedDict([("item", name), ("heal_amount", CAT_SLICE_HEAL)]) for name in CAT_SLICES]
    _append(components["minecraft:healable"], "items", heal, fish)
    return vanilla


# 鸡 / 猪 / 兔子 / 鹦鹉 / 狼认农夫乐事的作物和肉（JE：CommonSetup 改 Chicken.FOOD_ITEMS、Pig.FOOD_ITEMS、Parrot.TAME_FOOD，
# RabbitsEatCabbageMixin 让卷心菜（标签 crops/cabbage：卷心菜、卷心菜叶）算兔子的食物，狼吃所有 isMeat 的食物）。
# JE 的 isFood 同时管繁殖和喂小崽长大：基岩的繁殖在成年组的 breedable、喂小崽在幼年组的 ageable，两处都加；吸引（tempt）在基础组件里。
# 兔子的吸引由 Shared/Data/Mobs.py 在实体出现时加（那张表早就有），这里只加繁殖和喂小崽。
CHICKEN_FOOD = ("arris:cabbage_seeds", "arris:tomato_seeds", "arris:rice")
PIG_FOOD = ("arris:cabbage", "arris:tomato")
RABBIT_FOOD = ("arris:cabbage", "arris:cabbage_leaf")
PARROT_FOOD = CHICKEN_FOOD
# 狼：JE FoodValues 里带 meat() 的 11 种去掉狗粮（狗粮对驯服的狼的右键由 Server/Livestock 接管，JE 的 DogFoodItem 也先于狼自己的喂食）。
# 值是 JE 的饱食度；治疗量照基岩原版狼的写法 = 饱食度 × 2（原版生猪排饱食度 3、治疗 6，熟猪排 8、16）
WOLF_MEATS = collections.OrderedDict([
    ("arris:minced_beef", 2), ("arris:beef_patty", 4), ("arris:chicken_cuts", 1), ("arris:cooked_chicken_cuts", 3), ("arris:bacon", 2),
    ("arris:cooked_bacon", 4), ("arris:mutton_chops", 1), ("arris:cooked_mutton_chops", 3), ("arris:ham", 5), ("arris:smoked_ham", 10)])


def _breedAndGrow(entity, adult, baby, food, anchor):
    groups = entity["component_groups"]
    _append(groups[adult]["minecraft:breedable"], "breed_items", list(food), (anchor,))
    _append(groups[baby]["minecraft:ageable"], "feed_items", list(food), (anchor,))


def build_chicken(vanilla):
    entity = vanilla["minecraft:entity"]
    _breedAndGrow(entity, "minecraft:chicken_adult", "minecraft:chicken_baby", CHICKEN_FOOD, "wheat_seeds")
    _append(entity["components"]["minecraft:behavior.tempt"], "items", list(CHICKEN_FOOD), ("wheat_seeds",))
    return vanilla


def build_pig(vanilla):
    entity = vanilla["minecraft:entity"]
    _breedAndGrow(entity, "minecraft:pig_adult", "minecraft:pig_baby", PIG_FOOD, "carrot")
    _append(entity["components"]["minecraft:behavior.tempt"], "items", list(PIG_FOOD), ("carrot",))
    return vanilla


def build_rabbit(vanilla):
    _breedAndGrow(vanilla["minecraft:entity"], "adult", "baby", RABBIT_FOOD, "carrot")
    return vanilla


def build_parrot(vanilla):
    groups = vanilla["minecraft:entity"]["component_groups"]
    _append(groups["minecraft:parrot_wild"]["minecraft:tameable"], "tame_items", list(PARROT_FOOD), ("wheat_seeds",))
    return vanilla


def build_wolf(vanilla):
    entity = vanilla["minecraft:entity"]
    _breedAndGrow(entity, "minecraft:wolf_adult", "minecraft:wolf_baby", list(WOLF_MEATS), "beef")
    heal = [collections.OrderedDict([("item", name), ("heal_amount", food * 2)]) for name, food in WOLF_MEATS.items()]
    _append(entity["components"]["minecraft:healable"], "items", heal, ("beef",))
    return vanilla


def _buy(item, quantity, maxUses, traderExp):
    # 农民收货：quantity 个 item 换 1 个绿宝石（JE：emeraldForItemsTrade(item, quantity, maxTrades, xp)，价格倍率 0.05）
    return collections.OrderedDict([
        ("wants", [collections.OrderedDict([("item", item), ("quantity", quantity), ("price_multiplier", 0.05)])]),
        ("gives", [collections.OrderedDict([("item", "minecraft:emerald"), ("quantity", 1)])]),
        ("trader_exp", traderExp), ("max_uses", maxUses), ("reward_exp", True)])


def build_farmer(vanilla):
    tiers = vanilla["tiers"]
    # JE 新手农民（第 1 级）多收洋葱、番茄，学徒（第 2 级）多收卷心菜、稻米；基岩版的"收货换绿宝石"那一组是各级的第 0 组
    for tier, trades in ((0, [_buy("arris:onion", 26, 16, 2), _buy("arris:tomato", 26, 16, 2)]),
                         (1, [_buy("arris:cabbage", 16, 16, 5), _buy("arris:rice", 20, 16, 5)])):
        group = tiers[tier]["groups"][0]
        for trade in group["trades"]:
            if trade["gives"][0]["item"] != "minecraft:emerald":
                raise SystemExit("原版农民表结构变了：第 %d 级第 0 组不再是'收货换绿宝石'，请先看过原版再改本工具" % tier)
        group["trades"].extend(trades)
    return vanilla


def _sell(item):
    # 流浪商人：1 个绿宝石换 1 个 item，只能买 1 次（JE：itemForEmeraldTrade(item, 1, 12)）
    return collections.OrderedDict([
        ("wants", [collections.OrderedDict([("item", "minecraft:emerald"), ("quantity", 1)])]),
        ("gives", [collections.OrderedDict([("item", item), ("quantity", 1)])]),
        ("max_uses", 1)])


def build_wanderer(vanilla):
    # 第 0 级第 2 组是"随机抽 5 个"的大杂烩（对应 JE 的 getGenericTrades）
    group = vanilla["tiers"][0]["groups"][2]
    if group.get("num_to_select") != 5 or len(group["trades"]) < 30:
        raise SystemExit("原版流浪商人表结构变了：第 0 级第 2 组不再是大杂烩，请先看过原版再改本工具")
    group["trades"].extend(_sell(item) for item in ("arris:cabbage_seeds", "arris:tomato_seeds", "arris:rice", "arris:onion"))
    return vanilla


# 输出文件（相对 bp/）-> (原版里的相对路径, 构建函数)
OUTPUTS = collections.OrderedDict([
    ("entities/cat.json", ("entities/cat.json", build_cat)),
    ("entities/chicken.json", ("entities/chicken.json", build_chicken)),
    ("entities/pig.json", ("entities/pig.json", build_pig)),
    ("entities/rabbit.json", ("entities/rabbit.json", build_rabbit)),
    ("entities/parrot.json", ("entities/parrot.json", build_parrot)),
    ("entities/wolf.json", ("entities/wolf.json", build_wolf)),
    ("trading/economy_trades/farmer_trades.json", ("trading/economy_trades/farmer_trades.json", build_farmer)),
    ("trading/economy_trades/wandering_trader_trades.json", ("trading/economy_trades/wandering_trader_trades.json", build_wanderer)),
])


def _version_key(path):
    # .../MinecraftPE_Netease/3.10.0.448891/data/behavior_packs/vanilla -> (3, 10, 0, 448891)；目录名不是版本号的排到最后
    name = path.replace("\\", "/").split("/data/behavior_packs/vanilla")[0].rsplit("/", 1)[-1]
    parts = name.split(".")
    return tuple(int(part) for part in parts) if all(part.isdigit() for part in parts) else ()


def find_vanilla(explicit=None):
    candidates = [explicit, os.environ.get("FD_VANILLA_BP")]
    candidates += sorted(glob.glob(vanilla_pack.gameDir() + "/*/data/behavior_packs/vanilla"), key=_version_key, reverse=True)
    for path in candidates:
        if path and os.path.isfile(os.path.join(path, "entities", "cat.json")):
            return path
    return None


def generate(vanillaDir):
    """{输出相对路径: 文件文本}。"""
    result = {}
    for out, (source, build) in OUTPUTS.items():
        with io.open(os.path.join(vanillaDir, source), encoding="utf-8-sig") as f:
            result[out] = dump(build(load(f.read())))
    return result


def main(argv):
    explicit = argv[argv.index("--vanilla") + 1] if "--vanilla" in argv else None
    vanillaDir = find_vanilla(explicit)
    if vanillaDir is None:
        print("找不到原版行为包：用 --vanilla 或环境变量 FD_VANILLA_BP 指定 behavior_packs/vanilla")
        return 2
    stale = []
    for out, text in generate(vanillaDir).items():
        path = os.path.join(BP, *out.split("/"))
        current = io.open(path, encoding="utf-8", newline="").read().replace("\r\n", "\n") if os.path.isfile(path) else None
        if current == text:
            continue
        stale.append(out)
        if "--check" not in argv:
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            print("写入 %s" % out)
    if "--check" in argv and stale:
        print("与原版 %s 不一致：%s（py -3 tools/gen_vanilla_overrides.py 重新生成）" % (vanillaDir, ", ".join(stale)))
        return 1
    print("原版：%s；%s" % (vanillaDir, "全部是新的" if not stale else "更新了 %d 个文件" % len(stale)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
