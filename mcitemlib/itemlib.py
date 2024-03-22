"""
A library for creating and editing Minecraft items using python.
"""

import json
import time
import socket
import websocket
from typing import List, Literal
from mcitemlib.style import StyledString, ampersand_to_section_format, snake_to_capitalized


BOOK_ITEMS = {
    'minecraft:writable_book',
    'minecraft:written_book'
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


class PyNbtException(Exception):
    pass


class TypedInt:
    def __init__(self, value: int, type: str):
        self.value = value
        self.type = type
    
    def __repr__(self) -> str:
        return f'{self.value}{self.type}'


def get_insert_index(nums: List[int], target: int):
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


class _RawTagValue:
    """
    Represents a tag value that should be inserted into an nbt string exactly as is.
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
            'id': f'minecraft:{item_id}',
            'Count': count,
        })
        if item_id == 'written_book':
            self.nbt['tag']['author'] = 'pynbt'
            self.nbt['tag']['title'] = 'Written Book'
    

    def __repr__(self):
        return f'Item({self.nbt.__repr__()})'
    

    def __str__(self):
        return self.__repr__()
    

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
        return self.nbt['id']
    

    def get_count(self) -> str:
        """
        Get the count of this item.

        :return: The count of this item.
        """
        return self.nbt['Count']
    

    def get_durability(self) -> int:
        """
        Get the durability of this item as the amount of damage done to it.

        :return: The damage done to this item
        """
        return self.nbt['tag']['Damage']


    def get_name(self) -> StyledString:
        """
        Get the name of this item.

        :return: The name of the item.
        """
        name = self.nbt['tag']['display']['name']
        if isinstance(name, AutoDict):
            return StyledString.from_string(snake_to_capitalized(self.nbt['id'][10:]))
        return self.nbt['tag']['display']['name']


    def get_lore(self) -> List[StyledString]:
        """
        Get all lore on this item.

        :return: A list of lore texts.
        """
        return self.nbt['tag']['display']['Lore']


    def get_enchantments(self) -> List:
        """
        Get a list of enchantments applied to this item.

        :return: A list of enchantment data.
            - Format: `[{'id': <enchant id>, 'lvl': <enchant level>}]`
        """
        if 'Enchantments' not in self.nbt['tag'].data:
            return []
        return self.nbt['tag']['Enchantments']


    def get_shulker_box_item(self, slot: int):
        """
        Get a shulker box item at the given slot.

        :param int slot: The inventory slot to access.

        :return: The item in the given slot.
        """
        if not 'shulker_box' in self.nbt['id']:
            raise PyNbtException('Tried to access contents of non shulker box item.')
        item_list = self.nbt['tag']['BlockEntityTag'].set_list('Items')
        used_slots = [item.nbt['Slot'] for item in item_list]
        if slot not in used_slots:
            return Item('air')
        index = used_slots.index(slot)
        return item_list[index]


    def get_book_text(self) -> List[str]:
        """
        Get all book text from this item.
        """
        if self.nbt['id'] not in BOOK_ITEMS:
            raise PyNbtException('Tried to get text from non-book item.')
        if 'pages' in self.nbt['tag'].data:
            return self.nbt['tag']['pages']
        return []


    def get_tag(self, tag_name: str):
        """
        Get a tag value from the tag directory of this item.

        :param str tag_name: The name of the tag to access.
        """
        if tag_name in self.nbt['tag'].data:
            return self.nbt['tag'][tag_name]
        raise PyNbtException(f'Tag `{tag_name}` not found')
    

    def set_id(self, id: str):
        """
        Set the ID of this item.

        :param str id: The ID to set.
        """
        self.nbt['id'] = id
    
    
    def set_count(self, count: int):
        """
        Set the count of this item.

        :param int count: The count to set.
        """
        self.nbt['Count'] = count
    

    def set_durability(self, damage: int):
        """
        Set the durability damage of this item

        :param int damage: The amount of damage to set.
            - Higher damage = less durability
        """
        self.nbt['tag']['Damage'] = damage
    

    def set_name(self, name: str|StyledString):
        """
        Set the name of this item.

        :param str|StyledString name: The name to set.
        """
        self.nbt['tag']['display']['Name'] = _parse_text_parameter(name)
    

    def set_lore(self, lore_lines: List[str]|List[StyledString]):
        """
        Set all lore lines for this item.

        :param List[str]|List[StyledString] lore_lines: The lore texts to set.
        """
        self.nbt['tag']['display']['Lore'] = [_parse_text_parameter(l) for l in lore_lines]
    

    def set_lore_line(self, lore_text: str|StyledString, lore_line: int=-1):
        """
        Set the lore text for this item at a given line.

        :param str|StyledString lore_text: The text to set.
        :param int lore_line: The line to set the text.
            - If `-1`, the text will be added to the end of the lore list.
        """
        self.nbt['tag']['display'].set_list('Lore')
        lore_list = self.nbt['tag']['display']['Lore']

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
        self.nbt['tag'].set_list('Enchantments')
        self.nbt['tag']['Enchantments'].append({'id': f'minecraft:{enchant_id}', 'lvl': TypedInt(enchant_level, 's')})
    

    def set_shulker_box_item(self, item, slot: int=-1):
        """
        Set an item in this shulker box.

        :param Item item: The item to set.
        :param int slot: The slot to set the item in.
            - If `-1`, sets the item in the next available slot in the box.
        """
        if not 'shulker_box' in self.nbt['id']:
            raise PyNbtException('Tried to access contents of non shulker box item.')
        item_list = self.nbt['tag']['BlockEntityTag'].set_list('Items')
        self.nbt['tag']['BlockEntityTag']['id'] = 'minecraft:shulker_box'
        added_item = item.clone()
        used_slots = [item.nbt['Slot'] for item in item_list]
        if slot == -1:
            if len(item_list) == 27:
                raise PyNbtException('Cannot insert item into filled shulker box.')
            empty_slot = 0
            for i in range(27):
                if i not in used_slots:
                    empty_slot = i
                    break
            added_item.nbt['Slot'] = empty_slot
            index = get_insert_index(used_slots, empty_slot)
            item_list.insert(index, added_item)
            return

        added_item.nbt['Slot'] = slot
        if slot in used_slots:
            index = used_slots.index(slot)
            item_list[index] = added_item
        else:
            index = get_insert_index(used_slots, slot)
            item_list.insert(index, added_item)
    

    def set_book_text(self, pages: List[str]):
        """
        Set all pages in this book.

        :param List[str] pages: The page texts to set.
        """
        if self.nbt['id'] not in BOOK_ITEMS:
            raise PyNbtException('Tried to write text to non-book item.')
        new_pages = [ampersand_to_section_format(t) for t in pages]
        self.nbt['tag']['pages'] = new_pages
    

    def set_book_page(self, page_text: str, page_number: int=-1):
        """
        Set a page in this book.

        :param str page_text: The text to set on the page.
        :param int page_number: The page number to set the text on.
            - If `-1`, adds a new page to the end of the book.
        """
        if self.nbt['id'] not in BOOK_ITEMS:
            raise PyNbtException('Tried to write text to non-book item.')
        page_list = self.nbt['tag'].set_list('pages')
        if page_number == -1:
            page_list.append(ampersand_to_section_format(page_text))
        else:
            page_list[page_number] = ampersand_to_section_format(page_text)
    

    def set_book_author(self, author: str):
        if self.nbt['id'] not in BOOK_ITEMS:
            raise PyNbtException('Tried to write to non-book item.')
        self.nbt['tag']['author'] = author
    

    def set_book_title(self, title: str):
        if self.nbt['id'] not in BOOK_ITEMS:
            raise PyNbtException('Tried to write to non-book item.')
        self.nbt['tag']['title'] = title


    def set_tag(self, tag_name: str, tag_value, raw: bool=False):
        """
        Set a custom tag for this item in the 'tag' directory.

        :param str tag_name: The name of the tag.
        :param str tag_value: The value for the tag.
        :param bool raw: If false, `tag_value` will be formatted normally. Otherwise, `tag_value` will appear exactly as it is inputted.
        """
        if raw:
            tag_value = _RawTagValue(tag_value)
        self.nbt['tag'][tag_name] = tag_value

    
    def _format_as_nbt(self, value) -> str:
        if isinstance(value, int):
            return f'{value}b'
        
        if isinstance(value, TypedInt):
            return f'{value.value}{value.type}'

        if isinstance(value, float):
            return f'{value}d'
        
        if isinstance(value, _RawTagValue):
            return str(value)

        if isinstance(value, str):
            return f'"{value}"'

        if isinstance(value, StyledString):
            return f"'{value.format()}'"
        
        if isinstance(value, dict):
            nbt_list = []
            for k, v in value.items():
                nbt_list.append(f'{k}:{self._format_as_nbt(v)}')
            return f'{{{",".join(nbt_list)}}}'
        
        if isinstance(value, list):
            nbt_list = []
            for v in value:
                nbt_list.append(self._format_as_nbt(v))
            return f'[{",".join(nbt_list)}]'

        if isinstance(value, Item):
            return value.get_nbt()
        
        raise PyNbtException(f'_format_as_nbt received an unexpected type `{type(value)}`')
    

    def get_nbt(self) -> str:
        """
        Returns the raw nbt data of this item as a string.
        """
        return self._format_as_nbt(self.nbt.as_dict())


    def send_to_minecraft(self, method: Literal['recode', 'codeclient']) -> int:
        """
        Builds this template and sends it to DiamondFire automatically.
        
        :param bool includeTags: If True, include item tags in code blocks. Otherwise omit them.
        """
        if method == 'recode':
            return send_recode(self)
        if method == 'codeclient':
            return send_codeclient(self)
        return -1
    
    
    # only works for templates; not really applicable here, but still saving the code in case i need it later
    # @staticmethod
    # def receive_from_recode():
    #     print('Waiting for item to be sent...')
    #     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     s.connect(('127.0.0.1', 31372))
    #     received = s.recv(8192)
    #     print(received)
    #     s.close()


def send_recode(item: Item) -> int:
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
    
    data = {'type': 'nbt', 'source': f'mcitemlib - {item.get_name().to_string()}', 'data': item.get_nbt()}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('localhost', RECODE_PORT))
    except ConnectionRefusedError:
        print(f"""{COL_ERROR}Could not connect to recode item API. Possible problems:
    - Minecraft is not open
    - Recode is not installed (get it here: https://modrinth.com/mod/recode or join the discord here: https://discord.gg/GWxWtcwA2C){COL_RESET}""")
        s.close()
        return 1
    
    s.send((str(data) + '\n').encode('utf-8'))
    received = json.loads(s.recv(1024).decode())
    status = received['status']
    s.close()
    time.sleep(0.5)

    if status == 'success':
        print(f'{COL_SUCCESS}Template sent to client successfully.{COL_RESET}')
        return 0
    error = received['error']
    print(f'{COL_ERROR}Error sending template: {error}{COL_RESET}')
    return 2


def send_codeclient(item: Item) -> int:
    try:
        ws = websocket.WebSocket()
        ws.connect(CODECLIENT_URL)
        print(f'{COL_SUCCESS}Connected. {COL_WARN}Please run /auth in game.{COL_RESET}')
        
        ws.recv()  # auth response

        command = f'give {item.get_nbt()}'
        ws.send(command)
        ws.close()

        print(f'{COL_SUCCESS}Template sent to client successfully.{COL_RESET}')
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
