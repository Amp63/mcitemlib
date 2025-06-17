from mcitemlib.itemlib import Item, SlotItem


def test_shulker_methods():
    def slot_test(contents: list[SlotItem], slot: int, id: str, count: int):
        slot_item = next((i for i in contents if i['slot'] == slot), None)['item']
        assert slot_item is not None
        assert slot_item.get_id() == id
        assert slot_item.get_count() == count

    SHULKER_NBT = """{components:{"minecraft:container":[{item:{count:64,id:"minecraft:diamond"},slot:0},{item:{count:21,id:"minecraft:gold_ingot"},slot:5},{item:{count:21,id:"minecraft:gold_ingot"},slot:6},{item:{count:11,id:"minecraft:gold_ingot"},slot:7},{item:{count:11,id:"minecraft:gold_ingot"},slot:8},{item:{count:32,id:"minecraft:iron_ingot"},slot:11},{item:{count:32,id:"minecraft:iron_ingot"},slot:22}]},count:1,id:"minecraft:red_shulker_box"}"""
    item1 = Item.from_snbt(SHULKER_NBT)
    contents = item1.get_shulker_box_contents()
    assert len(contents) == 7
    slot_test(contents, 11, 'minecraft:iron_ingot', 32)
    
    item2 = Item('blue_shulker_box')
    item2.set_shulker_box_contents(contents)
    slot_test(item2.get_shulker_box_contents(), 6, 'minecraft:gold_ingot', 21)

    custom_contents = [
        {'slot': 2, 'item': Item('apple', 5)},
        {'slot': 10, 'item': Item('wooden_sword')},
        {'slot': 15, 'item': Item('ender_pearl', 16)}
    ]
    item3 = Item('yellow_shulker_box')
    item3.set_shulker_box_contents(custom_contents)
    got_contents = item3.get_shulker_box_contents()
    assert len(got_contents) == 3
    slot_test(got_contents, 10, 'minecraft:wooden_sword', 1)
