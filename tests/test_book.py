from mcitemlib.itemlib import Item


def test_book_methods():
    WRITABLE_BOOK_NBT = """{components:{"minecraft:writable_book_content":{pages:[{raw:"test book\n\npage 1"},{raw:"page 2"}]}},count:1,id:"minecraft:writable_book"}"""
    item1 = Item.from_snbt(WRITABLE_BOOK_NBT)
    assert item1.get_book_text()[0].to_string() == 'test book\n\npage 1', 'Failed to get writable book text.'

    WRITTEN_BOOK_NBT = """{components:{"minecraft:written_book_content":{author:"Amp__",pages:[{raw:'"page 1!"'},{raw:'"this is page 2!\\n\\n:)"'}],resolved:1b,title:{raw:"A Written Book"}}},count:1,id:"minecraft:written_book"}"""
    item2 = Item.from_snbt(WRITTEN_BOOK_NBT)
    assert item2.get_book_text()[0].to_string() == 'page 1!', 'Failed to get written book text.'
    assert item2.get_book_title().to_string() == 'A Written Book', 'Failed to get book title.'
    assert item2.get_book_author() == 'Amp__', 'Failed to get book author.'

    item3 = Item('writable_book')
    item3.set_book_text([
        '&apage 1',
        '&bpage 2',
        '&cpage 3'
    ])
    assert item3.get_book_text()[0].to_string() == 'page 1'
