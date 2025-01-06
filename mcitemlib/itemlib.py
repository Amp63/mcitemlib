"""
A library for creating and editing Minecraft items using python.
"""

import json
import time
import socket
import websocket
import nbtlib
import numpy
from typing import Literal
from mcitemlib.style import StyledString, ampersand_to_section_format, snake_to_capitalized, McItemlibStyleException


BOOK_ITEMS = {
    'minecraft:writable_book': 'minecraft:writable_book_content',
    'minecraft:written_book': 'minecraft:written_book_content'
}

COL_WARN = '\x1b[33m'
COL_RESET = '\x1b[0m'
COL_SUCCESS = '\x1b[32m'
COL_ERROR = '\x1b[31m'

RECODE_PORT = 31372
CODECLIENT_URL = 'ws://localhost:31375'


class AutoDict:
    """
    Dictionary that automatically adds nested dictionaries if a key does not exist already.
    """

    def __init__(self, d: dict):
        self.data = d
    

    @staticmethod
    def from_dict(d: dict):
        auto_dict = AutoDict({})
        for k, v in d.items():
            if isinstance(v, dict):
                auto_dict[k] = AutoDict.from_dict(v)
            else:
                auto_dict[k] = v
        return auto_dict

    def __repr__(self):
        return str(self.data)
    

    def __getitem__(self, key):
        if key not in self.key_set():
            self.data[key] = AutoDict({})
        return self.data[key]


    def __setitem__(self, key, value):
        self.data[key] = value


    def key_set(self) -> set:
        return set(self.data.keys())
    

    def as_dict(self) -> dict:
        new_dict = {}
        for key, value in self.data.items():
            if isinstance(value, AutoDict):
                new_dict[key] = value.as_dict()
            elif isinstance(value, list):
                new_dict[key] = [v.as_dict() if isinstance(v, AutoDict) else v for v in value]
            else:
                new_dict[key] = value
        return new_dict


    def set_list(self, key) -> list:
        """
        Creates a new list value at key if the key does not already exist.
        Returns the list at the given key.
        """
        if key not in self.key_set():
            self.data[key] = []
        return self.data[key]


class MCItemlibException(Exception):
    pass


class _TypedInt:
    def __init__(self, value: int, type: str):
        self.value = value
        self.type = type
    
    def __repr__(self) -> str:
        return f'{self.value}{self.type}'


def get_insert_index(nums: list[int], target: int):
    left, right = 0, len(nums)
    while left < right:
        mid = left + (right - left) // 2
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid
    return left


def _parse_text_parameter(string: str|StyledString):
    if isinstance(string, str):
        return StyledString.from_codes(string)
    return string


class _RawValue:
    """
    Represents a value that should be inserted into an nbt string exactly as is.
    """
    def __init__(self, value):
        self.value = value
    
    def __repr__(self) -> str:
        return str(self.value)
    
    def __str__(self) -> str:
        return str(self.value)


class Item:
    def __init__(self, item_id: str, count: int=1):
        self.nbt = AutoDict({
            '~id': f'minecraft:{item_id}',
            '~count': count,
        })
        if item_id == 'written_book':
            content = AutoDict({
                '~resolved': _TypedInt(1, 'b'),
                '~author': 'mcitemlib',
                '~title': {'~raw': 'Written Book'}
            })
            self.nbt['~components']['minecraft:written_book_content'] = content
    

    @classmethod
    def from_nbt(cls, nbt: str):
        i = cls('stone')
        nbt_dict = convert_nbt_tag(nbtlib.parse_nbt(nbt))
        i.nbt = nbt_dict
        return i
    

    def __repr__(self):
        return f'Item({self.nbt.__repr__()})'
    

    def __str__(self):
        return self.__repr__()


    def __eq__(self, value):
        if not isinstance(value, Item):
            return False
        return self.get_nbt() == value.get_nbt()
    

    def clone(self):
        """
        Returns a deep copy of this item.
        """
        new_nbt = AutoDict(self.nbt.as_dict())
        new_item = Item('stone')
        new_item.nbt = new_nbt
        return new_item


    def get_id(self) -> str:
        """
        Get the ID of this item.

        :return: The ID of this item.
        """
        return self.nbt['~id']
    

    def get_count(self) -> int:
        """
        Get the count of this item.

        :return: The count of this item.
        """
        count = self.nbt['~count']
        if isinstance(count, _TypedInt):
            return count.value
        return count
    

    def get_durability(self) -> int:
        """
        Get the durability of this item as the amount of damage done to it.

        :return: The damage done to this item
        """
        damage = self.nbt['~components']['minecraft:damage']
        if isinstance(damage, _TypedInt):
            return damage.value
        return damage


    def get_name(self) -> StyledString:
        """
        Get the name of this item.

        :return: The name of the item.
        """
        name = self.nbt['~components']['minecraft:custom_name']
        if isinstance(name, AutoDict):
            return StyledString.from_string(snake_to_capitalized(self.nbt['~id'][10:]))
        return self.nbt['~components']['minecraft:custom_name']


    # TODO: return empty list if lore doesnt exist
    def get_lore(self) -> list[StyledString]:
        """
        Get all lore on this item.

        :return: A list of lore texts.
        """
        return self.nbt['~components']['minecraft:lore']


    def get_enchantments(self) -> dict:
        """
        Get a list of enchantments applied to this item.

        :return: A list of enchantment data.
            - Format: `[{<enchant id>, <enchant level>}]`
        """
        if 'minecraft:enchantments' not in self.nbt['~components'].data:
            return {}
        return self.nbt['~components']['minecraft:enchantments']['levels']


    def get_shulker_box_item(self, slot: int):
        """
        Get a shulker box item at the given slot.

        :param int slot: The inventory slot to access.

        :return: The item in the given slot.
        """
        if not 'shulker_box' in self.nbt['~id']:
            raise MCItemlibException('Tried to access contents of non shulker box item.')
        item_list = self.nbt['~components'].set_list('minecraft:container')
        used_slots = [item.nbt['slot'] for item in item_list]
        if slot not in used_slots:
            return Item('air')
        index = used_slots.index(slot)
        return item_list[index]


    def get_book_text(self) -> list[str]:
        """
        Get all book text from this item.
        """
        page_tag = BOOK_ITEMS.get(self.nbt['~id'])
        if page_tag is None:
            raise MCItemlibException('Tried to get text from non-book item.')
        if page_tag not in self.nbt['~components'].data:
            return []
        pages = self.nbt['~components'][page_tag]['~pages']
        return [p['~raw'] for p in pages]


    def get_custom_data(self, key: str):
        """
        Get a data value from the `custom_data` directory of this item.

        :param str key: The name of the tag to access.
        """
        if key in self.nbt['~components']['minecraft:custom_data'].data:
            return self.nbt['~components']['minecraft:custom_data'][key]
        raise MCItemlibException(f'Key `{key}` not found')
    

    def set_id(self, id: str):
        """
        Set the ID of this item.

        :param str id: The ID to set.
        """
        self.nbt['~id'] = id
    
    
    def set_count(self, count: int):
        """
        Set the count of this item.

        :param int count: The count to set.
        """
        self.nbt['~count'] = count
    

    def set_durability(self, damage: int):
        """
        Set the durability damage of this item

        :param int damage: The amount of damage to set.
            - Higher damage = less durability
        """
        self.nbt['~components']['minecraft:damage'] = damage
    

    def set_name(self, name: str|StyledString):
        """
        Set the name of this item.

        :param str|StyledString name: The name to set.
        """
        self.nbt['~components']['minecraft:custom_name'] = _parse_text_parameter(name)
    

    def set_lore(self, lore_lines: list[str]|list[StyledString]):
        """
        Set all lore lines for this item.

        :param list[str]|list[StyledString] lore_lines: The lore texts to set.
        """
        self.nbt['~components']['minecraft:lore'] = [_parse_text_parameter(l) for l in lore_lines]
    

    def set_lore_line(self, lore_text: str|StyledString, lore_line: int=-1):
        """
        Set the lore text for this item at a given line.

        :param str|StyledString lore_text: The text to set.
        :param int lore_line: The line to set the text.
            - If `-1`, the text will be added to the end of the lore list.
        """
        self.nbt['~components'].set_list('minecraft:lore')
        lore_list = self.nbt['~components']['minecraft:lore']

        parsed_lore_text = _parse_text_parameter(lore_text)
        if lore_line == -1:
            lore_list.append(parsed_lore_text)
        else:
            if lore_line >= len(lore_list):  # autofill empty lines
                for _ in range(lore_line-len(lore_list)+1):
                    lore_list.append(StyledString.from_string(''))
            lore_list[lore_line] = parsed_lore_text
    

    def set_enchantment(self, enchant_id: str, enchant_level: int):
        """
        Set an enchantment on this item.

        :param str enchant_id: The ID of the enchantment to set.
        :param int enchant_level: The level of the enchantment to set.
        """
        self.nbt['~components']['minecraft:enchantments']['levels'][f'minecraft:{enchant_id}'] = enchant_level
    

    def set_shulker_box_item(self, item: "Item", slot: int=-1):
        """
        Set an item in this shulker box.

        :param Item item: The item to set.
        :param int slot: The slot to set the item in.
            - If `-1`, sets the item in the next available slot in the box.
        """
        if not 'shulker_box' in self.nbt['~id']:
            raise MCItemlibException('Tried to access contents of non shulker box item.')
        item_list = self.nbt['~components'].set_list('minecraft:container')
        added_item = item.clone()
        used_slots = [item.nbt['~slot'] for item in item_list]
        if slot == -1:
            if len(item_list) == 27:
                raise MCItemlibException('Cannot insert item into filled shulker box.')
            empty_slot = 0
            for i in range(27):
                if i not in used_slots:
                    empty_slot = i
                    break
            container_item_data = {'~slot': empty_slot, '~item': added_item}
            index = get_insert_index(used_slots, empty_slot)
            item_list.insert(index, container_item_data)
            return

        container_item_data = {'~slot': slot, '~item': added_item}
        if slot in used_slots:
            index = used_slots.index(slot)
            item_list[index] = container_item_data
        else:
            index = get_insert_index(used_slots, slot)
            item_list.insert(index, container_item_data)
    

    def set_book_text(self, pages: list[str]):
        """
        Set all pages in this book.

        :param list[str] pages: The page texts to set.
        """
        item_id = self.nbt['~id']
        page_tag = BOOK_ITEMS.get(item_id)
        if page_tag is None:
            raise MCItemlibException('Tried to write text to non-book item.')
        if item_id == 'minecraft:written_book':
            formatted_pages = [{'~raw': "'" + {ampersand_to_section_format(p).replace('\n', '\\\\n')} + "'"} for p in pages]
        else:
            formatted_pages = [{'~raw': ampersand_to_section_format(p)} for p in pages]
        self.nbt['~components'][page_tag]['~pages'] = formatted_pages
    

    def set_book_page(self, page_text: str, page_number: int=-1):
        """
        Set a page in this book.

        :param str page_text: The text to set on the page.
        :param int page_number: The page number to set the text on.
            - If `-1`, adds a new page to the end of the book.
        """
        item_id = self.nbt['~id']
        page_tag = BOOK_ITEMS.get(item_id)
        if page_tag is None:
            raise MCItemlibException('Tried to write text to non-book item.')
        if page_number < 0 or page_number > 99:
            raise McItemlibStyleException('Enter a page number between 0 and 99.')
        page_list = self.nbt['~components'][page_tag].set_list('~pages')

        formatted_page_text = ampersand_to_section_format(page_text)
        if item_id == 'minecraft:written_book':
            formatted_page_text = "'" + formatted_page_text.replace('\n', '\\\\n') + "'"

        if page_number == -1:
            page_list.append({'~raw': formatted_page_text})
        else:
            while (len(page_list) <= page_number):
                if item_id == 'minecraft:written_book':
                    page_list.append({'~raw': _RawValue("""'""'""")})
                else:
                    page_list.append({'~raw': _RawValue('""')})
            page_list[page_number] = {'~raw': formatted_page_text}
    

    def set_book_author(self, author: str):
        if self.nbt['~id'] != 'minecraft:written_book':
            raise MCItemlibException('Tried to write to non-book item.')
        self.nbt['~components']['minecraft:written_book_content']['~author'] = author


    def set_book_title(self, title: str):
        if self.nbt['~id'] != 'minecraft:written_book':
            raise MCItemlibException('Tried to write to non-book item.')
        self.nbt['~components']['minecraft:written_book_content']['~title'] = {'~raw': title}


    def set_custom_data(self, key: str, value, raw: bool=False):
        """
        Set a custom tag for this item in the 'tag' directory.

        :param str key: The name of the tag.
        :param str value: The value for the tag.
        :param bool raw: If false, `value` will be formatted normally. Otherwise, `value` will appear exactly as it is inputted.
        """
        if raw:
            value = _RawValue(value)
        self.nbt['~components']['minecraft:custom_data'][key] = value

    
    def _format_as_nbt(self, value) -> str:
        if isinstance(value, int):
            return f'{value}'
        
        if isinstance(value, _TypedInt):
            return f'{value.value}{value.type}'

        if isinstance(value, float):
            return f'{value}d'
        
        if isinstance(value, _RawValue):
            return str(value)

        if isinstance(value, str):
            return f'"{value}"'

        if isinstance(value, StyledString):
            return f"'{value.format()}'"
        
        if isinstance(value, dict):
            nbt_list = []
            for k, v in value.items():
                k: str = k[1:] if k.startswith('~') else f'"{k}"'
                nbt_list.append(f'{k}:{self._format_as_nbt(v)}')
            return f'{{{",".join(nbt_list)}}}'
        
        if isinstance(value, list):
            nbt_list = []
            for v in value:
                nbt_list.append(self._format_as_nbt(v))
            return f'[{",".join(nbt_list)}]'

        if isinstance(value, Item):
            return value.get_nbt()
        
        if isinstance(value, numpy.ndarray):
            return f'[I;{",".join(str(i) for i in value)}]'
        
        raise MCItemlibException(f'_format_as_nbt received an unexpected type `{type(value)}`')
    

    def get_nbt(self) -> str:
        """
        Returns the raw nbt data of this item as a string.
        """
        return self._format_as_nbt(self.nbt.as_dict())


    def send_to_minecraft(self, method: Literal['recode', 'codeclient'], source: str='mcitemlib') -> int:
        """
        Builds this template and sends it to Minecraft automatically.
        
        :param str source: The source program from which the item was sent.
        """
        if method == 'recode':
            return send_recode(self, source)
        if method == 'codeclient':
            return send_codeclient(self)
        return -1


def send_recode(item: Item, source: str='mcitemlib') -> int:
    """
    Sends a template to DiamondFire via recode item api.

    :param str templateCode: The code for the template as a base64 string.
    :param str name: The name of the template.
    :param str author: The author of the template.

    :return: status code
        - `0` = Success
        - `1` = Connection refused
        - `2` = Other socket error
    """
    
    data = {'type': 'nbt', 'source': f'{source} - {item.get_name().to_string()}', 'data': item.get_nbt()}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('localhost', RECODE_PORT))
    except ConnectionRefusedError:
        print(f"""{COL_ERROR}Could not connect to recode item API. Possible problems:
    - Minecraft is not open
    - Recode is not installed (get it here: https://modrinth.com/mod/recode or join the discord here: https://discord.gg/GWxWtcwA2C){COL_RESET}""")
        s.close()
        return 1
    
    s.send((json.dumps(data) + '\n').encode('utf-8'))
    received = json.loads(s.recv(1024).decode())
    status = received['status']
    s.close()
    time.sleep(0.5)

    if status == 'success':
        print(f'{COL_SUCCESS}Item sent to client successfully.{COL_RESET}')
        return 0
    error = received['error']
    print(f'{COL_ERROR}Error sending item: {error}{COL_RESET}')
    return 2


def send_codeclient(item: Item) -> int:
    try:
        ws = websocket.WebSocket()
        ws.connect(CODECLIENT_URL)
        print(f'{COL_SUCCESS}Connected.{COL_RESET}')

        command = f'give {item.get_nbt()}'
        ws.send(command)
        ws.close()

        print(f'{COL_SUCCESS}Item sent to client successfully.{COL_RESET}')
        return 0
        
    except Exception as e:
        if isinstance(e, ConnectionRefusedError):
            print(f'{COL_ERROR}Could not connect to CodeClient API. Possible problems:')
            print(f'    - Minecraft is not open')
            print(f'    - CodeClient is not installed (get it here: https://modrinth.com/mod/codeclient)')
            print(f'    - CodeClient API is not enabled (enable it in CodeClient general settings)')
            return 1
        
        print(f'Connection failed: {e}')
        return 2


def convert_nbt_tag(nbt_tag: nbtlib.Base, quote_keys=False):
    """
    Converts nbtlib tags into mcitemlib objects
    """
    if isinstance(nbt_tag, nbtlib.Compound):
        unpacked = nbt_tag.unpack()
        if 'text' in unpacked:
            return StyledString.from_nbt_dict(unpacked)
        new_tag = {}
        for k, v in nbt_tag.items():
            do_quotes_here = not (k.startswith('minecraft:') or k =='pages')
            if not quote_keys:
                k = f'~{k}'
            new_tag[k] = convert_nbt_tag(v, do_quotes_here)
        return AutoDict(new_tag)
    elif isinstance(nbt_tag, nbtlib.List):
        return [convert_nbt_tag(t, quote_keys) for t in nbt_tag]
    elif isinstance(nbt_tag, nbtlib.Numeric):
        return _TypedInt(nbt_tag.unpack(), nbt_tag.suffix)
    elif isinstance(nbt_tag, nbtlib.String):
        try:
            return StyledString.from_nbt(nbt_tag.unpack())
        except McItemlibStyleException:
            unpacked = nbt_tag.unpack()
            if '"' in unpacked:
                return _RawValue(f"'{unpacked}'")  # this probably won't work for some things
            return nbt_tag.unpack()
    return nbt_tag.unpack()
