# -*- coding: utf-8 -*-
"""
库的界面底座与组件里的控件路径（与 tools/gen_ui.py 生成的界面 JSON 对应，tests/test_ui_json.py 核对）。
布局内容里的路径（格子区、写文字的控件、具名控件）在布局的绑定表里（Client/Layouts.py），都相对屏幕根 ROOT。
"""

from .UiDefs import FILE as UI_FILE, NAMESPACE  # noqa: F401  命名空间与文件名带内容哈希，由生成器写

SCREEN = "/variables_button_mappings_and_controls"   # 屏幕上的全部（连同背景）
ROOT = SCREEN + "/safezone_screen_matrix/inner_matrix/safezone_screen_panel/root_screen_panel"
GATE = ROOT + "/transition_gate"   # 退出过渡的门：藏起来时退出过渡跳过（切换布局时内部弹出旧屏幕，见 tools/gen_ui.py）
CONTENT = ROOT + "/content"                       # 布局的内容（布局屏幕给的 $dc_content）
FLYING = ROOT + "/flying_item_renderer"           # 原版物品飞行渲染器

# 跟随指针的部分：手持物、渐进拿取进度条
CURSOR = ROOT + "/cursor"
CURSOR_ICON = CURSOR + "/icon"
CURSOR_RENDERER = CURSOR_ICON + "/selected_item_icon"
CURSOR_COUNT = CURSOR_ICON + "/selected_stack_size_text"
CURSOR_LOCK = CURSOR_ICON + "/selected_item_lock_overlay"
CURSOR_DURABILITY = CURSOR_ICON + "/durability_bar_grabbed"
CURSOR_STORAGE = CURSOR_ICON + "/storage_bar_grabbed"
CURSOR_HOLD = CURSOR + "/hold_icon"

# 两套界面共有的上层部件
ITEM_DETAILS = ROOT + "/item_details"
ITEM_DETAILS_IMAGE = ITEM_DETAILS + "/item_panel_image"
ITEM_DETAILS_TEXT = ITEM_DETAILS_IMAGE + "/item_text_label"
LOCK_NOTIFICATION = ROOT + "/lock_notification"
LOCK_NOTIFICATION_IMAGE = LOCK_NOTIFICATION + "/notification_background_image"
LOCK_NOTIFICATION_TEXT = LOCK_NOTIFICATION_IMAGE + "/notification_text_label"
SPLIT_BAR = ROOT + "/split_bar"
SPLIT_BAR_SIDES = {"above": "progressive_up", "below": "progressive_down", "left": "progressive_left_side",
                   "right": "progressive_right_side"}
SPLIT_BAR_FILL = "/stack_progress_bar/progressive_select_progress_bar"
SPLIT_BAR_TEXT = "/stack_progress_bar/progressive_select_text"
HELPERS = ROOT + "/helpers"
HELPER_TEXT = HELPERS + "/buttons/%s/description_panel/desc"
HELPER_KEYS = ("x", "a", "y", "b")

# 格子区里的格子控件：固定格子区与按格数的滚动内容里是 s<序号>，按行回收的滚动内容里是 r<行>/s<列>
CONTENT_ROW = "/r%d"
CONTENT_ROW_SLOT = "/r%d/s%d"
CONTENT_SLOT = "/s%d"

# 格子的子控件（照原版 container_item 的结构）
SLOT_RENDERER = "/item_cell/item/item_renderer"
SLOT_COUNT = "/item_cell/item/stack_count_label"
SLOT_DURABILITY = "/item_cell/durability_bar"
SLOT_STORAGE = "/item_cell/storage_bar"
SLOT_CELL = "/item_cell/bg/cell_image"
SLOT_CELL_SELECTED = "/item_cell/bg/cell_image_selected"
SLOT_SELECTED = "/item_selected_image"
SLOT_SELECTED_PROGRESS = SLOT_SELECTED + "/progress_bar_release"
SLOT_BUTTON = "/item_button_ref"
SLOT_HOVER = SLOT_BUTTON + "/hover"
SLOT_HOVER_PARTS = ("/highlight", "/white_border")
SLOT_TIP = SLOT_HOVER + "/highlight/hover_text"     # 悬停文本（原版挂在高亮下面）
SLOT_LOCK = "/container_item_lock_overlay"
SLOT_LOCK_CELL = "/item_lock_cell_image"
SLOT_DISABLED = "/item_disabled_image"   # 停用的格子（合成器的停用格）
SLOT_DECOR_TINT = "/decor_tint"            # 格子装饰（Std/Decor）：底色
SLOT_DECOR_PLACEHOLDER = "/decor_placeholder"   # 空着时的占位图标
SLOT_DECOR_FILL = "/decor_fill"            # 从下往上盖的一层
SLOT_DECOR_LINE = "/decor_line"            # 底边的横条
SLOT_DECOR_LOCK = "/decor_lock"            # 锁住的样子
SLOT_DECOR_RENDERER = "/decor_renderer"    # 布局给格子加的自定义渲染器（$dc_slot_renderer，织布机图案按钮上的旗帜）
SLOT_DECOR_BADGE = "/decor_badge"          # 右下角的小图标（原版创造栏组头的加号、减号）
LOCK_YELLOW = "/lock_yellow"     # 锁在背包
LOCK_RED = "/lock_red"           # 锁在格子

# 收纳袋：悬停提示（键鼠与手柄跟着指针的一份，触屏贴底边的一份）
BUNDLE_CURSOR = ROOT + "/bundle_cursor"
BUNDLE_CURSOR_TOOLTIP = BUNDLE_CURSOR + "/tooltip"
BUNDLE_TOUCH_TOOLTIP = ROOT + "/bundle_touch"
ITEM_LAYERS = ("top_layer_3", "top_layer_2", "top_layer_1", "bottom_layer_1", "bottom_layer_2")   # 网易的物品叠加贴图
ITEM_LAYER_TEMPLATE = NAMESPACE + ".item_%s"             # 按需建在图标控件下，控件名就是层名
BUNDLE_CELL_TEMPLATE = NAMESPACE + ".bundle_cell_%s"     # 提示网格一格的模板（classic / pocket，触屏的再加 _touch）
# 提示里的部件（相对提示）
BT_SELECTED_NAME = "/background/selected_item_tooltip"
BT_SELECTED_TEXT = BT_SELECTED_NAME + "/item_text_label"
BT_LABEL = "/header_stack/bundle_label"
BT_BODY = "/wrapper/vertical_layout_stack/horisontal_layout_stack/body_stack"
BT_GRID = BT_BODY + "/item_grid"
BT_CELL = BT_GRID + "/c%d"
BT_INFO = BT_BODY + "/info_message"
BT_BAR = BT_BODY + "/footer_panel/weight_bar"
BT_BAR_EMPTY = BT_BAR + "/empty_message"
BT_BAR_FILL = BT_BAR + "/weight_bar_fill"
BT_BAR_FULL = BT_BAR + "/weight_bar_full"
# 网格一格里的部件（相对格）
BC_SLOT = "/slot"
BC_RENDERER = BC_SLOT + "/item_cell/item/item_renderer"
BC_COUNT = BC_SLOT + "/item_cell/item/stack_count_label"
BC_DURABILITY = BC_SLOT + "/item_cell/durability_bar"
BC_STORAGE = BC_SLOT + "/item_cell/storage_bar"
BC_HIGHLIGHT = BC_SLOT + "/item_cell/highlight"
BC_HIGHLIGHT_MOUSE = BC_HIGHLIGHT + "/mouse"
BC_HIGHLIGHT_TOUCH = BC_HIGHLIGHT + "/touch"
BC_MORE = "/more"
# 收纳袋张开的覆盖层：每个格子区一个（经典版在 ipool、hpool 与容器滚动内容里，携带版在两个滚动内容里）
BUNDLE_OPEN = "/bopen"
BO_MOUSE = "/panel/background/mouse"
BO_TOUCH_CELL = "/panel/background/touch_cell"
BO_TOUCH_FRAME = "/panel/background/touch_frame"
BO_BACK = "/panel/open_back"
BO_ITEM = "/panel/selected_item"
BO_FRONT = "/panel/open_front"
BO_STORAGE = "/panel/storage_bar"

# 按钮名（JSON 的 to_button_id，ViewBinder 收这些）
BUTTONS = ("#dc.primary", "#dc.ok", "#dc.secondary", "#dc.quick", "#dc.drop", "#dc.dropall", "#dc.hover",
           "#dc.panel", "#dc.panel2", "#dc.blank", "#dc.blank2", "#dc.outside", "#dc.outside2", "#dc.close",
           "#dc.wheelup", "#dc.wheeldown", "#dc.bcell", "#dc.bhide", "#dc.btip",
           "#dc.stickup", "#dc.stickdown", "#dc.stickleft", "#dc.stickright") + \
    tuple("#dc.slot%d" % number for number in range(1, 10))   # 快捷栏键位
# 控件里的按钮（布局或控件模板里写，组件文件里没有）：按下与抬起各报一次，按按钮路径交给它所在的控件
# （Client/Widgets.py 的 onInput）。照原版"交互"时机报一次的按钮（库的按钮、开关、循环按钮、页签）不走它：引擎的
# 交互事件里没有按钮路径，所以每个按钮一个名字（编译时生成），按名字交给控件（Widget.presses）
WIDGET_BUTTON = "#dc.widget"
# 原版文本框里的清空按钮（$text_clear_button_enabled）映射到的按钮名（原版模板里写死的）：界面按它接，交给按钮所在的文本框；
# 按钮在文本框里的路径与它的显隐绑定（原版按全局绑定设显隐）
TEXT_CLEAR_BUTTON = "button.text_edit_box_clear"
TEXT_CLEAR_PATH = "/centering_panel/clipper_panel/clear_text_button_panel/clear_text_button"
TEXT_CLEAR_VISIBLE = "#show_clear_text_button"

# Python 播放的淡出动画（gen_ui.py 的 animations）
DETAILS_ANIMATION = "details_alpha"
LOCK_BACKGROUND_ANIMATION = "lock_background_alpha"
LOCK_TEXT_ANIMATION = "lock_text_alpha"
# 运行时按名字建或挂的模板：物品图标的叠加层、收纳袋提示的格子、上面几个淡出动画。布局里引用不到它们，拷进使用方时公共界面
# 文件按这里列的保留（docs/ARCHITECTURE.md 第 2.2 节）；写成字面量，vendor 按语法树读
UI_TEMPLATES = ("item_top_layer_3", "item_top_layer_2", "item_top_layer_1", "item_bottom_layer_1", "item_bottom_layer_2",
                "bundle_cell_classic", "bundle_cell_classic_touch", "bundle_cell_pocket", "bundle_cell_pocket_touch",
                "details_alpha", "lock_background_alpha", "lock_text_alpha")
