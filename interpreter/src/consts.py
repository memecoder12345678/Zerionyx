import os
import sys
import string

DIGITS = string.digits
LETTERS = string.ascii_letters
LETTERS_DIGITS = LETTERS + DIGITS
INFO = "(v2.0.11, June 2025, 5:18:16)"
if getattr(sys, "frozen", False):
    LIBS_PATH = os.path.dirname(sys.executable)
else:
    LIBS_PATH = os.path.dirname(os.path.abspath(__file__))
TT_INT = "INT"
TT_FLOAT = "FLOAT"
TT_STRING = "STRING"
TT_IDENTIFIER = "IDENTIFIER"
TT_KEYWORD = "KEYWORD"
TT_PLUS = "PLUS"
TT_MINUS = "MINUS"
TT_MUL = "MUL"
TT_DIV = "DIV"
TT_FLOORDIV = "FLOORDIV"
TT_POW = "POW"
TT_MOD = "MOD"
TT_EQ = "EQ"
TT_LPAREN = "LPAREN"
TT_RPAREN = "RPAREN"
TT_LSQUARE = "LSQUARE"
TT_RSQUARE = "RSQUARE"
TT_EE = "EE"
TT_NE = "NE"
TT_LT = "LT"
TT_GT = "GT"
TT_LTE = "LTE"
TT_GTE = "GTE"
TT_COMMA = "COMMA"
TT_ARROW = "ARROW"
TT_NEWLINE = "NEWLINE"
TT_EOF = "EOF"
KEYWORDS = [
    "let",
    "and",
    "or",
    "not",
    "if",
    "elif",
    "else",
    "for",
    "to",
    "do",
    "step",
    "while",
    "defun",
    "done",
    "return",
    "continue",
    "break",
    "load",
]
