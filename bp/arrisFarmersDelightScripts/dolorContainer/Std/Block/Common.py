# -*- coding: utf-8 -*-
"""
标准库：引擎方块容器的种类（两端都要导入；服务端的存法在 Std/Block/Server.py）。

ENGINE_CONTAINER 是方块自己的格子：原版的箱子、陷阱箱、木桶、潜影盒、漏斗、发射器、投掷器与网易的自定义容器方块，经引擎
读写，改了当场作用到方块里（原版界面、漏斗、别的玩家看到的是同一份）。实例键要是方块的实例键（"维度:x:y:z"，方块宿主给的
就是）。界面模型里声明的格数照方块：箱子、木桶、潜影盒 27，大箱子 54（从哪一半打开都是同一个 54 格），漏斗 5，发射器与
投掷器 9；比方块多出来的格子是空的、放不进。

    from ..dolorContainer.Std.Block import Common as BlockCommon
    s.collection("container_items", s.container("block", BlockCommon.ENGINE_CONTAINER, 27))

原版潜影盒不收潜影盒（各种颜色的）：给潜影盒用的格子写上格子类型的 accept=notShulkerBox，客户端预测就与服务端一致。
不能互相装的盒子是登记表（Std/Slots.addUnnestable：模组的背包、存储箱子），潜影盒方块与这类格子都照它。
"""
from ...Common.Collections import ContainerKind, registerKind
from ..Slots import notUnnestable

ENGINE_CONTAINER = registerKind(ContainerKind("engine_block"))


def isShulkerBox(name):
    """方块名或物品名是不是潜影盒（各种颜色的、没染色的）。"""
    return bool(name) and name.endswith("shulker_box")


def notShulkerBox(stack, rules=None):
    """格子类型的 accept：不收不能互相装的盒子（原版潜影盒的规矩，另加 Std/Slots.addUnnestable 登记过的；收纳袋里装着的也算）。"""
    return notUnnestable(stack, rules)
