# 兼容承诺与废弃流程

农夫乐事对做联动的模组作者承诺哪些接口保持兼容、兼容到什么程度，接口要废弃时怎么办。
用法见 [EXTENSION-API.md](EXTENSION-API.md)（新接口）和 [linkage.md](../linkage.md)（兼容入口），每次增减记在 [API-CHANGELOG.md](API-CHANGELOG.md)。

---

## 1. 两个版本号

| 版本号 | 取法 | 什么时候变 |
| --- | --- | --- |
| `hostVersion` | `ext.hostVersion`，形如 `(1, 0, 2)` | 农夫乐事每次发版都变，和 manifest 的 `header.version` 一样 |
| `apiVersion` | `ext.apiVersion`，ready 载荷里的 `"apiVersion"` 也是它 | 只在公共接口有破坏性变更时加一，新增接口不变。现在是 1 |

- 某个接口在不在，用 `ext.hasCapability(name)` 判断（能力名见 EXTENSION-API.md §3），不要拿版本号推。
- 农夫乐事够不够新（比如你依赖某一版才修好的行为），比 `hostVersion`；太旧时给玩家一句明确的提示。

---

## 2. 公共接口的范围

受本文承诺约束的：

1. **新接口**：ready 事件和它的载荷（EXTENSION-API.md §2 的命名空间、系统名、事件名，`arrisFarmersDelightScripts.Api.ExtensionApi.Events` 里的常量），
   `ext` 和 `ext.recipes`、`ext.tags` 上 EXTENSION-API.md 写明的成员（参数、返回值、错误码、行为），主动导入用的
   `arrisFarmersDelightScripts.Api.ExtensionApi.getExtensionApi`（和机械动力的兜底同一个写法）与原来的
   `arrisFarmersDelightScripts.Api.ExtensionApi.Facade.getExtensionApi`（EXTENSION-API.md §1.4）。
2. **配方 JSON 的写法**（[RECIPE-JSON.md](RECIPE-JSON.md)）和配方 ID 的规矩（EXTENSION-API.md §5.2），包括农夫乐事自带配方的 ID。
3. **兼容入口**：`CreateModAttr("arris")` 的三个函数 `ArrisFarmersDelightInterface` / `ArrisFarmersDelightObtain` / `ArrisAddCookingPotRecipe`，
   它们交出去的那些表（同一个对象，下游拿的是活引用）和表里原有的写法（linkage.md、`Shared/Data/` 里对应的文件）。不改不删，不再加新功能；
   表里以后可能多出可选的键（比如厨锅配方行的 `Id`、`Slots`，砧板条目的 `id`），读表的请按键名取、容忍多出来的键。
   **例外是厨锅配方行的 `Disabled`（墓碑）**：它改变这一行的含义——带 `"Disabled": True` 的行是被删掉的配方（行还留在表里，
   因为别处拿行的位置当身份），遍历 `CookingPotRecipeList` 时要跳过它；另外新接口登记的配方 `Recipe` 可能是空列表（只写了格子、展开不出写法）。
4. **标签词表**：[TAGS.md](TAGS.md) 列出的标签名（`common:` 和 `farmersdelight:`）和含义（成员会随版本增加）。

其余一律是内部实现，任何一次发版都可能改名、移动或删除，例如：`Server.*`、`Client.*`、`Compat.*`、`Shared.*` 下的模块和函数
（包括配方表的索引、表同步的消息格式）、以下划线开头的名字、方块实体数据的键名。能看到源码不等于可以依赖它；公共接口里缺你要的东西，见第 5 节。

---

## 3. 同一个 apiVersion 里只加不改

- **新增接口不升 `apiVersion`**：新方法、新的配方类型、新的登记口直接加，同时登记一个新的能力名，用 `hasCapability` 探测。
- **已有方法只在参数末尾加可选参数**，缺省值等于原来的行为；不改名，不调整已有参数的顺序和含义，不改已有返回值的含义。
  返回的字典以后可能多出新的键、新的错误码：按键名取值、看 `ok` 判断成败。
- **处理函数（`onRecipesChanged`）收到的 `event` 只加属性**，已有的 `types`、`recipeIds` 含义不变。
- **配方 JSON 只加可选的键**；已有的键含义不变。

做不到"只加不改"的（改名、删除、改含义）一律走第 4 节。

---

## 4. 废弃流程

1. **标注**：在接口所在的文档小节和 API-CHANGELOG.md 里标"废弃"，写明替代用法、最早可能删除的版本。
2. **保留**：标注之后至少保留 2 个发版（按 `hostVersion` 算，标注的那一版算第 1 个）。例如 1.0.5 标废弃，1.0.6 仍保留，最早 1.0.7 删除。
3. **提示**：保留期间，每个调用方在日志里得到一次提示，写明替代用法。
4. **删除**：保留期满才删；删除时 `apiVersion` 加一，并记进 API-CHANGELOG.md。

只适用于第 2 节的公共接口；内部实现的改动不走这个流程。兼容入口（linkage.md）目前没有废弃计划。

---

## 5. 缺接口怎么办

公共接口里没有你要的能力时，提 issue 写清使用场景和你希望的调用方式（仓库：`ArrisTeam/arrisFarmersDelight`）。
新接口加进来之后按第 3 节保持兼容。在那之前请不要依赖内部模块：它们随时会变，农夫乐事升级一次你的联动就可能坏掉。
