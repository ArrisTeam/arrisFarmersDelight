# -*- coding: utf-8 -*-
"""CookingPotRecipes - 厨锅配方表（双端，纯数据）

每条配方：Recipe（若干变体，每个变体最多 6 个 (物品名, aux)）、CookResult、
Vessel（盛出成品需要的容器，可缺省）、PushItem（出料时吐出的余料）、text（界面显示名）。
查表索引见 Shared/Rules/CookingPot.py；表被修改后要调用它的 rebuildIndex()。
"""
# 厨锅配方
CookingPotRecipeList = [
    {
        "Recipe": [
            [
                ("minecraft:red_mushroom", 0),
                ("minecraft:red_mushroom", 0)
            ],
            [
                ("minecraft:brown_mushroom", 0),
                ("minecraft:brown_mushroom", 0)
            ],
            [
                ("minecraft:red_mushroom", 0),
                ("minecraft:brown_mushroom", 0)
            ]
        ],
        "CookResult": ("minecraft:mushroom_stew", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "蘑菇煲"
    },
    {
        "Recipe": [
            [
                ("minecraft:beetroot", 0),
                ("minecraft:beetroot", 0),
                ("minecraft:beetroot", 0)
            ]
        ],
        "CookResult": ("minecraft:beetroot_soup", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "甜菜汤"
    },
    {
        "Recipe": [
            [
                ("minecraft:rabbit", 0),
                ("minecraft:red_mushroom", 0),
                ("minecraft:potato", 0),
                ("minecraft:carrot", 0)
            ],
            [
                ("minecraft:rabbit", 0),
                ("minecraft:brown_mushroom", 0),
                ("minecraft:potato", 0),
                ("minecraft:carrot", 0)
            ]
        ],
        "CookResult": ("minecraft:rabbit_stew", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "兔肉煲"
    },
    {
        "Recipe": [
            [
                ("arris:tomato", 0),
                ("arris:tomato", 0)
            ]
        ],
        "CookResult": ("arris:tomato_sauce", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "番茄酱"
    },
    {
        "Recipe": [
            [
                ("arris:rice", 0)
            ]
        ],
        "CookResult": ("arris:cooked_rice", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "米饭"
    },
    {
        "Recipe": [
            [
                ("arris:rice", 0),
                ("minecraft:egg", 0),
                ("minecraft:carrot", 0),
                ("arris:onion", 0),
            ]
        ],
        "CookResult": ("arris:fried_rice", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "炒饭"
    },
    {
        "Recipe": [
            [
                ("arris:wheat_dough", 0),
                ("arris:cabbage_leaf", 0),
                ("arris:onion", 0),
                ("arris:bacon", 0)
            ],
            [
                ("arris:wheat_dough", 0),
                ("arris:cabbage_leaf", 0),
                ("arris:onion", 0),
                ("arris:minced_beef", 0)
            ],
            [
                ("arris:wheat_dough", 0),
                ("arris:cabbage_leaf", 0),
                ("arris:onion", 0),
                ("arris:cod_slice", 0)
            ],
            [
                ("arris:wheat_dough", 0),
                ("arris:cabbage_leaf", 0),
                ("arris:onion", 0),
                ("arris:salmon_slice", 0)
            ]
        ],
        "CookResult": ("arris:dumplings", 0),
        "Vessel": ("arris:cabbage_leaf", 0),
        "PushItem": [
        ],
        "text": "饺子"
    },
    {
        "Recipe": [
            [
                ("arris:minced_beef", 0),
                ("arris:raw_pasta", 0),
                ("arris:tomato", 0)
            ]
        ],
        "CookResult": ("arris:pasta_with_meatballs", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "肉丸意面"
    },
    {
        "Recipe": [
            [
                ("arris:mutton_chops", 0),
                ("arris:raw_pasta", 0),
                ("arris:tomato", 0)
            ]
        ],
        "CookResult": ("arris:pasta_with_mutton_chop", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "羊排意面"
    },
    {
        "Recipe": [
            [
                ("minecraft:brown_mushroom", 0),
                ("minecraft:red_mushroom", 0),
                ("arris:rice", 0),
                ("minecraft:potato", 0),
            ],
            [
                ("minecraft:brown_mushroom", 0),
                ("minecraft:brown_mushroom", 0),
                ("arris:rice", 0),
                ("minecraft:potato", 0),
            ],
            [
                ("minecraft:red_mushroom", 0),
                ("minecraft:red_mushroom", 0),
                ("arris:rice", 0),
                ("minecraft:potato", 0),
            ],
            [
                ("minecraft:brown_mushroom", 0),
                ("minecraft:red_mushroom", 0),
                ("arris:rice", 0),
                ("minecraft:carrot", 0),
            ],
            [
                ("minecraft:brown_mushroom", 0),
                ("minecraft:brown_mushroom", 0),
                ("arris:rice", 0),
                ("minecraft:carrot", 0),
            ],
            [
                ("minecraft:red_mushroom", 0),
                ("minecraft:red_mushroom", 0),
                ("arris:rice", 0),
                ("minecraft:carrot", 0),
            ]
        ],
        "CookResult": ("arris:mushroom_rice", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "蘑菇饭"
    },
    {
        "Recipe": [
            [
                ("minecraft:brown_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("minecraft:potato", 0),
            ],
            [
                ("minecraft:red_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("minecraft:potato", 0),
            ],
            [
                ("minecraft:brown_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("minecraft:carrot", 0),
            ],
            [
                ("minecraft:red_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("minecraft:carrot", 0),
            ],
            [
                ("minecraft:brown_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("minecraft:beetroot", 0),
            ],
            [
                ("minecraft:red_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("minecraft:beetroot", 0),
            ],
            [
                ("minecraft:brown_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("arris:onion", 0),
            ],
            [
                ("minecraft:red_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("arris:onion", 0),
            ],
            [
                ("minecraft:brown_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("arris:tomato", 0),
            ],
            [
                ("minecraft:red_mushroom", 0),
                ("arris:raw_pasta", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("arris:tomato", 0),
            ]
        ],
        "CookResult": ("arris:vegetable_noodles", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "蔬菜面"
    },
    {
        "Recipe": [
            [
                ("arris:tomato", 0),
                ("arris:onion", 0),
                ("minecraft:beetroot", 0),
                ("minecraft:carrot", 0)
            ],
            [
                ("arris:tomato", 0),
                ("arris:onion", 0),
                ("minecraft:beetroot", 0),
                ("minecraft:beetroot", 0)
            ],
            [
                ("arris:tomato", 0),
                ("arris:onion", 0),
                ("minecraft:beetroot", 0),
                ("minecraft:potato", 0)
            ],
            [
                ("arris:tomato", 0),
                ("arris:onion", 0),
                ("minecraft:beetroot", 0),
                ("arris:onion", 0)
            ],
            [
                ("arris:tomato", 0),
                ("arris:onion", 0),
                ("minecraft:beetroot", 0),
                ("arris:tomato", 0)
            ]
        ],
        "CookResult": ("arris:ratatouille", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "蔬菜杂烩"
    },
    {
        "Recipe": [
            [
                ("arris:cod_slice", 0),
                ("arris:raw_pasta", 0),
                ("arris:tomato", 0),
                ("minecraft:ink_sac", 0)
            ],
            [
                ("arris:salmon_slice", 0),
                ("arris:raw_pasta", 0),
                ("arris:tomato", 0),
                ("minecraft:ink_sac", 0)
            ]
        ],
        "CookResult": ("arris:squid_ink_pasta", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "鱿鱼墨面"
    },
    {
        "Recipe": [
            [
                ("arris:rice", 0),
                ("minecraft:brown_mushroom", 0),
                ("minecraft:potato", 0),
                ("minecraft:sweet_berries", 0),
                ("minecraft:carrot", 0),
                ("arris:onion", 0)
            ],
            [
                ("arris:rice", 0),
                ("minecraft:red_mushroom", 0),
                ("minecraft:potato", 0),
                ("minecraft:sweet_berries", 0),
                ("minecraft:carrot", 0),
                ("arris:onion", 0)
            ],
            [
                ("arris:rice", 0),
                ("minecraft:brown_mushroom", 0),
                ("minecraft:potato", 0),
                ("minecraft:glow_berries", 0),
                ("minecraft:beetroot", 0),
                ("arris:onion", 0)
            ],
            [
                ("arris:rice", 0),
                ("minecraft:red_mushroom", 0),
                ("minecraft:potato", 0),
                ("minecraft:glow_berries", 0),
                ("minecraft:beetroot", 0),
                ("arris:onion", 0)
            ],
            [
                ("arris:rice", 0),
                ("minecraft:brown_mushroom", 0),
                ("minecraft:potato", 0),
                ("minecraft:sweet_berries", 0),
                ("arris:onion", 0),
                ("arris:tomato", 0)
            ],
            [
                ("arris:rice", 0),
                ("minecraft:red_mushroom", 0),
                ("minecraft:potato", 0),
                ("minecraft:sweet_berries", 0),
                ("arris:onion", 0),
                ("arris:tomato", 0)
            ],
        ],
        "CookResult": ("arris:stuffed_pumpkin_block_stage0", 0),
        "Vessel": ("minecraft:pumpkin", 0),
        "PushItem": [
        ],
        "text": "填馅南瓜"
    },
    {
        "Recipe": [
            [
                ("arris:bacon", 0),
                ("arris:bacon", 0),
                ("arris:cabbage_leaf", 0)
            ],
            [
                ("arris:minced_beef", 0),
                ("arris:minced_beef", 0),
                ("arris:cabbage_leaf", 0)
            ],
            [
                ("arris:chicken_cuts", 0),
                ("arris:chicken_cuts", 0),
                ("arris:cabbage_leaf", 0)
            ],
            [
                ("arris:mutton_chops", 0),
                ("arris:mutton_chops", 0),
                ("arris:cabbage_leaf", 0)
            ],
            [
                ("arris:cod_slice", 0),
                ("arris:cod_slice", 0),
                ("arris:cabbage_leaf", 0)
            ],
            [
                ("arris:salmon_slice", 0),
                ("arris:salmon_slice", 0),
                ("arris:cabbage_leaf", 0)
            ]
        ],
        "CookResult": ("arris:cabbage_rolls", 0),
        "Vessel": ("arris:cabbage_leaf", 0),
        "PushItem": [
        ],
        "text": "卷心菜卷"
    },
    {
        "Recipe": [
            [
                ("minecraft:bone", 0),
                ("minecraft:brown_mushroom", 0)
            ],
            [
                ("minecraft:bone", 0),
                ("minecraft:red_mushroom", 0)
            ],
            [
                ("minecraft:bone", 0),
                ("minecraft:sweet_berries", 0)
            ],
            [
                ("minecraft:bone", 0),
                ("minecraft:glow_berries", 0)
            ]
        ],
        "CookResult": ("arris:bone_broth", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "大骨汤"
    },
    {
        "Recipe": [
            [
                ("arris:minced_beef", 0),
                ("minecraft:carrot", 0),
                ("minecraft:potato", 0)
            ]
        ],
        "CookResult": ("arris:cookbeef_stew", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "牛肉炖"
    },
    {
        "Recipe": [
            [
                ("arris:chicken_cuts", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("minecraft:potato", 0)
            ],
            [
                ("arris:chicken_cuts", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("minecraft:beetroot", 0)
            ],
            [
                ("arris:chicken_cuts", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("arris:onion", 0)
            ],
            [
                ("arris:chicken_cuts", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("arris:tomato", 0)
            ],
            [
                ("arris:chicken_cuts", 0),
                ("arris:cabbage_leaf", 0),
                ("minecraft:carrot", 0),
                ("arris:pumpkin_slice", 0)
            ]
        ],
        "CookResult": ("arris:chicken_soup", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "鸡肉汤"
    },
    {
        "Recipe": [
            [
                ("arris:cabbage_leaf", 0),
                ("minecraft:beetroot", 0),
                ("minecraft:carrot", 0),
                ("minecraft:potato", 0)
            ],
            [
                ("arris:cabbage_leaf", 0),
                ("arris:pumpkin_slice", 0),
                ("minecraft:carrot", 0),
                ("minecraft:potato", 0)
            ]
        ],
        "CookResult": ("arris:vegetable_soup", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "蔬菜汤"
    },
    {
        "Recipe": [
            [
                ("arris:cod_slice", 0),
                ("arris:tomato", 0),
                ("arris:onion", 0)
            ],
            [
                ("arris:salmon_slice", 0),
                ("arris:tomato", 0),
                ("arris:onion", 0)
            ]
        ],
        "CookResult": ("arris:fish_stew", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "鱼肉炖"
    },
    {
        "Recipe": [
            [
                ("arris:pumpkin_slice", 0),
                ("arris:cabbage_leaf", 0),
                ("arris:bacon", 0),
                ("arris:milk_bottle", 0)
            ]
        ],
        "CookResult": ("arris:pumpkin_soup", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
            ("minecraft:glass_bottle", 0)
        ],
        "text": "南瓜汤"
    },
    {
        "Recipe": [
            [
                ("arris:cod_slice", 0),
                ("minecraft:egg", 0),
                ("arris:tomato", 0),
                ("minecraft:potato", 0)
            ],
            [
                ("arris:cod_slice", 0),
                ("minecraft:egg", 0),
                ("arris:pumpkin_slice", 0),
                ("minecraft:potato", 0)
            ]
        ],
        "CookResult": ("arris:baked_cod_stew", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "烘焙鳕鱼炖"
    },
    {
        "Recipe": [
            [
                ("arris:raw_pasta", 0),
                ("minecraft:dried_kelp", 0),
                ("arris:fried_egg", 0),
                ("arris:bacon", 0)
            ],
            [
                ("arris:raw_pasta", 0),
                ("minecraft:dried_kelp", 0),
                ("arris:fried_egg", 0),
                ("arris:minced_beef", 0)
            ],
            [
                ("arris:raw_pasta", 0),
                ("minecraft:dried_kelp", 0),
                ("arris:fried_egg", 0),
                ("arris:cod_slice", 0)
            ],
            [
                ("arris:raw_pasta", 0),
                ("minecraft:dried_kelp", 0),
                ("arris:fried_egg", 0),
                ("arris:salmon_slice", 0)
            ]
        ],
        "CookResult": ("arris:noodle_soup", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "面条汤"
    },
    {
        "Recipe": [
            [
                ("arris:milk_bottle", 0),
                ("minecraft:cocoa_beans", 0),
                ("minecraft:cocoa_beans", 0),
                ("minecraft:sugar", 0)
            ]
        ],
        "CookResult": ("arris:hot_cocoa", 0),
        "Vessel": ("minecraft:glass_bottle", 0),
        "PushItem": [
            ("minecraft:glass_bottle", 0)
        ],
        "text": "热可可"
    },
    {
        "Recipe": [
            [
                ("minecraft:apple", 0),
                ("minecraft:apple", 0),
                ("minecraft:sugar", 0)
            ]
        ],
        "CookResult": ("arris:apple_cider", 0),
        "Vessel": ("minecraft:glass_bottle", 0),
        "PushItem": [
        ],
        "text": "苹果酒"
    },
    {
        "Recipe": [
            [
                ("minecraft:glow_berries", 0),
                ("minecraft:egg", 0),
                ("minecraft:sugar", 0),
                ("arris:milk_bottle", 0)
            ]
        ],
        "CookResult": ("arris:glow_berry_custard", 0),
        "Vessel": ("minecraft:glass_bottle", 0),
        "PushItem": [
            ("minecraft:glass_bottle", 0)
        ],
        "text": "发光浆果蛋奶沙司"
    },
    {
        "Recipe": [
            [
                ("minecraft:rotten_flesh", 0),
                ("minecraft:bone_meal", 0),
                ("arris:rice", 0),
                ("minecraft:chicken", 0)
            ]
        ],
        "CookResult": ("arris:dog_food", 0),
        "Vessel": ("minecraft:bowl", 0),
        "PushItem": [
        ],
        "text": "狗粮"
    }
]
