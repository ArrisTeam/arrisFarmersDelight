# -*- coding: utf-8 -*-
"""
组件的编译期说明（Std/Components.py）与运行时控件（Std/Client/Widgets.py）都要的尺寸、常数与绑定名（docs/ARCHITECTURE.md
第 2.1 节）：放在这里，运行时的控件不必载入编译期说明。两端共用，不导入引擎。
"""

STATE_TEXT_LIMIT = 32   # 只改客户端界面状态的文本框没写 $dc_max_length 时最多几个字
PAGE_NAMES = ("page", "pages")   # 分页的列表页码格式串里多出来的名字：第几页（1 起）、一共几页
PAGE_FORMAT = "{page} / {pages}"   # 页码缺省的写法
PAGE_ARROWS = ["<", ">"]   # 翻页按钮上缺省的字
GAUGE_FILL = "textures/ui/white_background"   # 仪表里资源名没有对应贴图时的填充
GAUGE_INSET = 1       # 仪表、流体堆叠里面离边的距离（组件文件里的缺省；$dc_inset 可以另写）
GAUGE_TIP_NAMES = ("name", "amount", "capacity", "unit", "fraction")   # 仪表、流体堆叠的悬停格式串里多出来的名字
FLUID_LAYERS = 8      # 流体堆叠最多画几种流体（组件文件里的层数，与 tools/gen_ui.py 一样）
FLUID_MIN_BAND = 3    # 流体堆叠里每种流体至少画几像素高（少的也看得见、点得到）
DOLL_STAGE = 2              # 网易纸娃娃渲染控件的边长：引擎按它的短边乘缩放比例画，大小全由比例给，控件只是摆在原点上
PLAYER_PIXELS = 30.0 / 70   # 原版物品栏 52 × 70 的框里一格方块画 30 像素：玩家与骨骼模型缺省按控件的高取这个比例
EYE_HEIGHT = 1.62           # 玩家的位置在眼睛，高出脚 1.62 格（原版人物渲染器以控件中心为眼睛）
BLOCK_FIT = (1.5, 1.7)      # 等轴的一格方块大约占几格宽、几格高：缺省的大小按它放进控件


def dropdownOption(drop, index):
    """下拉第 index 项单选项的名字：单选项的开关状态按它绑定，引擎报选中时也用它。"""
    return "#%s_o%d" % (drop, index)


def dropdownLabel(drop):
    """下拉开关上的字的绑定名。"""
    return "#%s_label" % drop


def dropdownText(drop, index):
    """选项来自界面数据时第 index 项的字的绑定名。"""
    return "#%s_t%d" % (drop, index)


def dropdownShown(drop, index):
    """选项来自界面数据时第 index 项显不显示的绑定名（没有这一项时藏起来）。"""
    return "#%s_v%d" % (drop, index)
