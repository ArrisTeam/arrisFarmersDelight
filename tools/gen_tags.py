# -*- coding: utf-8 -*-
"""gen_tags - 从词表 Shared/Data/Tags.py 生成行为包的 netease_tags/ 和 docs/TAGS.md 里的词表（开发工具，py -3 运行）

一个标签一个文件：{"type": "item" | "block", "identifier": 标签名, "items": [成员...]}，文件名照机械动力：
item_<标签名里的 : 和 / 换成 _>.json、block_<同上>.json。引擎把各模组登记的同名标签（type 和 identifier 都一样）合并去重。
原版自带的标签（VANILLA_TAGS）不生成文件。目录里不是这里生成的文件也算不一致（--check 失败，生成时删掉），词表是唯一的出处。
docs/TAGS.md 的词表（两行标记之间）也从词表生成：标签、意思、对应 JE、农夫乐事登记的、农夫乐事在哪里读；"意思"和"在哪里读"写在下面的
MEANINGS / READS 里（文档的话，不进游戏），词表加了标签这里没写意思时生成失败。"在哪里读"里配方读的那部分不手写，从配方表里数
（recipeReaders：厨锅每道菜的 Slots 里写着的 #标签、砧板的 CuttingTagDict）：改了这两张表要重新生成（测试核对文档是最新的）。
用法：py -3 tools/gen_tags.py            生成 / 更新 bp/netease_tags/ 和 docs/TAGS.md 的词表
      py -3 tools/gen_tags.py --check    只比较，不一致时退出码 1（tests/test_netease_tags.py 也会比）
"""
import importlib
import importlib.util
import io
import json
import os
import sys

sys.dont_write_bytecode = True      # 按路径加载词表、导入配方表时别在包里留 __pycache__

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "bp")
OUT = os.path.join(ROOT, "bp", "netease_tags")
SOURCE = os.path.join(ROOT, "bp", "arrisFarmersDelightScripts", "Shared", "Data", "Tags.py")
DOC = os.path.join(ROOT, "docs", "TAGS.md")
BEGIN = "<!-- gen_tags: 词表开始（tools/gen_tags.py 从 Shared/Data/Tags.py 生成，别手改） -->"
END = "<!-- gen_tags: 词表结束 -->"

MEANINGS = {
    "common:tomato": "番茄", "common:tomato_seeds": "番茄种子", "common:rice": "米（也是水稻的种子）", "common:rice_panicle": "稻穗",
    "common:cooked_rice": "米饭", "common:dough": "面团", "common:cooked_egg": "做熟的蛋（煎蛋）", "common:mutton_chops": "生羊排",
    "common:cooked_mutton_chops": "熟羊排", "common:knife": "刀", "arris:knife": "刀（农夫乐事的老标签，照旧有效）",
    "common:raw_beef": "生牛肉（含牛肉末）", "common:raw_pork": "生猪肉（含培根）", "common:raw_chicken": "生鸡肉（含鸡块）",
    "common:raw_mutton": "生羊肉（含羊排）", "common:raw_meat": "生肉：上面四种和生兔肉", "common:cooked_beef": "熟牛肉（含牛肉饼）",
    "common:cooked_pork": "熟猪肉（含熟培根）", "common:cooked_chicken": "熟鸡肉（含熟鸡块）", "common:cooked_mutton": "熟羊肉（含熟羊排）",
    "common:raw_fish": "生鱼（含鱼片，不含河豚）", "common:vegetable": "蔬菜（不含卷心菜）", "common:cabbage": "卷心菜（含卷心菜叶）",
    "common:milk": "奶（奶桶、奶瓶）", "common:mushrooms": "能吃的蘑菇", "common:onion": "洋葱", "common:carrot": "胡萝卜",
    "common:potato": "土豆", "common:beetroot": "甜菜根", "common:wheat": "小麦", "common:bread": "面包", "common:pasta": "生意面",
    "common:berry": "浆果", "common:bones": "骨头", "common:raw_cod": "生鳕鱼（含鱼片）", "common:raw_salmon": "生鲑鱼（含鱼片）",
    "common:cooked_fish": "熟鱼（含熟鱼片）", "common:cooked_cod": "熟鳕鱼（含熟鱼片）", "common:cooked_salmon": "熟鲑鱼（含熟鱼片）",
    "common:raw_bacon": "生培根", "common:cooked_bacon": "熟培根", "common:cabbage_seeds": "卷心菜种子", "common:water_bucket": "水桶",
    "common:crops": "作物（团队已有的名字）", "common:seeds": "种子（团队已有的名字）", "common:flowers": "花（团队已有的名字）",
    "farmersdelight:heat_sources": "热源：给上面的锅 / 煎锅加热（有点燃状态的要点着）",
    "minecraft:egg": "蛋（原版自带的标签）", "common:fruit": "水果", "common:wheat_flour": "小麦粉（机械动力的）",
    "farmersdelight:heat_conductors": "把热传给上面一格的方块",
    "farmersdelight:tray_heat_sources": "锅 / 煎锅放在上面要画托盘的方块",
    "farmersdelight:compost_activators": "有机肥周围的催化剂",
    "farmersdelight:unaffected_by_rich_soil": "沃土不催熟的植物",
    "farmersdelight:mushroom_colony_growable_on": "蘑菇菌落在它上面才长",
    "farmersdelight:drops_cake_slice": "拿刀右键切得下一片蛋糕的方块（插蜡烛的蛋糕）",
    "farmersdelight:meals": "饭菜（盛在碗里的一份；原版的蘑菇煲、甜菜汤、兔肉煲也算）", "farmersdelight:snacks": "小吃（三明治、汉堡、卷、饺子……）",
    "farmersdelight:sweets": "甜食（蛋糕、曲奇、派的切片、冰棍……）", "farmersdelight:drinks": "饮料（瓶装的）",
    "farmersdelight:feasts": "大餐（放在地上、一份一份盛出来的那几样）", "farmersdelight:pies": "派（原版的南瓜派也算）",
    "farmersdelight:wild_crops": "野生作物", "farmersdelight:mushroom_colonies": "蘑菇菌落", "farmersdelight:cabinets": "橱柜",
    "farmersdelight:serving_containers": "盛饭菜的容器（碗、玻璃瓶、桶）",
}
READS = {
    "common:knife": "是不是刀（Shared/Rules/Knives）", "arris:knife": "是不是刀（Shared/Rules/Knives）",
    "farmersdelight:heat_sources": "热源（Shared/Rules/HeatSources；锅底下的有点燃状态要点着，手持煎锅身边的不看）",
    "farmersdelight:heat_conductors": "锅 / 煎锅下面是它时看再下面一格（HeatSources.conducts）",
    "farmersdelight:tray_heat_sources": "锅 / 煎锅画不画托盘（Server/Helpers/Heat.RefreshHeat）",
    "farmersdelight:compost_activators": "有机肥堆沤的概率（Server/OrganicCompost）",
    "farmersdelight:unaffected_by_rich_soil": "沃土 / 沃土耕地催不催熟上面的植物（Server/BoneMeal.BoostPlant）",
    "farmersdelight:mushroom_colony_growable_on": "蘑菇菌落长不长（Server/MushroomColony）",
    "farmersdelight:drops_cake_slice": "拿刀右键切蛋糕（Server/KnifeSlicing.cutsLikeACake）",
}


def vocabulary():
    spec = importlib.util.spec_from_file_location("fd_tags_vocabulary", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fileName(kind, identifier):
    return "%s_%s.json" % (kind, identifier.replace(":", "_").replace("/", "_"))


def render(kind, identifier, members):
    body = json.dumps({"type": kind, "identifier": identifier, "items": list(members)}, indent=2, ensure_ascii=False)
    # 键的顺序照官方例子：type、identifier、items（json.dumps 不排序时按插入顺序，py3.7 起保证）
    return body + "\n"


def files(tags=None):
    """{文件名: 内容}"""
    tags = tags or vocabulary()
    found = {}
    for kind, table in (("item", tags.ITEM_TAGS), ("block", tags.BLOCK_TAGS)):
        for identifier, members in table.items():
            found[fileName(kind, identifier)] = render(kind, identifier, members)
    return found


def _codes(names):
    return "、".join("`%s`" % name for name in names) if names else "—"


def recipeReaders():
    """{标签: [读它的配方是哪些（一句话）]}，从配方表里数：厨锅每道菜的 Slots 里写着的 #标签（列出是哪几道菜，按表里的先后）、
    砧板按标签的配方（Shared/Data/Cutting.CuttingTagDict 的键，列出切成什么）。按包导入那两张表（厨锅配方表要相对导入词表）。"""
    if BP not in sys.path:
        sys.path.insert(0, BP)
    recipes = importlib.import_module("arrisFarmersDelightScripts.Shared.Data.CookingPotRecipes")
    cutting = importlib.import_module("arrisFarmersDelightScripts.Shared.Data.Cutting")
    dishes = {}
    for row in recipes.CookingPotRecipeList:
        for slot in row.get("Slots") or ():
            for option in slot:
                if isinstance(option, str) and option.startswith("#"):
                    names = dishes.setdefault(option[1:], [])
                    if row["text"] not in names:
                        names.append(row["text"])
    found = dict((tag, ["厨锅的格子：%s（Shared/Data/CookingPotRecipes 的 Slots）" % "、".join(names)]) for tag, names in dishes.items())
    for tag, recipe in sorted(cutting.CuttingTagDict.items()):
        made = "、".join("`%s`" % entry["itemName"] for entry in recipe["itemList"])
        found.setdefault(tag, []).append("砧板按标签切成 %s（Shared/Data/Cutting.CuttingTagDict，Shared/Rules/CuttingStation.recipeOf）" % made)
    return found


def docTable(tags=None):
    """docs/TAGS.md 的词表（两行标记之间的内容）。"""
    tags = tags or vocabulary()
    readers = recipeReaders()
    known = set(tags.ITEM_TAGS) | set(tags.VANILLA_TAGS) | set(tags.WITHOUT_MEMBERS)
    unknown = sorted(set(readers) - known)
    if unknown:
        raise SystemExit("配方里用了词表里没有的物品标签：%s（加进 Shared/Data/Tags.py，或者改配方）" % "、".join(unknown))
    rows = ["| 标签 | 种类 | 意思 | 对应 JE | 农夫乐事登记的 | 农夫乐事在哪里读 |", "| --- | --- | --- | --- | --- | --- |"]
    groups = (("物品", tags.ITEM_TAGS), ("方块", tags.BLOCK_TAGS), ("物品（原版自带，不生成文件）", tags.VANILLA_TAGS),
              ("物品（农夫乐事没有成员，不生成文件）", dict((tag, ()) for tag in tags.WITHOUT_MEMBERS)))
    for kind, table in groups:
        for tag, members in table.items():
            if tag not in MEANINGS:
                raise SystemExit("tools/gen_tags.py 的 MEANINGS 里没写 %s 的意思" % tag)
            reads = ([READS[tag]] if tag in READS else []) + (readers.get(tag, []) if kind.startswith("物品") else [])
            rows.append("| `%s` | %s | %s | %s | %s | %s |" % (tag, kind, MEANINGS[tag], _codes(tags.JE_NAMES.get(tag, ())),
                                                             _codes(members), "；".join(reads) or "—"))
    return "\n".join(rows)


def docText(current, tags=None):
    """把 current（docs/TAGS.md 现在的内容）里两行标记之间换成词表；没有标记返回 None。"""
    start, end = current.find(BEGIN), current.find(END)
    if start < 0 or end < start:
        return None
    return current[:start + len(BEGIN)] + "\n" + docTable(tags) + "\n" + current[end:]


def _syncDoc(tags, check):
    """docs/TAGS.md 的词表：一致返回 None，不一致（或没有标记）返回要报的话；不是 check 时写回。"""
    current = io.open(DOC, encoding="utf-8").read() if os.path.exists(DOC) else ""
    text = docText(current, tags)
    if text is None:
        return "docs/TAGS.md 里没有词表的两行标记"
    if text == current:
        return None
    if not check:
        with io.open(DOC, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    return "docs/TAGS.md 的词表"


def main(argv):
    tags = vocabulary()
    want = files(tags)
    check = "--check" in argv
    present = sorted(name for name in os.listdir(OUT)) if os.path.isdir(OUT) else []
    stale = [name for name in present if name not in want]
    changed = []
    for name, text in sorted(want.items()):
        path = os.path.join(OUT, name)
        current = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if current != text:
            changed.append(name)
            if not check:
                if not os.path.isdir(OUT):
                    os.makedirs(OUT)
                with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
    doc = _syncDoc(tags, check)
    if check:
        for name in changed + stale + ([doc] if doc else []):
            print("不一致：" + name)
        return 1 if changed or stale or doc else 0
    for name in stale:
        os.remove(os.path.join(OUT, name))
    print("netease_tags：%d 个文件，改了 %d 个，删了 %d 个；%s" % (len(want), len(changed), len(stale), doc or "文档的词表没变"))
    return 1 if doc and "标记" in doc else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
