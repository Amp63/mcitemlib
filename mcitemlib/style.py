"""
Functions related to styling text.
"""

import re
from typing import List


class PyNbtStyleException(Exception):
    pass

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
    My implementation for converting values to correctly formatted strings.
    Doesn't do weird stuff to escape characters like json.dumps does.
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
                raise PyNbtStyleException(f'Unexpected format character "{c}" found in substring.')
            i += 1
        return sub

    
    def format(self) -> str:
        format_data = {}
        for key, value in self.data.items():
            if value or key in KEPT_FORMATTING:
                format_data[key] = value
        format_data['text'] = _add_quote_escapes(format_data['text'])
        return _simple_to_string(format_data)


class StyledString:
    def __init__(self, substrings: List[StyledSubstring]):
        self.substrings = substrings
    

    def __repr__(self):
        return f'StyledString([{self.substrings}])'


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
    

    def to_string(self) -> str:
        """
        Returns an unformatted representation of this string.
        """
        return ''.join([sub.data['text'] for sub in self.substrings])
    

    def format(self):
        amount_substrings = len(self.substrings)
        if amount_substrings == 0:
            raise PyNbtStyleException('Cannot format styled string without any substrings.')
        if amount_substrings == 1:
            return self.substrings[0].format()

        formatted_substrings = [s.format() for s in self.substrings]
        extra = ','.join(formatted_substrings)
        return f'{{"extra":[{extra}],"text":""}}'