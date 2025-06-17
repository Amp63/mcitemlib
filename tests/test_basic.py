from mcitemlib.itemlib import Item


def test_init():
    assert Item('apple', 64).get_id() == 'minecraft:apple'
    assert Item('minecraft:diamond_sword').get_id() == 'minecraft:diamond_sword'
    assert Item('ender_pearl', 5).get_count() == 5


def test_from_snbt():
    assert Item.from_snbt('{count:1,id:"minecraft:diamond"}').get_id() == 'minecraft:diamond'
    assert Item.from_snbt('{id:"minecraft:stone",count:1}').get_id() == 'minecraft:stone'
    assert Item.from_snbt('{id:"minecraft:stone",Count:1b}').get_id() == 'minecraft:stone'


def test_getters():
    ITEM_NBT = """{components:{"minecraft:custom_name":'{"extra":[{"color":"red","text":"Test "},{"bold":true,"color":"gold","text":"Item"}],"italic":false,"text":""}',"minecraft:damage":50,"minecraft:enchantments":{levels:{"minecraft:efficiency":5,"minecraft:unbreaking":1}},"minecraft:lore":['{"bold":false,"color":"green","italic":false,"obfuscated":false,"strikethrough":false,"text":"Line 1","underlined":false}','{"bold":false,"color":"aqua","italic":false,"obfuscated":false,"strikethrough":false,"text":"Line 2","underlined":false}','{"bold":false,"color":"red","italic":false,"obfuscated":false,"strikethrough":false,"text":"Line 3","underlined":false}']},count:1,id:"minecraft:diamond_pickaxe"}"""
    item = Item.from_snbt(ITEM_NBT)
    assert item.get_id() == 'minecraft:diamond_pickaxe', 'Failed to get item id.'
    assert item.get_count() == 1, 'Failed to get item count.'
    assert item.get_durability() == 50, 'Failed to get item durability.'
    assert item.get_name().to_string() == 'Test Item', 'Failed to get item name.'
    assert item.get_lore()[1].to_string() == 'Line 2', 'Failed to get item lore.'
    assert item.get_enchantments()['minecraft:efficiency'] == 5, 'Failed to get item enchantments.'


def test_setters():
    item = Item('iron_pickaxe')
    item.set_id('gold_pickaxe')
    item.set_durability(20)
    item.set_name('&6Gold Pick')
    item.set_lore([
        '&dLine A', 
        '&eLine B',
        '&fLine C'
    ])
    item.set_enchantments({
        'efficiency': 3,
        'fortune': 2
    })

    assert item.get_id() == 'minecraft:gold_pickaxe', 'Failed to get item id.'
    assert item.get_count() == 1, 'Failed to get item count.'
    assert item.get_durability() == 20, 'Failed to get item durability.'
    assert item.get_name().to_string() == 'Gold Pick', 'Failed to get item name.'
    assert item.get_lore()[2].to_string() == 'Line C', 'Failed to get item lore.'
    assert item.get_enchantments()['minecraft:fortune'] == 2, 'Failed to get item enchantments.'
