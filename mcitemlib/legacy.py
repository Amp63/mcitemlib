"""
Basic support for converting legacy item nbt into modern component based nbt.

Supported components:
- `banner_patterns`
- `container`
- `custom_data`
- `custom_name`
- `damage`
- `enchantments`
- `lore`
- `stored_enchantments`
- `unbreakable`
- `writable_book_content`
- `written_book_content`
- `attribute_modifiers` (somewhat)
"""


from rapidnbt import (
    CompoundTag, ListTag,
    ByteTag, IntTag, StringTag
)


DATA_TAG_KEYS = {'Items', 'CustomPotionColor', 'LodestoneTracked', 'pages', 'author', 'ChargedProjectiles', 'BlockStateTag', 'HideFlags', 'Decorations', 'LodestoneDimension', 'DebugProperty', 'Unbreakable', 'Explosion', 'EntityTag', 'resolved', 'instrument', 'Charged', 'SkullOwner', 'Enchantments', 'display', 'Trim', 'StoredEnchantments', 'LodestonePos', 'map', 'Potion', 'BucketVariantTag', 'AttributeModifiers', 'Fireworks', 'custom_potion_effects', 'filtered_pages', 'BlockEntityTag', 'RepairCost', 'filtered_title', 'map_to_lock', 'title', 'CustomModelData', 'CanDestroy', 'effects', 'Damage', 'CanPlaceOn', 'map_scale_direction', 'generation', 'Recipes'}

MODIFIER_OPERATIONS = [
    'add_value',
    'add_multiplied_base',
    'add_multiplied_total'
]

BANNER_PATTERNS = {
    'bl': 'square_bottom_left',
    'br': 'square_bottom_right',
    'tl': 'square_top_left',
    'tr': 'square_top_right',
    'bs': 'stripe_bottom',
    'ts': 'stripe_top',
    'ls': 'stripe_left',
    'rs': 'stripe_right',
    'cs': 'stripe_center',
    'ms': 'stripe_middle',
    'drs': 'stripe_downright',
    'dls': 'stripe_downleft',
    'ss': 'small_stripes',
    'cr': 'cross',
    'sc': 'straight_cross',
    'bt': 'triangle_bottom',
    'tt': 'triangle_top',
    'bts': 'triangles_bottom',
    'tts': 'triangles_top',
    'ld': 'diagonal_left',
    'rd': 'diagonal_up_right',
    'lud': 'diagonal_up_left',
    'rud': 'diagonal_right',
    'mc': 'circle',
    'mr': 'rhombus',
    'vh': 'half_vertical',
    'hh': 'half_horizontal',
    'vhr': 'half_vertical_right',
    'hhb': 'half_horizontal_bottom',
    'bo': 'border',
    'cbo': 'curly_border',
    'gra': 'gradient',
    'gru': 'gradient_up',
    'bri': 'bricks',
    'cre': 'creeper',
    'sku': 'skull',
    'flo': 'flower',
    'moj': 'mojang',
    'glb': 'globe',
    'pig': 'piglin'
}

BANNER_COLORS = [
    'white',
    'orange',
    'magenta',
    'light_blue',
    'yellow',
    'lime',
    'pink',
    'gray',
    'light_gray',
    'cyan',
    'purple',
    'blue',
    'brown',
    'green',
    'red',
    'black'
]


def _convert_attribute_modifiers(components_tag: CompoundTag, data_tag: CompoundTag):
    old_modifiers = data_tag['AttributeModifiers']
    if old_modifiers.is_null():
        return
    
    new_modifiers = ListTag()
    for old_modifier in old_modifiers:
        new_modifier = CompoundTag({
            'type': old_modifier['AttributeName'],
            'slot': old_modifier['Slot'],
            'amount': old_modifier['Amount']
        })
        new_operation = StringTag(MODIFIER_OPERATIONS[int(old_modifier['Operation'])])
        new_modifier['operation'] = new_operation
        new_modifiers.append(new_modifier)
    
    components_tag['minecraft:attribute_modifiers'] = new_modifiers


def _convert_damage_and_unbreakable(components_tag: CompoundTag, data_tag: CompoundTag):
    if 'Damage' in data_tag:
        components_tag['minecraft:damage'] = data_tag['Damage']
    
    unbreakable = data_tag['Unbreakable']
    if not unbreakable.is_null() and unbreakable.get_int():
        components_tag['minecraft:unbreakable'] = CompoundTag()


def _convert_enchantments(components_tag: CompoundTag, data_tag: CompoundTag):
    def convert_levels(old_enchants: ListTag):
        levels = CompoundTag()
        for old_enchant in old_enchants:
            old_enchant_id = str(old_enchant['id'])
            levels[old_enchant_id] = IntTag(int(old_enchant_id['lvl']))
        return levels

    old_enchants: ListTag = data_tag['Enchantments']
    if not old_enchants.is_null():
        enchant_levels = convert_levels(old_enchants)
        components_tag['minecraft:enchantments'] = enchant_levels
    
    old_stored_enchants: ListTag = data_tag['StoredEnchantments']
    if not old_stored_enchants.is_null():
        stored_enchant_levels = convert_levels(old_enchants)
        components_tag['minecraft:stored_enchantments'] = stored_enchant_levels


def _convert_writable_book(components_tag: CompoundTag, data_tag: CompoundTag):
    if 'author' in data_tag:  # Is a written book, so skip
        return
    
    old_pages = data_tag['Pages']
    if old_pages.is_null():
        return
    
    new_pages = ListTag()
    for old_page in old_pages:
        new_page = CompoundTag({
            'raw': old_page
        })
        new_pages.append(new_page)
    
    components_tag['minecraft:writable_book_content'] = CompoundTag({'pages': new_pages})


def _convert_written_book(components_tag: CompoundTag, data_tag: CompoundTag):
    old_pages = data_tag['Pages']
    if old_pages.is_null():
        return
    
    written_book_content = CompoundTag({
        'author': data_tag['author'],
        'title': CompoundTag({'raw': data_tag['title']}),
        'resolved': bool(int(data_tag['resolved'])),
        'generation': data_tag['generation']
    })

    new_pages = ListTag()
    for old_page in old_pages:
        new_page = CompoundTag({
            'raw': old_page
        })
        new_pages.append(new_page)
    
    written_book_content['pages'] = new_pages
    components_tag['minecraft:written_book_content'] = written_book_content


def _convert_banner_patterns(components_tag: CompoundTag, block_entity_tag: CompoundTag):
    old_patterns = block_entity_tag['Patterns']
    if old_patterns.is_null():
        return
    
    new_patterns = ListTag()
    for old_pattern in old_patterns:
        new_pattern = CompoundTag({
            'color': StringTag(BANNER_COLORS[int(old_pattern['Color'])]),
            'pattern': StringTag(BANNER_PATTERNS[str(old_pattern['Pattern'])])
        })
        new_patterns.append(new_pattern)

    components_tag['minecraft:banner_patterns'] = new_patterns


def _convert_container(components_tag: CompoundTag, block_entity_tag: CompoundTag):
    items_tag = block_entity_tag['Items']
    if items_tag.is_null():
        return
    
    container_tag = ListTag()
    for item in items_tag:
        new_item = convert_legacy_item(item)
        container_tag.append(new_item)
    
    components_tag['minecraft:container'] = container_tag


def _convert_name(components_tag: CompoundTag, display_tag: CompoundTag):
    if 'Name' in display_tag:
        components_tag['minecraft:custom_name'] = display_tag['Name']


def _convert_lore(components_tag: CompoundTag, display_tag: CompoundTag):
    if 'Lore' in display_tag:
        components_tag['minecraft:lore'] = display_tag['Lore']


def _convert_custom_data(components_tag: CompoundTag, data_tag: CompoundTag):
    custom_data_tag = CompoundTag() 
    for key, nbt_value in data_tag.items():
        if key not in DATA_TAG_KEYS:
            custom_data_tag[key] = nbt_value
    
    if len(custom_data_tag) > 0:
        components_tag['minecraft:custom_data'] = custom_data_tag


def convert_legacy_item(legacy_item: CompoundTag) -> CompoundTag:
    """
    Converts a [legacy item](https://minecraft.wiki/w/Item_format/Before_1.20.5) 
    into a modern [component](https://minecraft.wiki/w/Data_component_format) based item.
    """
    modern_item = CompoundTag()

    modern_item['count'] = IntTag(legacy_item['Count'].get_byte())
    modern_item['id'] = StringTag(legacy_item['id'].get_string())

    slot_value: ByteTag | None = legacy_item['slot']
    if slot_value:
        modern_item['slot'] = slot_value

    # Convert data tag keys
    data_tag = legacy_item['tag']
    if not data_tag.is_null():
        components_tag = CompoundTag()
        _convert_attribute_modifiers(components_tag, data_tag)
        _convert_damage_and_unbreakable(components_tag, data_tag)
        _convert_enchantments(components_tag, data_tag)
        _convert_writable_book(components_tag, data_tag)
        _convert_written_book(components_tag, data_tag)

        # Convert block entity keys
        block_entity_tag = data_tag['BlockEntityTag']
        if not block_entity_tag.is_null():
            _convert_banner_patterns(components_tag, block_entity_tag)
            _convert_container(components_tag, block_entity_tag)
        
        # Convert display keys
        display_tag = data_tag['display']
        if not display_tag.is_null():
            _convert_name(components_tag, display_tag)
            _convert_lore(components_tag, display_tag)
        
        # Copy any custom keys that may be present into custom_data
        _convert_custom_data(components_tag, data_tag)
    
        modern_item['components'] = components_tag

    return modern_item
