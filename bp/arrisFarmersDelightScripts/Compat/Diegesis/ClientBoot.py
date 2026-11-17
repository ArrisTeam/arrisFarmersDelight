# -*- coding: utf-8 -*-
"""ClientBoot - 场景交互前置的客户端联动入口：只挂 Presence，装了前置包才按步骤表联动；前置包太旧时提醒玩家更新（客户端）

单独在 modMain 里登记，Client/ 不导入 Compat/。和 ServerBoot 一样不导入任何站点模块（它们在 ClientSteps 的步骤里才被导入），
前置包没装时不联动、不提醒，什么也不做：方块照农夫乐事原样用，右键开经典界面或放料取料。
客户端只在 LoadClientAddonScriptsAfter 里找前置包（Presence.attach）：它的客户端接口模块会带进前置包自己的 QuModLibs，更早导入不安全。
前置包装了、接口却比本包要的老（Presence.REQUIRED_API_VERSION）时模式是 OUTDATED，一步也不联动，本地玩家进了世界就在左上角提醒更新，
隔 NOTICE_GAP 秒再提醒，共 NOTICE_TIMES 次（头一次容易被进世界时的别的提示盖住；和机械动力系列的附属包同一个做法）。
"""
from ...Client.Engine import compFactory, levelId
from ...QuModLibs.Client import ImportModule, Listen, clientApi
from ...Shared.Rules import HandsOnMode
from . import Presence
from .ClientSteps import STEPS

NOTICE = "§c[农夫乐事] §f前置模组 §e场景交互 · 前置§f 版本过旧，亲手做菜的站点不会启用，请更新。"     # 引擎的文本接口只收 str
NOTICE_TIMES = 3
NOTICE_GAP = 8.0

Presence.attach("client", STEPS, listen=Listen, find=clientApi.ImportModule, load=ImportModule)


def _notify(shown):
    compFactory.CreateTextNotifyClient(levelId).SetLeftCornerNotify(NOTICE)
    if shown + 1 < NOTICE_TIMES:
        compFactory.CreateGame(levelId).AddTimer(NOTICE_GAP, _notify, shown + 1)


@Listen("OnLocalPlayerStopLoading")
def OnLocalPlayerStopLoading(args=None):
    if HandsOnMode.mode("client") == HandsOnMode.OUTDATED:
        _notify(0)
