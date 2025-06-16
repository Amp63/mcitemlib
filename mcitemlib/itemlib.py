from typing import Any, TypedDict
import functools
import amulet_nbt
from amulet_nbt import (
    CompoundTag,
    ListTag,
    StringTag,
    IntTag,
    ByteTag
)
from mcitemlib.style import StyledString, ampersand_to_section_format


BOOK_ITEMS = {
    'minecraft:writable_book': 'minecraft:writable_book_content',
    'minecraft:written_book': 'minecraft:written_book_content'
}

COL_WARN = '\x1b[33m'
COL_RESET = '\x1b[0m'
COL_SUCCESS = '\x1b[32m'
COL_ERROR = '\x1b[31m'


class MCItemlibException(Exception):
    pass


class SlotItem(TypedDict):
    slot: int
    item: "Item"


class Item:
    def __init__(self, item_id: str, count: int=1):
        self.nbt = amulet_nbt.from_snbt(f'{{count:{count},id:"minecraft:{item_id}"}}')

        # Setup written book if necessary
        if item_id == 'written_book':
            if 'components' not in self.nbt:
                self.nbt['components'] = CompoundTag()
            
            content = CompoundTag({
                'resolved': ByteTag(1),
                'author': StringTag('mcitemlib'),
                'title': CompoundTag({'raw': StringTag('Written Book')})
            })

            self.nbt['components']['minecraft:written_book_content'] = content
    

    @classmethod
    def from_tag(cls, tag: CompoundTag):
        if 'id' not in tag or 'count' not in tag:
            raise MCItemlibException('Item requires "id" and "count" tags.')

        if not isinstance(tag['id'], StringTag):
            raise MCItemlibException('Expected `StringTag` for key "id".')
        if not isinstance(tag['count'], IntTag):
            raise MCItemlibException('Expected `IntTag` for key "count".')

        item = cls('stone', 1)
        item.nbt = tag
        return item
    

    @classmethod
    def from_snbt(cls, snbt: str):
        """
        Create a new item from an snbt string.
        """
        try:
            nbt = amulet_nbt.from_snbt(snbt)
        except amulet_nbt.SNBTParseError as e:
            raise MCItemlibException(f'Failed to parse nbt: {str(e)}')

        return cls.from_tag(nbt)


    def __repr__(self) -> str:
        return f'Item({self.nbt.__repr__()})'
    

    def __str__(self) -> str:
        return self.__repr__()


    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Item):
            return False
        return self.nbt == other.nbt


    @staticmethod
    def _check_components(func):
        """
        Sets the `components` tag if it doesn't exist already.
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if 'components' not in self.nbt:
                self.nbt['components'] = CompoundTag()
            return func(self, *args, **kwargs)
        return wrapper
    

    def clone(self):
        """
        Returns a deep copy of this item.
        """
        snbt = self.nbt.to_snbt()
        return Item.from_nbt(snbt)
    

    def get_nbt(self) -> str:
        """
        Returns the raw snbt data of this item.
        """
        return self.nbt.to_snbt()


    def get_id(self) -> str:
        """
        Get the ID of this item.

        :return: The ID of this item.
        """
        return str(self.nbt['id'])
    

    def get_count(self) -> int:
        """
        Get the count of this item.

        :return: The count of this item.
        """
        return int(self.nbt['count'])
    

    def get_durability(self) -> int:
        """
        Get the durability of this item as the amount of damage done to it.

        :return: The damage done to this item
        """
        if 'components' not in self.nbt:
            return 0
        
        components: CompoundTag = self.nbt['components']
        if 'minecraft:damage' not in components:
            return 0
        
        return int(self.nbt['components']['minecraft:damage'])


    def get_name(self) -> StyledString:
        """
        Get the name of this item.

        :return: The name of the item.
        """
        
        if 'components' not in self.nbt or 'minecraft:custom_name' not in self.nbt['components']:
            id_name = self.get_id().replace('minecraft:', '').replace('_', ' ').capitalize()
            return StyledString.from_string(id_name)
        
        name_tag: StringTag = self.nbt['components']['minecraft:custom_name']
        return StyledString.from_nbt(str(name_tag))


    
    def get_lore(self) -> list[StyledString]:
        """
        Get all lore on this item.

        :return: A list of lore texts.
        """
        if 'components' not in self.nbt:
            raise MCItemlibException('Item does not have lore.')
        
        components: CompoundTag = self.nbt['components']
        if 'minecraft:lore' not in components:
            raise MCItemlibException('Item does not have lore.')
        
        lore_texts: ListTag = components['minecraft:lore']
        return [StyledString.from_nbt(str(t)) for t in lore_texts]


    def get_enchantments(self) -> dict:
        """
        Get a list of enchantments applied to this item.

        :return: A list of enchantment data.
            - Format: `[{<enchant id>, <enchant level>}]`
        """
        if 'components' not in self.nbt:
            raise MCItemlibException('Item does not have any enchantments.')
        
        components: CompoundTag = self.nbt['components']
        if 'minecraft:enchantments' not in components:
            raise MCItemlibException('Item does not have any enchantments.')

        
        enchantments_tag: CompoundTag = components['minecraft:enchantments']['levels']
        enchantments = {}
        for enchant_id, enchant_level in enchantments_tag.items():
            enchantments[enchant_id] = int(enchant_level)
        
        return enchantments


    def get_shulker_box_contents(self) -> list[SlotItem]:
        """
        Get the contents of a shulker box.

        :return: A list of items.
        """
        if 'shulker_box' not in self.get_id():
            raise MCItemlibException('Cannot access contents of non shulker box item.')

        if 'components' not in self.nbt:
            return []
        
        components: CompoundTag = self.nbt['components']
        if 'minecraft:container' not in components:
            return []
    
        container: ListTag[CompoundTag] = components['minecraft:container']
        contents: list[SlotItem] = []
        for slot_data in container:
            contents.append({
                'slot': int(slot_data['slot']),
                'item': self.from_tag(slot_data['item'])
            })
        
        return contents


    def get_book_text(self) -> list[StyledString]:
        """
        Get all book text from this item.

        :return: A list of `StyledString`s containing each page of the book.
        """
        page_tag_key = BOOK_ITEMS.get(self.get_id())
        if page_tag_key is None:
            raise MCItemlibException('Tried to get text from non-book item.')

        if 'components' not in self.nbt:
            return []

        components: CompoundTag = self.nbt['components']
        if page_tag_key not in components:
            return []
        
        pages = components[page_tag_key]['pages']
        return [StyledString.from_codes(str(p['raw'])) for p in pages]


    def get_component(self, key: str) -> amulet_nbt.AnyNBT:
        """
        Get a value from the `components` tag in this item.

        :param str key: The name of the tag to access.
        """
        if 'components' not in self.nbt:
            raise MCItemlibException('Item does not have any components.')

        components: CompoundTag = self.nbt['components']
        if key not in components:
            raise MCItemlibException(f'Could not find key "{key}" in components.')
        
        return components[key]
    

    def set_id(self, id: str):
        """
        Set the ID of this item.

        :param str id: The ID to set.
        """
        if not id.startswith('minecraft:'):
            raise MCItemlibException('ID should start with "minecraft:".')
        
        self.nbt['id'] = StringTag(id)
    
    
    def set_count(self, count: int):
        """
        Set the count of this item.

        :param int count: The count to set.
        """
        if count < 1:
            raise MCItemlibException('Count cannot be less than 1.')
        
        self.nbt['count'] = IntTag(count)
    

    @_check_components
    def set_durability(self, damage: int):
        """
        Set the durability damage of this item

        :param int damage: The amount of damage to set.
        """
        self.nbt['components']['minecraft:damage'] = IntTag(damage)
    

    @_check_components
    def set_name(self, name: str | StyledString):
        """
        Set the name of this item.

        :param str|StyledString name: The name to set.
        """
        if isinstance(name, str):
            name = StyledString.from_codes(name)

        self.nbt['components']['minecraft:custom_name'] = StringTag(name.format())
    

    @_check_components
    def set_lore(self, lore_lines: list[str | StyledString]):
        """
        Set all lore lines for this item.

        :param list[str | StyledString] lore_lines: The lore texts to set.
        """

        formatted_lore_lines = []
        for line in lore_lines:
            if isinstance(line, str):
                line = StyledString.from_codes(line)
            line_tag = StringTag(line.format())
            formatted_lore_lines.append(line_tag)
        
        self.nbt['components']['minecraft:lore'] = ListTag(formatted_lore_lines)
    

    @_check_components
    def set_enchantments(self, enchantments: dict[str, int]):
        """
        Set the enchantments on this item.

        :param dict[str, int] enchantments: The IDs and levels of the enchantmments to set.
        """
        
        components: CompoundTag = self.nbt['components']
        if not 'minecraft:enchantments' in components:
            components['minecraft:enchantments'] = CompoundTag({'levels': CompoundTag()})
        
        enchantments_tag = components['minecraft:enchantments']['levels']

        for enchant_id, enchant_level in enchantments.items():
            enchantments_tag[enchant_id] = IntTag(enchant_level)
    

    @_check_components
    def set_shulker_box_contents(self, slot_items: list[SlotItem]):
        """
        Set the contents of this shulker box.

        :param list[SlotItem] items: The items to set.
        """
        if 'shulker_box' not in self.get_id():
            raise MCItemlibException('Cannot access contents of non shulker box item.')
        
        components: CompoundTag = self.nbt['components']
        if 'minecraft:container' not in components:
            components['minecraft:container'] = ListTag()
    
        container_tag: ListTag[CompoundTag] = components['minecraft:container']
        for slot_item in slot_items:
            slot_item_tag = CompoundTag({
                'slot': IntTag(slot_item['slot']),
                'item': slot_item['item'].nbt
            })
            container_tag.append(slot_item_tag)


    @_check_components
    def set_book_text(self, pages: list[str | StyledString]):
        """
        Set all pages in this book.

        :param list[str | StyledString] pages: The page texts to set.
        """
        page_tag_key = BOOK_ITEMS.get(self.get_id())
        if page_tag_key is None:
            raise MCItemlibException('Tried to set text on non-book item.')

        components: CompoundTag = self.nbt['components']
        if page_tag_key not in components:
            components[page_tag_key] = CompoundTag()

        pages_tag = ListTag()
        for page_string in pages:
            if isinstance(page_string, str):
                page_string = StyledString.from_codes(page_string)
            
            raw_value = ampersand_to_section_format(page_string.to_codes())
            page_tag = CompoundTag({'raw': StringTag(raw_value)})
            pages_tag.append(page_tag)
        

        components[page_tag_key]['pages'] = pages_tag
    

    @_check_components
    def set_book_author(self, author: str):
        if self.get_id() != 'minecraft:written_book':
            raise MCItemlibException('Tried to set author on non-written-book item.')
        
        book_content_tag = self.nbt['components']['minecraft:written_book_content']
        book_content_tag['author'] = StringTag(author)


    @_check_components
    def set_book_title(self, title: str | StyledString):
        if self.get_id() != 'minecraft:written_book':
            raise MCItemlibException('Tried to set title on non-written-book item.')

        if isinstance(title, str):
            title = StyledString.from_codes(title)
        raw_value = ampersand_to_section_format(title.to_codes())
        title_tag = CompoundTag({'raw': StringTag(raw_value)})

        book_content_tag = self.nbt['components']['minecraft:written_book_content']
        book_content_tag['title'] = title_tag


    @_check_components
    def set_component(self, key: str, value: amulet_nbt.AnyNBT):
        """
        Set a custom component for this item.

        :param str key: The name of the tag.
        :param AnyNBT value: The tag value.
        """
        self.nbt['components'][key] = value
