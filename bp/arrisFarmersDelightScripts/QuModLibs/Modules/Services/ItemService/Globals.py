# -*- coding: utf-8 -*-
lambda: "By Zero123 通用物品协议规范"

class _ItemBasicInfo:
    """ 基础物品信息 """
    class ITEM_CATEGORY:
        """ 创造模式栏分类 """
        CONSTRUCTION = "construction"
        """ 建筑 """
        NATURE = "nature"
        """ 自然 """
        EQUIPMENT = "equipment"
        """ 装备 """
        ITEMS = "items"
        """ 物品 """
        CUSTOM = "custom"
        """ 自定义 """
        UNKNOW = ""
        """ 未知不存在的 """

    class CUSTOM_TIPS:
        """ 自定义Tips"""
        ITEM_NAME = "%name%"
        """ 物品名称 """
        ITEM_TYPE = "%category%"
        """ 物品类型分页 """
        ITEM_ENCHANTING = "%enchanting%"
        """ 物品附魔信息 """
        ITEM_ATTACK_DAMAGE = "%attack_damage%"
        """ 攻击伤害 """

    def getArgs(self, itemName, auxValue, isEnchanted):
        return {}
        
    def __init__(self, itemName = "", auxValue = 0, isEnchanted = False):
        # type: (str, int, bool) -> None
        self.args = self.getArgs(itemName, auxValue, isEnchanted)
        self.itemName = ""          # type: str
        """ 本地化物品名称 """
        self.maxStackSize = 0       # type: int
        """ 最大堆叠数量 """
        self.maxDurability = 0      # type: int
        """ 最大耐久值 """
        self.itemCategory = ""      # type: str
        """ 创造模式栏分类 """
        self.itemType = ""          # type: str
        """ 物品类别 """
        self.weaponDamage = 0       # type: int
        """ 武器攻击力 """
        self.armorDefense = 0       # type: int
        """ 护甲防御力 """
        self.update()
    
    def update(self):
        if self.args == None:
            return
        self.itemName = self.args.get("itemName", "")
        self.maxStackSize = self.args.get("maxStackSize", 0)
        self.maxDurability = self.args.get("maxDurability", 0)
        self.itemCategory = self.args.get("itemCategory", "")
        self.itemType = self.args.get("itemType", "")
        self.weaponDamage = self.args.get("weaponDamage", 0)
        self.armorDefense = self.args.get("armorDefense", 0)

class NBT_TYPE:
    """ NBT类型 """
    INT = 1
    SHORT = 2
    LONG_LONG = 3
    FLOAT = 4
    DOUBLE = 5
    STRING = 8

    VIEW_MAPPING = {
        INT: int,
        SHORT: int,
        LONG_LONG: int,
        FLOAT: float,
        DOUBLE: float,
        STRING: str,
    }

    AUTO_CAST = {
        int: INT,
        float: FLOAT,
        str: STRING,
    }

class BaseNBTView:
    AUTO_TYPE = -1
    NOT_NBT_TYPE = -2

    """ NBT视图基类 """
    def __init__(self, data=None):
        # type: (dict | list | None) -> None
        self.refData = data
        if data is None:
            self.refData = dict()

    def getDataRef(self):
        return self.refData

    @staticmethod
    def checkIsNbtType(value):
        """ 检查是否为NBT类型 """
        return isinstance(value, dict) and "__type__" in value and "__value__" in value

    @staticmethod
    def pyObjectToNBTData(value, castType=AUTO_TYPE):
        """ 将Python对象转换为NBT数据 """
        typeId = 0
        if castType == BaseNBTView.AUTO_TYPE:
            # 自动转换类型
            typeId = NBT_TYPE.AUTO_CAST[type(value)]
        return {"__type__": typeId, "__value__": value}

    def getKey(self, key, noneValue=None):
        # type: (str, object | None) -> object | None
        """ 获取指定key的值 """
        if key in self.refData:
            value = self.refData[key]
            if BaseNBTView.checkIsNbtType(value):
                return value["__value__"]
            return value
        return noneValue

    def getNBTValueType(self, key):
        # type: (str) -> int
        """ 获取指定key的NBT类型 """
        if key in self.refData:
            value = self.refData[key]
            if BaseNBTView.checkIsNbtType(value):
                return value["__type__"]
        return BaseNBTView.AUTO_TYPE

    def hasKey(self, key):
        # type: (str) -> bool
        """ 检查是否存在指定key """
        return key in self.refData

    def setKey(self, key, value, castType=AUTO_TYPE):
        # type: (str, object, int) -> None
        """ 设置指定key的值 """
        if castType == BaseNBTView.NOT_NBT_TYPE:
            # 非NBT数据层
            self.refData[key] = value
            return
        self.refData[key] = BaseNBTView.pyObjectToNBTData(value, castType)

    def append(self, nbtData):
        if not isinstance(self.refData, list):
            raise RuntimeError("当前数据不是列表类型")
        self.refData.append(nbtData)

    def getSize(self):
        return len(self.refData)

class EnchantType:
    ArmorAll = 0
    """ 保护 """
    ArmorFire = 1
    """ 火焰保护 """
    ArmorFall = 2
    """ 摔落保护 """
    ArmorExplosive = 3
    """ 爆炸保护 """
    ArmorProjectile = 4
    """ 弹射物保护 """
    ArmorThorns = 5
    """ 荆棘 """
    WaterBreath = 6
    """ 水下呼吸 """
    WaterSpeed = 7
    """ 深海探索者 """
    WaterAffinity = 8
    """ 水下速掘 """
    WeaponDamage = 9
    """ 锋利 """
    WeaponUndead = 10
    """ 亡灵杀手 """
    WeaponArthropod = 11
    """ 节肢杀手 """
    WeaponKnockback = 12
    """ 击退 """
    WeaponFire = 13
    """ 火焰附加 """
    WeaponLoot = 14
    """ 抢夺 """
    MiningEfficiency = 15
    """ 效率 """
    MiningSilkTouch = 16
    """ 精准采集 """
    MiningDurability = 17
    """ 耐久 """
    MiningLoot = 18
    """ 时运 """
    BowDamage = 19
    """ 力量 """
    BowKnockback = 20
    """ 冲击 """
    BowFire = 21
    """ 火矢 """
    BowInfinity = 22
    """ 无限 """
    FishingLoot = 23
    """ 海之眷顾 """
    FishingLure = 24
    """ 饵钓 """
    FrostWalker = 25
    """ 冰霜行者 """
    Mending = 26
    """ 经验修补 """
    CurseBinding = 27
    """ 绑定诅咒 """
    CurseVanishing = 28
    """ 消失诅咒 """
    TridentImpaling = 29
    """ 穿刺 """
    TridentRiptide = 30
    """ 激流 """
    TridentLoyalty = 31
    """ 忠诚 """
    TridentChanneling = 32
    """ 引雷 """
    CrossbowMultishot = 33
    """ 多重射击 """
    CrossbowPiercing = 34
    """ 穿透 """
    CrossbowQuickCharge = 35
    """ 快速装填 """
    SoulSpeed = 36
    """ 灵魂疾行 """
    SwiftSneak = 37
    """ 迅捷潜行 """
    NumEnchantments = 38
    """ 附魔种数 """
    InvalidEnchantment = 39
    """ 无效附魔 """
    ModEnchant = 255
    """ 自定义附魔 """

class EnchNBTView(BaseNBTView):
    """ 附魔NBT视图 """
    class EnchStruct:
        """ 附魔数据结构 """
        def __init__(self, enchId=0, level=1, modEnchant=""):
            self.enchId = enchId
            self.level = level
            self.modEnchant = modEnchant
        
        @staticmethod
        def loadFromNBTDic(dic):
            # type: (dict) -> EnchNBTView.EnchStruct
            view = BaseNBTView(dic)
            enchId = view.getKey("id", 0)
            level = view.getKey("lvl", 0)
            modEnchant = view.getKey("modEnchant", "")
            return EnchNBTView.EnchStruct(enchId, level, modEnchant)

        def toNBTView(self):
            # type: () -> BaseNBTView
            """ 转换为NBT视图对象 """
            view = BaseNBTView()
            view.setKey("id", self.enchId, NBT_TYPE.SHORT)
            view.setKey("lvl", self.level, NBT_TYPE.SHORT)
            view.setKey("modEnchant", self.modEnchant, NBT_TYPE.STRING)
            return view

        def toNBTDict(self):
            # type: () -> dict
            """ 转换为NBT字典 """
            return self.toNBTView().getDataRef()

        def __eq__(self, other):
            if not isinstance(other, EnchNBTView.EnchStruct):
                return False
            return (
                self.enchId == other.enchId and
                self.level == other.level and
                self.modEnchant == other.modEnchant
            )

        def __hash__(self):
            return hash((self.enchId, self.level, self.modEnchant))
        
        def getSignedId(self):
            """ 获取识别ID """
            return self.modEnchant or self.enchId

    def walk(self):
        """ 附魔数据生成器 """
        for nbtEnch in self.refData:
            yield EnchNBTView.EnchStruct.loadFromNBTDic(nbtEnch)

    def addEnchData(self, enchId=0, level=1, modEnchant=""):
        """ 添加附魔数据(不会检查重复) """
        return self.addEnchStruct(EnchNBTView.EnchStruct(enchId, level, modEnchant))

    def addEnchStruct(self, data):
        # type: (EnchNBTView.EnchStruct) -> None
        """ 添加附魔数据结构(不会检查重复) """
        self.append(data.toNBTDict())

    def removeEnchantmentsByIds(self, enchIds=[]):
        """ 批量移除指定附魔ID数据（若存在） """
        removeDatas = set(enchIds)
        def removeEnch(ench):
            # type: (EnchNBTView.EnchStruct) -> EnchNBTView.EnchStruct | None
            if ench.enchId in removeDatas:
                return None
            return ench
        self.processEach(removeEnch)

    def setEnchantments(self, enchViews=[]):
        # type: (list[EnchNBTView.EnchStruct]) -> None
        """ 批量新增/修改附魔数据（支持原版/自定义附魔，若附魔等级<=0则视为丢弃） """
        setViewMaps = {}    # type: dict[str | int, EnchNBTView.EnchStruct]
        for ench in enchViews:
            setViewMaps[ench.getSignedId()] = ench
        def setEnch(ench):
            # type: (EnchNBTView.EnchStruct) -> EnchNBTView.EnchStruct | None
            signed = ench.getSignedId()
            if signed in setViewMaps:
                # 修改数据
                newData = setViewMaps[signed]
                del setViewMaps[signed]
                if newData.level <= 0:
                    # 丢弃数据
                    return None
                return newData
            return ench
        self.processEach(setEnch)
        # 添加新数据
        for ench in setViewMaps.values():
            if ench.level > 0:
                # 添加数据
                self.addEnchStruct(ench)

    def hasEnchantmentById(self, enchId=0):
        """ 检查是否存在指定附魔ID数据。（若需批量操作建议使用processEach） """
        for ench in self.walk():
            if ench.enchId == enchId:
                return True
        return False

    def processEach(self, func=lambda data: data):
        """ 使用用户提供的函数处理每个附魔数据，并返回新的附魔数据列表（若返回None代表移除特定附魔）。 """
        newNBTList = []
        for ench in self.walk():
            newData = func(ench)    # type: EnchNBTView.EnchStruct | None
            if newData:
                newNBTList.append(newData.toNBTDict())
        # 重新分配内存
        newSize = len(newNBTList)
        oldSize = len(self.refData)
        if newSize > oldSize:
            # 扩容
            self.refData.extend([None] * (newSize - oldSize))
        elif newSize < oldSize:
            # 收缩
            for _ in range(oldSize - newSize):
                self.refData.pop()
        # 替换原数据
        for i, data in enumerate(newNBTList):
            self.refData[i] = data
    
    def clearAll(self):
        refData = self.refData
        while refData:
            refData.pop()

class _ItemData:
    NULL_ITEM = "minecraft:air"
    def __init__(self, dicArgs = {}, userId = None, index = -1):
        # type: (dict | None, str | None, int) -> None
        self._dicArgs = dicArgs
        self.index = index
        """ 物品下标索引 通常指背包位置 仅特定方法拿到的物品信息才会持有该属性 """
        self.userId = userId
        """ 用户ID 通常指持有者玩家 """
        self.empty = False          # type: bool
        """ 是否为空物品 当物品为空气/数量参数为0时视为空物品 """
        self.newItemName = ""       # type: str
        """ 物品标识符名称 """
        self.newAuxValue = 0        # type: int
        """ 物品附加值 """
        self.count = 0              # type: int
        """ 物品数量 """
        self.extraId = ""           # type: str
        """ 物品自定义标识符 """
        self.durability = 0         # type: int
        """ 剩余耐久值 若物品本身无耐久则始终为0 """
        self.customTips = ""        # type: str
        """ 自定义Tips说明 """
        self.userData = {}
        """ 物品userData 需主动表明获取userData否则始终为空 """
        self.enchantData = []
        """ 游戏原版附魔数据 暂不支持操作 """
        self.modEnchantData = []
        """ MOD自定义附魔数据 暂不支持操作 """
        self.itemUpdate()
    
    def getEnchantState(self):
        """ 获取是否为附魔状态 """
        return len(self.enchantData) > 0 or len(self.modEnchantData) > 0

    @classmethod
    def create(cls):
        return cls()
    
    def __str__(self):
        return "<{}.{} {} ({})>".format(self.__class__.__name__, id(self), self.getFormatItemName(), self.count)
    
    def getDict(self):
        """ 获取并拷贝一份dict参数 """
        if self._dicArgs == None:
            return self.__class__.createItemData(_ItemData.NULL_ITEM, 0).getDict()
        return {k:v for k, v in self._dicArgs.items()}
    
    def getJSONData(self):
        if self.empty:
            return None
        return self.getDict()
    
    @classmethod
    def createItemData(cls, itemName="", count=1, aux=0):
        """ 快速创建一个简易物品参数 """
        return cls(
            {
                "newItemName": itemName,
                "itemName": itemName,
                "count": count,
                "newAuxValue": aux,
                "aux": aux
            }
        )

    def equal(self, otherItem):
        # type: (_ItemData) -> bool
        """ 比较与另外一个物品是否相当 相同物品不同数据参数也会视为不同 """
        if otherItem.empty or self.empty:
            # 空物品不与任何物品相当
            return False
        return (
            otherItem.newItemName == self.newItemName and
            otherItem.newAuxValue == self.newAuxValue and
            otherItem.durability == self.durability and
            otherItem.customTips == self.customTips and
            otherItem.extraId == self.extraId and
            otherItem.userData == self.userData and
            otherItem.enchantData == self.enchantData and
            otherItem.modEnchantData == self.modEnchantData
        )
    
    def identical(self, otherItem):
        # type: (_ItemData) -> bool
        """ 完整比较与另外一个物品是否相同，包括数量 """
        return self.equal(otherItem) and self.count == otherItem.count

    def getFormatItemName(self):
        """ 获取格式化后的物品名称 统一空物品值 """
        if not self.newItemName:
            return _ItemData.NULL_ITEM
        return self.newItemName
    
    def getItemBasicInfo(self):
        # type: () -> _ItemBasicInfo
        """ 获取物品基础信息 """
        return _ItemBasicInfo(self.newItemName, self.newAuxValue)

    def itemUpdate(self):
        """ 更新计算物品属性 """
        dicArgs = self._dicArgs
        if dicArgs == None:
            self.empty = True
        else:
            self.newItemName = dicArgs.get("newItemName", "")
            if self.newItemName == _ItemData.NULL_ITEM:
                self.empty = True
                return
            self.newAuxValue = dicArgs.get("newAuxValue", 0)
            self.count = dicArgs.get("count", 0)
            if self.count <= 0:
                self.empty = True
                return
            self.extraId = dicArgs.get("extraId", "")
            self.durability = dicArgs.get("durability", 0)
            self.customTips = dicArgs.get("customTips", "")
            self.userData = dicArgs.get("userData", {})
            self.enchantData = dicArgs.get("enchantData", [])
            self.modEnchantData = dicArgs.get("modEnchantData", [])
    
    def setItemName(self, itemName=None):
        """ 设置物品标识符 """
        if not itemName or itemName == _ItemData.NULL_ITEM:
            self.newItemName = _ItemData.NULL_ITEM
            self._dicArgs = None
            self.empty = True
            return
        if self._dicArgs == None:
            self._dicArgs = {}
        self._dicArgs["newItemName"] = itemName
        self._dicArgs["itemName"] = itemName
        if not "newAuxValue" in self._dicArgs:
            self._dicArgs["newAuxValue"] = 0
            self.newAuxValue = 0
        self.newItemName = itemName
        self.itemUpdate()

    def setItemAux(self, aux=0):
        """ 设置物品Aux 空物品无效 """
        if self.empty:
            return False
        self.newAuxValue = aux
        self._dicArgs["newAuxValue"] = aux
        return True

    def nameIsNull(self, name=""):
        return not name or name == _ItemData.NULL_ITEM
    
    def setCount(self, count=0):
        # type: (int) -> bool
        """ 设置物品数量 超过最大堆叠值将视为最大值 """
        if self.empty and self.nameIsNull(self.newItemName):
            return False
        maxCount = self.getItemBasicInfo().maxStackSize
        _count = min(maxCount, count)
        self._dicArgs["count"] = _count
        self.count = _count
        if self.count <= 0:
            self.empty = True
        elif self.count > 0 and not self.nameIsNull(self.newItemName):
            self.empty = False
        return True
    
    def setDurability(self, durability=0):
        # type: (int) -> bool
        """ 设置物品耐久值 超过最大值将视为最大值 """
        if self.empty:
            return False
        maxValue = self.getItemBasicInfo().maxDurability
        _durability = min(durability, maxValue)
        self._dicArgs["durability"] = _durability
        self.durability = _durability
        return True
    
    def setCustomTips(self, newCustomTips=""):
        """ 设置物品自定义Tips """
        if self.empty:
            return False
        self._dicArgs["customTips"] = newCustomTips
        self.customTips = newCustomTips
    
    def setExtraId(self, extraId=""):
        """ 设置物品自定义标识符 """
        if self.empty:
            return False
        self.extraId = extraId
        self._dicArgs["extraId"] = extraId
    
    def setUserData(self, userData={}):
        """ 设置用户参数 根据文档说明该参数存放附魔 颜色等相关原版数据 请勿随意操作 """
        if self.empty:
            return False
        self.userData = userData
        self._dicArgs["userData"] = userData
    
    def getJSONExtraId(self):
        # type: () -> dict
        """ 获取extraId并转换为JSON """
        from json import loads
        try:
            return loads(self.extraId)
        except Exception:
            pass
        return {}

    def setJSONExtraId(self, joData={}, ensureAscii=True):
        # type: (dict, bool) -> None
        """ 设置JSONExtraId """
        from json import dumps
        newStr = dumps(joData, ensure_ascii=ensureAscii)
        self.setExtraId(newStr)
    
    def fetchOrInitNBTData(self, key, defaultValue=None):
        # type: (str, dict | list | None) -> dict
        """ 获取并初始化指定的NBT数据层 """
        if not key in self.userData:
            if defaultValue is None:
                defaultValue = dict()
            self.userData[key] = defaultValue
            self.setUserData(self.userData)
        return self.userData[key]

    def createNBTDataView(self, key, defaultValue=None):
        # type: (str, dict | list | None) -> BaseNBTView
        """ 获取并初始化指定的NBT数据层视图 """
        return BaseNBTView(self.fetchOrInitNBTData(key, defaultValue))

    def getEnchNBTView(self):
        """ 获取附魔NBT视图, 可通过视图直接操作数据。 """
        return EnchNBTView(self.fetchOrInitNBTData("ench", []))

    def getNBTView(self):
        """ 获取NBT视图，可通过视图直接操作数据。 """
        if not self._dicArgs.get("userData", None) is self.userData:
            self.setUserData(dict())
        return BaseNBTView(self.userData)

class _InventoryData:
    """ 背包物品信息 """
    USE_ITEM_CLS = _ItemData
    def __init__(self, _size = 27, _userId = None):
        # type: (int, str | None) -> None
        self._size = _size
        """ 背包最大容量 """
        self._inventoryList = []    # type: list[_ItemData]
        """ 背包信息列表 """
        self._userId = _userId
        """ 用户ID 通常指持有者实体 """

    def __str__(self):
        return "<{}.{} {}>".format(self.__class__.__name__, id(self), [str(x) for x in self._inventoryList])

    def dumps(self):
        """ 返回格式化后的JSON数据 """
        return {
            "u": self._userId,
            "s": self._size,
            "i": [x.getJSONData() for x in self.walk()]
        }

    def getSize(self):
        return self._size
    
    def moveItemTo(self, moveIndex, otherInventoryData, otherIndex = 0):
        # type: (int, _InventoryData, int) -> int
        """ 尝试将一栏物品移动到另外一个背包的特定位置 返回移动后剩余未移动成功的数值当数值为0视为完全移动完毕 """
        otherItemData = otherInventoryData.getItem(otherIndex)
        myItem = self.getItem(moveIndex)
        if myItem.empty:
            # 当前移动物品是空的 不允许移动操作
            return myItem.count
        if otherItemData.empty:
            # 对方背包物品为空 完整移动
            if otherItemData.nameIsNull():
                # 对方为空物品栏 重新绘算
                otherItemData = otherItemData.__class__(myItem.getDict(), myItem.userId)
                otherItemData.setCount(0)
                otherInventoryData._inventoryList[otherIndex] = otherItemData
            otherItemData.setCount(otherItemData.count + myItem.count)
            myItem.setCount(myItem.count - otherItemData.count)
            return myItem.count
        if not myItem.equal(otherItemData):
            # 两种物品截然不同禁止移动堆叠
            return myItem.count
        # 两种物品相同且都不为空并有一定默认数量
        beforeOtherCount = otherItemData.count    # 移动之前对方持有数量
        otherItemData.setCount(beforeOtherCount + myItem.count)
        afterOtherCount = otherItemData.count     # 移动之后对方持有数量
        useCount = afterOtherCount - beforeOtherCount
        myItem.setCount(myItem.count - useCount)
        return myItem.count

    def exchangeItemTo(self, myIndex, otherInventoryData, otherIndex = 0):
        # type: (int, _InventoryData, int) -> None
        """ 交换两个背包的物品，若类型不相同则维持类型重新构造。 """
        otherItemData = otherInventoryData.getItem(otherIndex)
        myItem = self.getItem(myIndex)
        # 维护class类型一致性
        OtherItemCls = otherItemData.__class__
        MyItemCls = myItem.__class__
        # 同类型直接交换
        if MyItemCls is OtherItemCls:
            self._inventoryList[myIndex] = otherItemData
            otherInventoryData._inventoryList[otherIndex] = myItem
            return
        # 不同类型重新构造
        item1 = MyItemCls(otherItemData.getDict(), otherItemData.userId)
        item2 = OtherItemCls(myItem.getDict(), myItem.userId)
        self._inventoryList[myIndex] = item1
        otherInventoryData._inventoryList[otherIndex] = item2
    
    def simulatedOperation(self, _index, toInventoryData, toIndex):
        # type: (int, _InventoryData | None, int) -> tuple[_ItemData, _ItemData, int]
        """ 模拟操作背包物品 是moveItemTo与exchangeItemTo的整合
            @return - 将返回带有index操作后的 (原卡槽对象, Other卡槽对象, 状态码)

            状态码:
                0 移动叠加
                1 交换物品
        """
        toInventoryData = toInventoryData or self
        myItem = self.getItem(_index)
        beforeCount = myItem.count      # 移动之前数量
        self.moveItemTo(_index, toInventoryData, toIndex)
        lastCount = myItem.count        # 移动后剩余数量
        state = 0                       # 操作状态
        if beforeCount == lastCount:
            # 没有任何成功性的移动 尝试交换物品
            self.exchangeItemTo(_index, toInventoryData, toIndex)
            state = 1
        return (self.getItem(_index), toInventoryData.getItem(toIndex), state)

    def simulatedOperation2(self, index, toInventoryData, toIndex):
        # type: (int, _InventoryData, int) -> tuple[_ItemData, _ItemData, int]
        """ 模拟背包操作，反转封装版本，适用于GUI逻辑。 """
        return self.simulatedOperation(toIndex, toInventoryData, index)

    def moveSomeItemsTo(self, moveIndex, moveMaxCount, otherInventoryData, otherIndex = 0):
        # type: (int, int, _InventoryData, int) -> int
        """ 尝试将一部分物品移动到另外一个背包的特定位置 模拟长按移动部分物品操作 """
        myItem = self.getItem(moveIndex)
        if myItem.count <= moveMaxCount:
            # 待移动的总数量小于最大移动数量 直接完整移动
            return self.moveItemTo(moveIndex, otherInventoryData, otherIndex)
        oldCount = myItem.count                 # 原先数量
        myItem.setCount(moveMaxCount)           # 设置为需要移动数量
        notUseCount = oldCount - myItem.count   # 未选中移动数量
        _back = self.moveItemTo(moveIndex, otherInventoryData, otherIndex)  # 移动后剩余数量
        myItem.setCount(notUseCount + _back)    # 合并剩余原物品数量
        return myItem.count
    
    @classmethod
    def loads(cls, _json):
        # type: (dict) -> _InventoryData
        """ 从JSON数据加载回对象 """
        _userId = _json.get("u", None)
        _size = _json.get("s", 0)
        _inventoryList = _json.get("i", [])
        iv = cls.loadItemDictList(_inventoryList, _userId)
        iv._size = _size
        return iv

    @classmethod
    def loadItemDictList(cls, itemDictList = [], userId = None):
        # type: (list[dict | None], str | None) -> _InventoryData
        """ 加载物品字典列表 """
        inventoryData = cls(len(itemDictList), userId)
        for itemDict in itemDictList:
            inventoryData._inventoryList.append(
                cls.USE_ITEM_CLS(itemDict, userId)
            )
        return inventoryData

    @classmethod
    def createOptInventoryDataWithIndexItems(cls, *args):
        # type: (_ItemData) -> _InventoryData
        """ 基于一部分带有index上下文的物品构造一个临时背包用于操作 对于提供的ItemData将视为待操作对象 因此会强制认定为非empty """
        maxLength = 0
        for obj in args:
            maxLength = max(obj.index + 1, maxLength)
        newInventory = cls(maxLength)
        newInventory.initItemList()
        for itemData in args:
            newObj = None
            if itemData.empty:
                newObj = cls.USE_ITEM_CLS.createItemData(
                    _ItemData.NULL_ITEM, 0
                )
            else:
                newObj = cls.USE_ITEM_CLS(
                    itemData.getDict()
                )
            newInventory._inventoryList[itemData.index] = newObj
            newObj.empty = False
            newObj.index = itemData.index
        return newInventory

    def getItemsDictMap(self, itemPosType = 0, leaveBlankValues = False):
        # type: (int, bool) -> dict[tuple[int, int], dict]
        """ 获取批物品字典
            leaveBlankValues 设置为True时将会保留空物品
        """
        itemDictMap = {}
        for obj in self.walk():
            if not leaveBlankValues and obj.empty:
                continue
            itemDictMap[(itemPosType, obj.index)] = obj.getDict()
        return itemDictMap

    def initItemList(self):
        """ 初始化物品列表 当列表元素数目与总背包数目不足时将会补足为空 """
        for _ in range(len(self._inventoryList), self._size):
            self._inventoryList.append(self.createNullItem())
    
    def toDicList(self):
        """ 返回物品列表 """
        return [item.getDict() for item in self.walk()]
    
    def walk(self):
        """ 返回一个物品背包生成器以便遍历操作 """
        for i in range(self._size):
            yield self.getItem(i)

    def getItem(self, _index):
        # type: (int) -> _ItemData
        """ 基于下标索引获取物品 """
        if _index >= self._size:
            raise Exception("超出背包物品最大值")
        if _index >= len(self._inventoryList):
            # 索引超出列表持有范围 进行补全
            self.initItemList()
        itemData = self._inventoryList[_index]
        itemData.index = _index
        return itemData
    
    def createNullItem(self):
        """ 创建一个空物品对象 """
        return self.__class__.USE_ITEM_CLS.createItemData(_ItemData.NULL_ITEM, 0)
