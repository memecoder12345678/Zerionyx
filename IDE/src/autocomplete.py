from PyQt5.Qsci import QsciAPIs
from .lexer import ZerionLexer


def build_autocomplete(lexer: ZerionLexer) -> QsciAPIs:
    apis = QsciAPIs(lexer)
    apis.clear()

    editor = lexer.editor
    pos = editor.SendScintilla(editor.SCI_GETCURRENTPOS)
    style = editor.SendScintilla(editor.SCI_GETSTYLEAT, pos - 1)

    if style in (lexer.STRING, lexer.COMMENTS):
        apis.prepare()
        return apis

    if isinstance(lexer, ZerionLexer):
        for token in lexer.keywords_list:
            apis.add(token)
        for func in lexer.available_functions:
            if func not in lexer.user_functions:
                apis.add(func)
        for type_ in lexer.types:
            apis.add(type_)
    apis.prepare()
    return apis
