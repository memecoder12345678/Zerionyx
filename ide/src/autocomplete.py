from PyQt5.Qsci import QsciAPIs
from .lexer import ZerionyxLexer, JsonLexer


def build_autocomplete(lexer: ZerionyxLexer | JsonLexer) -> QsciAPIs:
    apis = QsciAPIs(lexer)
    apis.clear()

    editor = lexer.editor
    pos = editor.SendScintilla(editor.SCI_GETCURRENTPOS)
    style = editor.SendScintilla(editor.SCI_GETSTYLEAT, pos - 1)

    if style in (lexer.STRING, lexer.COMMENTS):
        apis.prepare()
        return apis

    if isinstance(lexer, ZerionyxLexer):
        for token in lexer.keywords_list:
            apis.add(token)
        for func in lexer.available_functions:
            if func not in lexer.user_functions:
                apis.add(func)
        for type_ in lexer.types:
            apis.add(type_)
        for i in lexer.literals:
            apis.add(i)
    elif isinstance(lexer, JsonLexer):
        apis.add("true")
        apis.add("false")
        apis.add("null")

    apis.prepare()
    return apis
