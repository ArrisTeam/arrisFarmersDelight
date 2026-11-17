# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点同步给客户端的东西（Compat/Diegesis/PotSync.py + PotLogic 的 userData / 控件写入）：六个控件跟着锅和勺子走、
站点数据（共享的部分和每人自己的两项）。引擎是 potfake.py 里的假的。"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import potkit as K
from potkit import BOWL, POT, SAUCE, TOMATO, fake

Protocol = K.Protocol
HandCooking = K.HandCooking
CONTROLS = ("progress", "heated", "stirring", "spoon_x", "spoon_z", "stars")


def _controls(manager):
    state = manager.stations[(0, POT)].state
    return dict((name, state.getControl(name)) for name in CONTROLS)


def _data(manager):
    return manager.stations[(0, POT)].state.getData()


def testTheControlsAreZeroOnAnIdlePotAndHeatedFollowsTheFire():
    manager, data = K.setup()
    K.opened(manager)
    assert _controls(manager) == {"progress": 0.0, "heated": 1.0, "stirring": 0.0, "spoon_x": 0.0, "spoon_z": 0.0, "stars": 0.0}
    data["heatEnable"] = False
    K.run(manager, 0.5)
    assert _controls(manager)["heated"] == 0.0, "熄了火：heated 跟着变"


def testAStrokeMovesTheSpoonAndItSettlesTwoSecondsAfterTheLastOne():
    manager, data = K.setup()
    K.feed(manager, TOMATO, 16)
    assert K.do(manager, "a", K.custom("stir", x=0.5, z=-0.25, at=1.0))
    controls = _controls(manager)
    assert controls["stirring"] == 1.0 and controls["spoon_x"] == 0.5 and controls["spoon_z"] == -0.25, controls
    K.run(manager, 1.5)
    assert _controls(manager)["stirring"] == 1.0, "搅一下算被搅 2 秒"
    K.run(manager, 1.0)
    controls = _controls(manager)
    assert controls["stirring"] == 0.0 and controls["spoon_x"] == 0.0 and controls["spoon_z"] == 0.0, "停了：勺子回到中间"
    assert K.do(manager, "a", K.custom("stir", x=7.0, z="bad", at=1.0))
    controls = _controls(manager)
    assert controls["spoon_x"] == 1.0 and controls["spoon_z"] == 0.0, "越界夹进 -1..1，不是数的当 0（不回滚、不抛）"
    assert K.do(manager, "a", K.custom("stir", x=1.0e30, z=0.25, at=1.0)) and _controls(manager)["spoon_x"] == 0.0
    assert not K.do(manager, "a", K.custom("stir", x=0.5, z=0.5, at=float("nan"))), "NaN 过不了前置包的线格式检查：整个动作被拒"
    assert _controls(manager)["spoon_x"] == 0.0 and _controls(manager)["spoon_z"] == 0.25


def testTheProgressAndTheStarsFollowTheStirringBatch():
    manager, data = K.setup()
    HandCooking.addMade("a", SAUCE, 40)
    K.feed(manager, TOMATO, 16)
    K.run(manager, 3.0, stir=True)
    controls = _controls(manager)
    assert 0.2 < controls["progress"] < 0.5, "3 秒的搅：整批共约 9.4 秒"
    assert 1.0 <= controls["stars"] <= 3.0 and controls["stirring"] == 1.0
    shared = _data(manager)
    assert shared["mode"] == K.HandCooking.PotCooking.STIRRED and shared["batch"] == 8 and shared["open_stars"] == 3
    assert 5.0 < shared["cook_left"] < 7.5, "还要几秒：总时长 x (1 - 进度) / 批量速度：%r" % shared["cook_left"]
    K.run(manager, 3.0)
    controls = _controls(manager)
    assert controls["stirring"] == 0.0 and controls["stars"] < 0.5, "不搅了：星星往下落"
    assert controls["progress"] > 0.4 and _data(manager)["mode"] == K.HandCooking.PotCooking.WAITING, "进度停在原处，等勺子"


def testTheSharedDataSaysWhatIsInThePot():
    manager, data = K.setup()
    K.opened(manager)
    assert _data(manager)["dish"] == {} and _data(manager)["vessel"] == {} and _data(manager)["cook_left"] == 0.0
    K.feed(manager, TOMATO, 16)
    K.run(manager, 0.5)
    shared = _data(manager)
    assert shared["dish"] == {"newItemName": SAUCE, "newAuxValue": 0, "count": 1} and shared["meal"] == {}
    assert shared["sunk"] == [] and shared["batch"] == 8 and shared["open_stars"] == 1
    K.run(manager, 20.0, stir=True)
    shared = _data(manager)
    assert shared["meal"] == {"newItemName": SAUCE, "newAuxValue": 0, "count": 8}, "煮好等着盛"
    assert shared["vessel"] == {"newItemName": BOWL, "newAuxValue": 0, "count": 1} and shared["vessel_name"] == "name:" + BOWL
    assert shared["dish"] == {} and shared["batch"] == 0 and shared["grade"] == 1 and shared["bonus"] == 0
    assert shared["sunk"] == [] and shared["cook_left"] == 0.0


def testTheDataIsRecomputedOnTheNextTickAfterTheSlotsChangeNotAQuarterSecondLater():
    manager, data = K.setup()
    fake.give("a", 3, "minecraft:milk_bucket", 1)
    fake.give("a", 4, "minecraft:carrot", 2)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3))) and K.do(manager, "a", K.click(K.slot(0)))
    assert _data(manager)["sunk"] == [], "站点数据在下一刻重算"
    manager.tick(0.05)
    assert _data(manager)["sunk"] == [0], "放进去之后的下一刻（不是 0.25 秒后）：奶桶是沉着的料"
    assert K.do(manager, "a", K.click(K.inv(4))) and K.do(manager, "a", K.click(K.slot(1)))
    manager.tick(0.05)
    assert _data(manager)["sunk"] == [0], "胡萝卜浮着"
    assert K.do(manager, "a", K.click(K.slot(0)))
    manager.tick(0.05)
    assert _data(manager)["sunk"] == [], "拿走了：不再沉着"


def testEachPlayerGetsHisOwnMadeCountAndWhetherTheSpoonIsInHisHand():
    manager, data = K.setup()
    HandCooking.addMade("b", SAUCE, 9)
    K.feed(manager, TOMATO, 16)
    logic = manager.stations[(0, POT)].logic
    assert logic.userData("a") == {"made": 0, "made_all": {}, "here": True}
    assert manager.open("b", list(POT)), "第二个人也能开：勺子给后来开的（没人在搅时）"
    manager.tick(0.3)
    assert logic.userData("b") == {"made": 9, "made_all": {SAUCE: 9}, "here": True}, "每道菜各做过几份：食谱书上的星星按它算"
    assert logic.userData("a") == {"made": 0, "made_all": {}, "here": False}
    states = fake.world.take("a", Protocol.EP_STATE)
    assert [s[2]["state"]["data"]["here"] for s in states if "here" in s[2]["state"].get("data", {})][-1] is False
    assert _data(manager)["open_stars"] == 2, "握着勺子的是 b：他做过 9 份，开 2 颗星"
    assert "made" not in _data(manager) and "made_all" not in _data(manager) and "here" not in _data(manager), "这几项不在共享的部分里"
    K.do(manager, "b", K.custom("stir", x=0.3, z=0.3, at=1.0))
    assert K.do(manager, "a", K.custom("stir", x=-0.3, z=-0.3, at=1.0)), "别人握着勺子：动作照收（不回滚）"
    assert abs(_controls(manager)["spoon_x"] - 0.3) < 0.02, "但 a 的这一下不算：勺子还在 b 手里（勺尖量化到 1/32）"


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
