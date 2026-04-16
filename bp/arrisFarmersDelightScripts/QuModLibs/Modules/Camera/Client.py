# -*- coding: utf-8 -*-
from ...Client import ListenForEvent, UnListenForEvent, clientApi, playerId, levelId, Entity, Vec3

lambda: "QuModLibs 摄像机模块 By Zero123"

class LensAnimType:
    NONE = -1
    """ 无过渡处理 """
    LINEAR = 0
    """ 线性动画 """

class LensAnimPositionProcessType:
    ABSOLUTE = -1
    """ 绝对坐标信息 """
    RELATIVE = 0
    """ 相对坐标信息 """

class CameraData:
    """ 摄像机参数 """
    def __init__(self, pos = (0, 0, 0), rot = (0, 0)):
        self.x = pos[0]
        self.y = pos[1]
        self.z = pos[2]
        self.rotX = rot[0]
        self.rotY = rot[1]
    
    def __str__(self):
        return "<CameraData.{}: {} {}>".format(id(self), (self.x, self.y, self.z), (self.rotX, self.rotY))

class LensPlayer:
    """ 镜头播放器 """
    def __init__(self, lensAnimType = LensAnimType.LINEAR, lockOperation = True):
        """
            镜头播放器参数
            @lensAnimType 镜头动画类型 默认为线性 具有过渡处理
            @lockOperation 是否锁定操作 默认为True 启用后在镜头动画期间锁定玩家
        """
        self.lensAnimType = lensAnimType
        self.lockOperation = lockOperation
        self._animTime = 0.0
        self._animObj = None                    # type: LensAnim | None
        self._workState = False
        self._speed = 1.0
        self._isListen = False

    def _createListen(self):
        if not self._isListen:
            self._isListen = True
            ListenForEvent("OnScriptTickNonChaseFrameClient", self, self.onFpsUpdate)
    
    def _freeListen(self):
        if self._isListen:
            self._isListen = False
            UnListenForEvent("OnScriptTickNonChaseFrameClient", self, self.onFpsUpdate)
    
    def free(self):
        """ 释放资源 """
        if self.getPlayState():
            self.onEnd()
        self._freeListen()
    
    def loadAnim(self, obj):
        # type: (CameraData) -> None
        comp = clientApi.GetEngineCompFactory().CreateCamera(levelId)
        comp.LockCamera((obj.x, obj.y, obj.z), (obj.rotX, obj.rotY))
        
    def onFpsUpdate(self):
        if not self._animObj:
            return
        if self._animObj.getTimeIsEnd(self._animTime):
            self._animTime = 0.0
            self.onEnd()
            self._animObj._onEnd()
            self._animObj = None
            return
        self.loadAnim(self._animObj.getTransformationWithTime(self._animTime))
        comp = clientApi.GetEngineCompFactory().CreateGame(levelId)
        self._animTime += (1.0 / comp.GetFps()) * self._speed
    
    def play(self, animObj, speed = 1.0):
        # type: (LensAnim, float) -> None
        """ 播放镜头动画 """
        newAnim = animObj.copy()
        self.setSpeed(speed)
        if self.lensAnimType == LensAnimType.LINEAR and self._animObj and self._animObj._lastCameraData:
            # 线性合并
            if len(newAnim._timeLineSet) > 0:
                newAnim.animDict[newAnim._timeLineSet[0]] = self._animObj._lastCameraData
        self._animObj = newAnim
        self._animTime = 0.0
        if not self.getPlayState():
            self.onStart()
        self._animObj._onStart()
    
    def stop(self):
        """ 停止当前的播放 """
        if self.getPlayState():
            self.onEnd()
    
    def setSpeed(self, speed = 1.0):
        """ 设置播放器速度 """
        self._speed = float(speed)
    
    def getPlayState(self):
        """ 获取播放状态 用于判断是否正在播放 """
        return self._workState

    def onStart(self):
        self._workState = True
        self._createListen()
        comp = clientApi.GetEngineCompFactory().CreateCamera(levelId)
        comp.LockModCameraYaw(1)    # 锁定摄像机 不允许玩家主动控制
        comp.LockModCameraPitch(1)

        comp = clientApi.GetEngineCompFactory().CreatePlayerView(playerId)
        comp.LockPerspective(1)     # 进入第三人称状态

        if self.lockOperation:
            # 锁定操作
            # motionComp = clientApi.GetEngineCompFactory().CreateActorMotion(playerId)
            # motionComp.LockInputVector((0, 0))
            from ...Modules.SharedAPI.Client import PlayerSharedAPI
            # 采用引用计数管理玩家是否允许移动
            PlayerSharedAPI.canNotMove.increaseRefCountWithKey(id(self))

    def onEnd(self):
        self._workState = False
        self._freeListen()
        comp = clientApi.GetEngineCompFactory().CreateCamera(levelId)
        comp.LockModCameraYaw(0)
        comp.LockModCameraPitch(0)
        comp.UnLockCamera()         # 解锁摄像机

        comp = clientApi.GetEngineCompFactory().CreatePlayerView(playerId)
        comp.LockPerspective(-1)

        if self.lockOperation:
            # 恢复操作
            # motionComp = clientApi.GetEngineCompFactory().CreateActorMotion(playerId)
            # motionComp.UnlockInputVector()
            from ...Modules.SharedAPI.Client import PlayerSharedAPI
            # 采用引用计数管理玩家是否允许移动
            PlayerSharedAPI.canNotMove.decreaseRefCountWithKey(id(self))

class LensAnim:
    """ 镜头动画 """
    def __init__(self, animDict = {}, positionProcess = LensAnimPositionProcessType.RELATIVE, unit = 1.0, onStart = lambda *_: None, onEnd = lambda *_: None):
        """
            镜头动画参数
            @animDict JSON形式的动画运镜信息 可借助三方工具开发
            @positionProcess 位置处理策略 默认使用相对位置(相对玩家) 可以修改为绝对位置信息(世界运镜)
            @unit 单位策略 默认16为一单位
            @onStart 动画播放开始的回调
            @onEnd 动画结束的回调
        """
        self.animDict = animDict                    # type: dict
        self._positionProcess = positionProcess
        self._unit = unit
        self._onStart = onStart
        self._onEnd = onEnd
        self._timeLineSet = list(animDict)
        self._timeLineSet.sort(key = lambda x: float(x))
        self._lastCameraData = None                 # type: list | None
        self._loop = False

    def setLoop(self, mode = True):
        """ 设置循环播放状态 """
        self._loop = mode
        return self

    def copy(self):
        """ 拷贝克隆方法 """
        obj = self.__class__({k:v for k, v in self.animDict.items()}, self._positionProcess, self._unit, self._onStart, self._onEnd)
        obj._loop = self._loop
        return obj
    
    def toCameraData(self, lis):
        # type: (list[float]) -> CameraData
        """ 转换到摄像机参数 """
        self._lastCameraData = lis
        obj = CameraData((lis[0], lis[1], lis[2]), (lis[3], lis[4]))
        self.formatTransformation(obj)
        return obj
    
    def getTransformationWithTime(self, __timeValue):
        # type: (float | int) -> CameraData
        """ 获取时间线变换 """
        if self._loop:
            # 循环播放
            __timeValue %= self.getMaxTime()
        headTimeKey = None
        endTimeKey = None
        for key in self._timeLineSet:
            timeV = float(key)
            # 头尾计算
            if timeV <= __timeValue:
                headTimeKey = key
            elif timeV > __timeValue:
                endTimeKey = key
            if headTimeKey != None and endTimeKey != None:
                # 找到了头尾
                break
        size = len(self._timeLineSet)
        if headTimeKey and not endTimeKey:
            # 有头无尾 越界时间轴
            if size > 0:
                trLis = self.animDict[self._timeLineSet[size-1]]
                return self.toCameraData(trLis)
        trLis = self.animDict[headTimeKey][::]
        end = self.animDict[endTimeKey]
        for i in range(len(end)):
            trLis[i] = trLis[i] + (end[i] - trLis[i]) * ((__timeValue - float(headTimeKey)) / (float(endTimeKey) - float(headTimeKey)))
        return self.toCameraData(trLis)

    def getTimeIsEnd(self, timeValue):
        """ 判断时间是否越界即结束动画 """
        if self._loop:
            return False
        if timeValue > self.getMaxTime():
            return True
        return False
    
    def getMaxTime(self):
        # type: () -> float
        """ 获取动画最大时间长度 """
        size = len(self._timeLineSet)
        if size > 0:        
            return float(self._timeLineSet[size-1])
        return 0.0

    def formatTransformation(self, obj):
        # type: (CameraData) -> None
        """ 格式化CameraData """
        obj.x /= self._unit
        obj.y /= self._unit
        obj.z /= self._unit

        # 计算相对位置信息
        if self._positionProcess != LensAnimPositionProcessType.RELATIVE:
            return
        playerObj = Entity(playerId)
        axis = Vec3(0, 1, 0)                        # 旋转轴

        _, rY = playerObj.Rot
        obj.rotY += rY

        # 相对的旋转
        posVec = Vec3(-obj.x, obj.y, -obj.z).rotateVector(axis, 360 - rY)
        posVec.addTuple(playerObj.Pos)

        obj.x = posVec.x
        obj.y = posVec.y
        obj.z = posVec.z

    @staticmethod
    def loadBEJSONAnim(jsonDict, unit = 16.0, yOff = -1.62, onStart = lambda *_: None, onEnd = lambda *_: None):
        # type: (dict[str, dict], float, float, object, object) -> LensAnim
        """ 从BE JSON动画参数加载 暂不支持时间线补位 请确保多个参数之间时间线的对齐
            @jsonDict JSON动画参数
            @unit 单位 对于MC动画16为1物理方块单位
            @yOff y轴偏移物理单位
        """
        data = {}
        hasRotZ = False
        for k, v in jsonDict.items():
            for timeLine, trData in v.items():
                if not timeLine in data:
                    data[timeLine] = [0 for _ in range(5)]
                dt = data[timeLine]
                if k == "rotation":
                    dt[3] = trData[0]
                    dt[4] = trData[1]
                    if len(trData) >= 3 and trData[2] != 0:
                        hasRotZ = True
                elif k == "position":
                    dt[0] = -trData[0]
                    dt[1] = trData[1] + yOff * unit
                    dt[2] = trData[2]
        if hasRotZ:
            print("LensAnim: 暂不支持RotZ轴 相关参数已被丢弃")
        obj = LensAnim(animDict = data, positionProcess = LensAnimPositionProcessType.RELATIVE, unit = unit, onStart = onStart, onEnd = onEnd)
        return obj