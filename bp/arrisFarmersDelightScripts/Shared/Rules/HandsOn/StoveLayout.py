# -*- coding: utf-8 -*-
"""StoveLayout - 炉灶烤架上的六个烤位：位置、命中盒、机位、每件的朝向、离光标最近的空位、点一下做什么（双端，纯计算）

移植自 Hands-On Delight：scenes/stove.json（机位、piece_0~5、mouth / grill 薄板）与 client/StoveBehavior.java 的常量（43-60）、
placeOf（315-317）、yaw（220-222）、nearestFree（427-443）、onEvent（353-362）、onItemClick（417-423）。
坐标是 JE 场景的像素（16 = 1 格），原点在方块西北下角，按"炉灶朝北、玩家站在北面"书写：+x 在画面左边，+z 朝远处，
烤架面在 y = 16，件的中心 y = 16.02。两排各三件，0 1 2 在远处一排（从左到右），3 4 5 在近处一排；一件的边长 5 像素。
本移植里件的位置固定在方块里（不随炉灶朝向转，世界里的展示 Shared/Rules/BlockDisplay.STOVE_SLOTS 用同一份），所以客户端
要把这里的点按玩家所在的一侧换到站点空间（Compat/Diegesis/GrillView.py）；这个模块只管"炉灶朝北"那一份。
"""
PLACES = 6                   # Grill.PLACES
TOP = 16.02                  # 件的中心离方块底的高度，px（StoveBehavior.java:44）
SIZE = 5.0                   # 一件画多宽，px：FD 自己的炉灶把东西画成六像素宽、彼此留一点缝（43 行）
FLIGHT = 0.3                 # 翻一次在空中的时间，秒（48 行）；点得比它再快 0.05 秒以内的一下不发
AGAIN = FLIGHT + 0.05        # 同一件两次点翻面至少隔这么久（357 行）

PIECE_AT = ((12.8, 11.2), (8.0, 11.2), (3.2, 11.2), (12.8, 4.8), (8.0, 4.8), (3.2, 4.8))     # stove.json 34-39：件的 (x, z)，px
PIECE_BOX = ((-2.4, -0.2, -2.6), (2.4, 1.6, 2.6))        # 一件的命中盒，相对它自己的位置（stove.json 同行 collider）
MOUTH_BOX = ((1.0, 15.8, 1.0), (15.0, 16.2, 15.0))       # 拿着东西时整个烤架面都是它（drop_zone "hand"，stove.json:25-29）
GRILL_BOX = ((1.0, 15.8, 1.0), (15.0, 16.1, 15.0))       # 件旁边的点击（stove.json:30-33）：点上去什么也不发生
CAMERA = {"pos": (8.0, 50.5, -21.0), "target": (8.0, 16.0, 8.0), "fov": 30.0}     # stove.json:6-10
WORK_PLANE = 17.0            # 拿在手上的东西画在 work_plane + carry_lift（缺省 2.5）这个高度（stove.json:4）
STEP = 1.0 / 32.0            # 服务端告诉客户端烤到哪了的粒度（StoveLogic.java:19）

TAKE, TURN = "take", "turn"


def placeOf(place):
    """第 place 件躺的位置 (x, y, z)，px（StoveBehavior.placeOf）：x 取 12.8 / 8 / 3.2，z 取 11.2 / 4.8。"""
    x, z = PIECE_AT[place]
    return (x, TOP, z)


def blockFractions():
    """六件在方块里的位置（占方块宽的比例 x, z）：世界里展示用（BlockDisplay.STOVE_SLOTS），和开着站点时的画面对得上。"""
    return tuple((x / 16.0, z / 16.0) for x, z in PIECE_AT)


def pieceBox(place):
    """第 place 件的命中盒 (lo, hi)，px，炉灶朝北的那一份。"""
    x, y, z = placeOf(place)
    lo, hi = PIECE_BOX
    return ((x + lo[0], y + lo[1], z + lo[2]), (x + hi[0], y + hi[1], z + hi[2]))


def yawOf(place):
    """每件摆得各转一点、没有两件同向：((place * 7919) % 41 - 20) * 1.5 度（StoveBehavior.yaw，220-222）。"""
    return ((place * 7919) % 41 - 20) * 1.5


def nearestFree(cursor, centers, free):
    """离光标最近的空位（StoveBehavior.nearestFree）：cursor 是光标落在烤架面上的 (x, z)，没有就是 None（那就取最靠前的空位）；
    centers 是各件的 (x, z)，同一个坐标系；free 是各位置空不空。没有空位返回 -1。"""
    best, nearest = -1, None
    for place in range(len(free)):
        if not free[place]:
            continue
        if cursor is None:
            distance = float(place)
        else:
            dx, dz = cursor[0] - centers[place][0], cursor[1] - centers[place][1]
            distance = dx * dx + dz * dz
        if nearest is None or distance < nearest:
            best, nearest = place, distance
    return best


def pieceClick(button, done, sinceTurn):
    """点烤位上的一件做什么（StoveBehavior.onEvent，353-362）：右键、或已经烤好的，都是取下（TAKE）；否则是翻面（TURN），
    但离这件上次翻不到 AGAIN 秒时什么也不做（None）：它还在空中。button 0 左键 1 右键，sinceTurn 是离上次翻过多少秒。"""
    if button == 1 or done:
        return TAKE
    return TURN if sinceTurn > AGAIN else None


def placeRequest(button, nearest):
    """手上拿着一叠点烤架：左键 = 每个空位摆一件（{}）；右键 = 只放离光标最近的空位那一个（onItemClick，417-423）。"""
    if button == 1:
        return {"one": True, "place": nearest}
    return {}
