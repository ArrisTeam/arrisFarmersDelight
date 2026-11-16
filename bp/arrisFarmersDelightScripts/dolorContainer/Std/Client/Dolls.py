# -*- coding: utf-8 -*-
"""
纸娃娃（Std/Components 的 doll，控件在 Std/Client/Widgets.py）用到的引擎接口：网易纸娃娃控件、实体的大小、方块模型的合成。

网易纸娃娃控件（netease_paper_doll_renderer）的行为，这里的写法按它们定：
- 实体（按实体编号）：以控件中心为原点，一格方块画"控件短边 × 缩放比例"像素；实体的原点在脚，玩家的原点在眼睛。
  转身、转头、低头都是 0 时正对着看的人，转身、转头为正时朝界面的左边，低头为负是抬头。实体离开这台客户端（走远、卸载、
  死亡）后不再画，回来了要重新交给它；
- 方块模型：缩放比例为 1 时一格方块画 10 像素，与控件大小无关；先是俯视（顶面朝着看的人），绕方块自己的竖轴转用 z 轴的
  初始转角，从上往下看的角度用 x 轴（-90 是正侧面，0 是正上方）；
- 骨骼模型：与实体一样以控件中心为脚、按控件短边乘缩放比例；模型没有登记时引擎改画一个没有实体的玩家（玩家动画控制器
  每帧报错），所以交给它之后要看模型建出来没有；
- 初始转角只取整数度；纸娃娃画的时候不管透明度。
引擎模块用到时才导入：标准库的控件模块会被离线的测试与编译工具导入。网易打包机审的接口桩里没有 mod.client.ui.controls，
纸娃娃控件的模块按名字取（Common/Modules.importModule），写成导入语句报 import-error。
"""
from ...Common import Modules

BLOCK_PIXELS = 10.0   # 方块模型缩放比例为 1 时一格方块的像素
_geometries = {}      # (方块名, 附加值) -> 合成的方块模型名（一次游戏里合成一次：名字相同的会覆盖，内容也一样）


def _client():
    import mod.client.extraClientApi as clientApi
    return clientApi


def _paperModule():
    return Modules.importModule("mod.client.ui.controls.neteasePaperDollUIControl").paperdoll


def entitySize(entityId):
    """实体碰撞箱的 (宽, 高)（格）；实体不在这台客户端上时为 None。"""
    try:
        size = _client().GetEngineCompFactory().CreateCollisionBox(entityId).GetSize()
    except Exception:  # noqa: BLE001  实体编号不对时引擎抛异常
        return None
    if not size or len(size) < 2 or not size[1] > 0:
        return None
    return float(size[0]), float(size[1])


def isPlayer(entityId):
    return entityId in (_client().GetPlayerList() or ())


def blockGeometry(name, aux):
    """一格方块合成的模型名；合成不了（方块名不对、引擎不支持这种方块）时为 None。"""
    key = (name, aux)
    if key not in _geometries:
        clientApi = _client()
        levelId = clientApi.GetLevelId()
        factory = clientApi.GetEngineCompFactory()
        palette = factory.CreateBlock(levelId).GetBlankBlockPalette()
        geometry = None
        if palette is not None and palette.DeserializeBlockPalette({
                "common": {(name, aux): [0]}, "extra": {}, "actor": {}, "volume": (1, 1, 1), "void": False}):
            geometry = factory.CreateBlockGeometry(levelId).CombineBlockPaletteToGeometry(
                palette, "dolor_doll_%s_%d" % (name.replace(":", "_"), aux), 1)
        _geometries[key] = geometry
    return _geometries[key]


class PaperDoll(object):
    """一个网易纸娃娃控件（control 是 asNeteasePaperDoll() 给的）：画什么、朝向。"""

    def __init__(self, control):
        self.control = control
        self._screen, self._path = control.mScreenName, control.FullPath()

    def entity(self, entityId, scale):
        return bool(self.control.RenderEntity({"entity_id": entityId, "scale": scale}))

    def blank(self):
        """什么都不画（交给一个不存在的实体）。"""
        _paperModule().render_actor(self._screen, self._path, "")

    def block(self, geometry, scale):
        return bool(self.control.RenderBlockGeometryModel({"block_geometry_model_name": geometry, "scale": scale}))

    def model(self, name, animation, scale):
        return bool(self.control.RenderSkeletonModel({"skeleton_model_name": name, "animation": animation,
                                                      "scale": scale}))

    def modelMissing(self):
        """交给它的骨骼模型没建出来（交给它之后要等引擎画过一帧）。"""
        return self.control.GetModelId() == -1

    def turnEntity(self, body, head, pitch, tilt):
        """实体的转身、转头、低头（度），整个模型绕横轴倾斜 tilt 度。"""
        paper = _paperModule()
        paper.set_rot(self._screen, self._path, (float(pitch), float(head)))
        paper.set_body_rot(self._screen, self._path, float(body))
        paper.set_head_rot(self._screen, self._path, float(head))
        paper.set_init_rot_x(self._screen, self._path, float(tilt))

    def turnModel(self, yaw, tilt):
        paper = _paperModule()
        paper.set_init_rot_y(self._screen, self._path, float(yaw))
        paper.set_init_rot_x(self._screen, self._path, float(tilt))

    def turnBlock(self, yaw, elevation):
        """方块绕自己的竖轴转 yaw 度、从上往下 elevation 度看。"""
        paper = _paperModule()
        paper.set_init_rot_z(self._screen, self._path, float(yaw))
        paper.set_init_rot_x(self._screen, self._path, float(elevation) - 90.0)
