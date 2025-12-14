"""
Functions and classes related to styled text.
"""

import re
from rapidnbt import (
    nbtio, TagType,
    CompoundTag, ListTag, CompoundTagVariant,
    StringTag, ByteTag
)


STYLE_CODE_REGEX = r'(&([0-9A-Fa-fklmnorKLMNOR]|x&[0-9A-Fa-f]&[0-9A-Fa-f]&[0-9A-Fa-f]&[0-9A-Fa-f]&[0-9A-Fa-f]&[0-9A-Fa-f]))+'

COLOR_CODES = {
    '0': 'black',
    '1': 'dark_blue',
    '2': 'dark_green',
    '3': 'dark_aqua',
    '4': 'dark_red',
    '5': 'dark_purple',
    '6': 'gold',
    '7': 'gray',
    '8': 'dark_gray',
    '9': 'blue',
    'a': 'green',
    'b': 'aqua',
    'c': 'red',
    'd': 'light_purple',
    'e': 'yellow',
    'f': 'white'
}

FORMAT_CODES = {
    'k': 'obfuscated',
    'l': 'bold',
    'm': 'strikethrough',
    'n': 'underlined',
    'o': 'italic',
}

KEPT_FORMATTING = {
    'text',
    'italic',
}


class McItemlibStyleException(Exception):
    pass


def _add_new_keys(d1: CompoundTag, d2: dict[str, CompoundTagVariant]):
    """
    Sets keys from `d2` into `d1` but only if the key doesn't already exist in `d1`.
    """
    for k, v in d2.items():
        if k not in d1:
            d1[k] = v


def _add_quote_escapes(string: str):
    new_string_list = []
    for c in string:
        if c == '"':
            new_string_list.append(r'\\"')
        elif c == "'":
            new_string_list.append(r'\'')
        else:
            new_string_list.append(c)
    return ''.join(new_string_list)


def _simple_to_string(value) -> str:
    """
    Convert values to correctly formatted strings.
    Doesn't do weird stuff to escape characters.
    """
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, dict):
        dict_texts = []
        for k, v in value.items():
            dict_texts.append(f'"{k}":{_simple_to_string(v)}')
        return f'{{{",".join(dict_texts)}}}'
    if isinstance(value, list):
        return ','.join([_simple_to_string(v) for v in value])
    return value


def ampersand_to_section_format(string: str) -> str:
    """
    Converts an ampersand prefixed format string into a section symbol prefixed one.
    """
    split_string = list(string)
    for match in re.finditer(STYLE_CODE_REGEX, string):
        for section_match in re.finditer(r'&', match.group()):
            split_string[match.start()+section_match.start()] = '§'
    return ''.join(split_string)


def section_to_ampersand_format(string: str) -> str:
    """
    Converts a section symbol (§) prefixed format string into an ampersand prefixed one.
    This reverses the ampersand_to_section_format function.
    """
    split_string = list(string)
    for match in re.finditer(STYLE_CODE_REGEX.replace('&', '§'), string):
        for section_match in re.finditer(r'§', match.group()):
            split_string[match.start()+section_match.start()] = '&'
    return ''.join(split_string)


def snake_to_capitalized(string: str) -> str:
    """
    Converts a snake case string into a string of capitalized, space separated words.
    """
    return ' '.join([w.capitalize() for w in string.split('_')])


class StyledSubstring:
    def __init__(self, text: str, color: str|None=None, bold: bool=False, italic: bool=False, underlined: bool=False, strikethrough: bool=False, obfuscated: bool=False):
        self.data = {
            'bold': bold,
            'italic': italic,
            'underlined': underlined,
            'strikethrough': strikethrough,
            'obfuscated': obfuscated,
            'text': text,
        }
        if color:
            self.data['color'] = color
    
    
    def __repr__(self):
        return f'StyledSubstring({self.data})'


    # resets all formatting for this substring.
    def reset(self):
        for value in FORMAT_CODES.values():
            self.data[value] = False
    

    @staticmethod
    def from_code(code: str, text: str):
        sub = StyledSubstring(text)
        raw_code = code.replace('&', '').lower()
        i = 0
        while i < len(raw_code):
            c = raw_code[i]
            if c in COLOR_CODES:
                sub.data['color'] = COLOR_CODES[c]
            elif c in FORMAT_CODES:
                sub.data[FORMAT_CODES[c]] = True
            elif c == 'r':
                sub.reset()
            elif c == 'x':
                sub.data['color'] = f'#{raw_code[i+1:i+7].upper()}'
                i += 6
            else:
                raise McItemlibStyleException(f'Unexpected format character "{c}" found in substring.')
            i += 1
        return sub
    

    @staticmethod
    def from_snbt(snbt: str | CompoundTag):
        style_data = snbt
        if isinstance(snbt, str):
            style_data = nbtio.loads_snbt(snbt)
            if style_data is None:
                raise McItemlibStyleException('Failed to parse styled string snbt.')
        
        def bool_tag(tag: CompoundTagVariant):
            if tag.is_null():
                return False
            if tag.get_type() == TagType.Byte:
                return bool(tag.get_byte())
            if tag.is_number_integer():
                return bool(tag.get_int())
            raise McItemlibStyleException('Failed to parse style formatting option.')
        
        bold = bool_tag(style_data['bold'])
        italic = bool_tag(style_data['italic'])
        underlined = bool_tag(style_data['underlined'])
        strikethrough = bool_tag(style_data['strikethrough'])
        obfuscated = bool_tag(style_data['obfuscated'])

        color = style_data['color']
        if not color.is_null():
            color = color.get_string()
        else:
            color = None
        
        return StyledSubstring(style_data['text'].get_string(), color, bold, italic, underlined, strikethrough, obfuscated)

    
    def format(self) -> CompoundTag:
        format_data = {
            'text': _add_quote_escapes(self.data['text'])
        }

        for key, value in self.data.items():
            if value or key in KEPT_FORMATTING:
                format_data[key] = value
            if isinstance(value, str):
                format_data[key] = StringTag(value)
            elif isinstance(value, bool):
                format_data[key] = ByteTag(int(value))
        
        return CompoundTag(format_data)


class StyledString:
    def __init__(self, substrings: list[StyledSubstring]):
        self.substrings = substrings
    

    def __repr__(self):
        return f'StyledString({self.substrings})'


    @staticmethod
    def from_codes(codes: str):
        pattern = re.compile(STYLE_CODE_REGEX)
        matches = list(pattern.finditer(codes))
        if len(matches) == 0:
            return StyledString([StyledSubstring(codes)])
        
        substrings = []
        codes_start = codes[:matches[0].start()]  # unstyled start of `codes`
        if codes_start:
            substrings.append(StyledSubstring(codes_start))
        
        for i, match in enumerate(matches):
            text = codes[match.end():]
            if i < len(matches)-1:
                text = codes[match.end():matches[i+1].start()]
            if not text:
                continue

            sub = StyledSubstring.from_code(match.group(), text)
            substrings.append(sub)
        
        return StyledString(substrings)


    @staticmethod
    def from_string(string: str):
        return StyledString([StyledSubstring(string)])
    

    @staticmethod
    def from_nbt_tag(nbt_tag: CompoundTag):
        if 'extra' in nbt_tag:
            substrings = []
            extra = nbt_tag['extra']
            outside_extra = CompoundTag({k: v for k, v in nbt_tag.items() if k != 'extra'})
            if str(nbt_tag['text']) != '':
                substrings = [StyledSubstring.from_snbt(outside_extra)]
            for substring_tag in extra:
                if not isinstance(substring_tag, CompoundTag):
                    substring_tag = CompoundTag({'text': substring_tag})
                _add_new_keys(substring_tag, outside_extra)
                substrings.extend(StyledString.from_nbt_tag(substring_tag).substrings)
            return StyledString(substrings)

        return StyledString([StyledSubstring.from_snbt(nbt_tag)])
    

    @staticmethod
    def from_snbt(snbt: str):
        if snbt.strip() in {'', '""', "''"}:
            return StyledString.from_string('')

        snbt = snbt.replace("\\'", "'")  # Replace \' with single quote

        nbt_tag = nbtio.loads_snbt(snbt)
        if nbt_tag is None:
            raise McItemlibStyleException('Failed to parse styled string snbt.')
        if not isinstance(nbt_tag, CompoundTag):
            raise McItemlibStyleException('Invalid style snbt.')
        if 'text' in nbt_tag:
            return StyledString.from_nbt_tag(nbt_tag)
        raise McItemlibStyleException('String is not a formatted styled string.')
        

    def to_string(self) -> str:
        """
        Returns an unformatted representation of this string.
        """
        return ''.join([sub.data['text'] for sub in self.substrings])
    

    def to_codes(self) -> str:
        """
        Converts the styled string back to a string with ampersand formatting codes.
        """
        if not self.substrings:
            return ""
        
        # Reverse mappings
        REVERSE_COLOR_CODES = {v: k for k, v in COLOR_CODES.items()}
        REVERSE_FORMAT_CODES = {v: k for k, v in FORMAT_CODES.items()}
        
        result = []
        
        for substring in self.substrings:
            codes = []
            
            # Add color code
            color = substring.data.get('color')
            if color:
                if color.startswith('#') and len(color) == 7:
                    # Handle hex colors
                    hex_color = color[1:].lower()  # Remove # and make lowercase
                    codes.append('&x')
                    for char in hex_color:
                        codes.append(f'&{char}')
                elif color in REVERSE_COLOR_CODES:
                    codes.append(f'&{REVERSE_COLOR_CODES[color]}')
            
            # Add format codes
            for format_name, format_code in REVERSE_FORMAT_CODES.items():
                if substring.data.get(format_name, False):
                    codes.append(f'&{format_code}')
            
            # Combine codes and text
            code_string = ''.join(codes)
            result.append(code_string + substring.data['text'])
        
        return ''.join(result)
    

    def format(self) -> CompoundTag:
        amount_substrings = len(self.substrings)
        if amount_substrings == 0:
            raise McItemlibStyleException('Cannot format styled string without any substrings.')
        if amount_substrings == 1:
            return self.substrings[0].format()

        formatted_substrings = [s.format() for s in self.substrings]
        extra = ListTag(formatted_substrings)
        return CompoundTag({
            'extra': extra,
            'text': StringTag('')
        })
