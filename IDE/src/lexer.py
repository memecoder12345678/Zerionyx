import re
import json
import os
from typing import TypedDict
from PyQt5.Qsci import QsciLexerCustom
from PyQt5.QtGui import QFont, QColor

class DefaultConfig(TypedDict):
    color: str
    paper: str
    font: tuple[str, int]


class BaseLexer(QsciLexerCustom):

    def __init__(
        self, language_name, editor, theme=None, defaults: DefaultConfig = None
    ):
        super(BaseLexer, self).__init__(editor)

        self.editor = editor
        self.language_name = language_name
        self.theme_json = None
        if theme is None:
            self.theme = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), f".{os.sep}theme.json"
            )
        else:
            self.theme = theme

        self.token_list: list[str, str] = []

        self.keywords_list = []
        self.builtin_names = []

        if defaults is None:
            defaults: DefaultConfig = {}
            defaults["color"] = "#b2eff5"
            defaults["paper"] = "#181a1b"
            defaults["font"] = ("Consolas", 14)

        self.setDefaultColor(QColor(defaults["color"]))
        self.setDefaultPaper(QColor(defaults["paper"]))
        self.setDefaultFont(QFont(defaults["font"][0], defaults["font"][1]))

        self._init_theme_vars()
        self._init_theme()

    def setKeywords(self, keywords: list[str]):
        self.keywords_list = keywords

    def setBuiltinNames(self, buitin_names: list[str]):
        self.builtin_names = buitin_names

    def _init_theme_vars(self):

        self.DEFAULT = 0
        self.KEYWORD = 1
        self.TYPES = 2
        self.STRING = 3
        self.BRACKETS = 4
        self.COMMENTS = 5
        self.CONSTANTS = 6
        self.FUNCTIONS = 7
        self.FUNCTION_AND_CLASS_DEF = 8
        self.CLASSES = 9

        self.default_names = [
            "default",
            "keyword",
            "functions",
            "function_and_class_def",
            "classes",
            "string",
            "types",
            "brackets",
            "comments",
            "constants",
        ]

        self.style_map = {
            "default": self.DEFAULT,
            "keyword": self.KEYWORD,
            "types": self.TYPES,
            "string": self.STRING,
            "brackets": self.BRACKETS,
            "comments": self.COMMENTS,
            "constants": self.CONSTANTS,
            "functions": self.FUNCTIONS,
            "function_and_class_def": self.FUNCTION_AND_CLASS_DEF,
            "classes": self.CLASSES,
        }

        self.font_weights = {
            "thin": QFont.Thin,
            "extralight": QFont.ExtraLight,
            "light": QFont.Light,
            "normal": QFont.Normal,
            "medium": QFont.Medium,
            "demibold": QFont.DemiBold,
            "bold": QFont.Bold,
            "extrabold": QFont.ExtraBold,
            "black": QFont.Black,
        }

    def _init_theme(self):
        if not os.path.exists(self.theme):
            print(f"Theme file '{self.theme}' not found!")
            return

        try:
            with open(self.theme, "r") as f:
                self.theme_json = json.load(f)
        except Exception as e:
            print(f"Error loading theme: {str(e)}")
            return

        colors = self.theme_json["theme"]["syntax"]

        for clr in colors:
            name: str = list(clr.keys())[0]

            if name not in self.default_names:
                print(f"Theme error: {name} is not a valid style name")
                continue

            style_id = self.style_map.get(name)
            if style_id is None:
                print(f"Theme error: No style ID found for {name}")
                continue

            for k, v in clr[name].items():
                if k == "color": 
                    self.setColor(QColor(v), style_id)
                elif k == "paper-color":
                    self.setPaper(QColor(v), style_id)
                elif k == "font":
                    try:
                        self.setFont(
                            QFont(
                                v.get("family", "Consolas"),
                                v.get("font-size", 14),
                                self.font_weights.get(
                                    v.get("font-weight", QFont.Normal)
                                ),
                                v.get("italic", False),
                            ),
                            style_id,
                        )
                    except AttributeError as e:
                        print(f"theme error: {e}")

    def language(self) -> str:
        return self.language_name

    def description(self, style: int) -> str:
        if style == self.DEFAULT:
            return "DEFAULT"
        elif style == self.CLASSES:
            return "CLASSES"
        elif style == self.KEYWORD:
            return "KEYWORD"
        elif style == self.TYPES:
            return "TYPES"
        elif style == self.STRING:
            return "STRING"
        elif style == self.COMMENTS:
            return "COMMENTS"
        elif style == self.FUNCTIONS:
            return "FUNCTIONS"
        elif style == self.FUNCTION_AND_CLASS_DEF:
            return "FUNCTION_AND_CLASS_DEF"
        elif style == self.BRACKETS:
            return "BRACKETS"
        elif style == self.CONSTANTS:
            return "CONSTANTS"
        return ""

    def generate_tokens(self, text):
        p = re.compile(r"/\*|\*/|\s+|\w+|\W")
        self.token_list = [
            (token, len(bytearray(token, "utf-8"))) for token in p.findall(text)
        ]

    def next_tok(self, skip: int = None):
        if skip is not None and skip > 0:
            for _ in range(skip):
                if len(self.token_list) > 0:
                    self.token_list.pop(0)
                else:
                    return None
        if len(self.token_list) > 0:
            return self.token_list.pop(0)
        else:
            return None


    def peek_tok(self, n=0):
        try:
            return self.token_list[n]
        except IndexError:
            return ("", 0)

    def skip_spaces_peek(self, skip_tokens=None):
        i = 0
        if skip_tokens is not None:
            i = skip_tokens

        temp_idx = i
        while temp_idx < len(self.token_list) and self.token_list[temp_idx][0].isspace():
            temp_idx += 1

        if temp_idx < len(self.token_list):
            return self.token_list[temp_idx], temp_idx + 1
        else:
            return ("", 0), temp_idx + 1



class ZerionLexer(BaseLexer):
    def __init__(self, editor):
        super(ZerionLexer, self).__init__("Zerion", editor)
        self.current_file = None
        self.core_functions = {
            "append", "clear", "extend", "is_none", "input", "insert", "is_func",
            "set_reusable", "is_list", "is_num", "is_thread", "is_str", "len",
            "catch", "finally", "panic", "pop", "print", "println", "to_float",
            "to_int", "to_str", "type",
        }
        self.lib_functions = {
            "libs.math": ["sqrt", "abs", "fact", "sin", "cos", "tan", "gcd", "lcm", "fib", "is_prime", "deg2rad", "rad2deg", "exp", "log", "sinh", "cosh", "tanh", "round"],
            "libs.string": ["split", "join", "replace", "strip", "to_upper", "to_lower", "ord", "chr", "is_digit", "is_ascii_lowercase", "is_ascii_uppercase", "is_ascii_letter", "is_space", "find", "find_all", "startswith", "endswith", "str_multiply", "str_slice"],
            "libs.list": ["map", "filter", "reduce", "min", "max", "reverse", "zip", "zip_longest", "change_value", "sort", "count", "index_of", "clear_list", "list_multiply", "rand_int_list", "rand_float_list"],
            "libs.file": ["read", "write", "remove_file", "remove_dir", "exists", "rename", "copy", "list_dir", "set_cdir", "get_cdir", "make_dir", "is_file", "abs_path", "base_name", "dir_name"],
            "libs.time": ["time", "ctime", "sleep"],
            "libs.random": ["rand", "rand_int", "rand_choice", "rand_float", "int_seed", "float_seed"],
            "libs.sys": ["exit", "system", "get_env", "set_env"],
            "libs.hash": ["md5", "sha1", "sha256", "sha512", "crc32"],
            "libs.memory": ["remember", "forget", "recall", "clear_memory", "keys", "is_empty", "size"],
            "libs.net": ["get_ip", "get_hostname", "get_local_ip", "get_mac", "ping", "downl"],
            "libs.threading" : ["thread_start", "thread_join", "thread_sleep", "thread_is_alive", "thread_cancel"],
            "libs.keyboard": ["keyboard_write", "keyboard_press", "keyboard_release", "keyboard_wait", "keyboard_is_pressed"],
            "libs.termcolor": ["cprintln", "cprint"],
        }
        self.operators = ["+", "-", "*", "/", "%", "^", "=", "<", ">", "!"]
        self.types = ["list", "str", "int", "float", "func"]
        self.literals = ["true", "false", "none"]
        self.user_functions = set()
        self.available_functions = set(self.core_functions)
        self.setKeywords([
            "let", "and", "or", "not", "if", "elif", "else", "for", "to", "do",
            "step", "while", "defun", "done", "return", "continue", "break", "load",
        ])


        self.in_string_mode = False
        self.string_quote_char = None
        self.is_triple_string = False
        self.triple_closing_match_count = 0
        self.is_escape_sequence_char = False
        
        self.last_scanned_pos = 0

    def set_current_file(self, filepath):
        self.current_file = filepath
        self.last_scanned_pos = 0
        if filepath:
            text = self.editor.text()
            self.update_definitions(text)
        else:
            self.user_functions.clear()
            self.available_functions = set(self.core_functions)

    def update_definitions(self, text):
        cleaned_text = self._remove_strings_and_comments(text)
        defun_pattern = r"\bdefun\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        current_funcs = set(re.findall(defun_pattern, cleaned_text))

        used_libs = set(self.find_loads_outside_strings(text))


        if self.user_functions != current_funcs or self.available_functions_changed(used_libs):
            self.user_functions = current_funcs
            self.available_functions = set(self.core_functions)
            for lib in used_libs:
                if lib in self.lib_functions:
                    self.available_functions.update(self.lib_functions[lib])
            if hasattr(self.editor, 'SendScintilla') and hasattr(self.editor, 'SCI_COLOURISE'):
                self.editor.SendScintilla(self.editor.SCI_COLOURISE, 0, -1)

    def available_functions_changed(self, used_libs):
        new_available = set(self.core_functions)
        for lib in used_libs:
            if lib in self.lib_functions:
                new_available.update(self.lib_functions[lib])
        return new_available != self.available_functions

    def find_loads_outside_strings(self, text):
        string_spans = []
        for m in re.finditer(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')', text):
            string_spans.append((m.start(), m.end()))

        def is_in_string(pos):
            for start, end in string_spans:
                if start <= pos < end:
                    return True
            return False

        pattern = re.compile(r'\bload\s*\(?\s*["\']([\w\.]+)["\']\s*\)?')
        result = []
        for m in pattern.finditer(text):
            if not is_in_string(m.start()):
                result.append(m.group(1))
        return result

    def _remove_strings_and_comments(self, text):
        processed = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'', '', text, flags=re.DOTALL)
        processed = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', '', processed)
        processed = re.sub(r'#.*$', '', processed, flags=re.MULTILINE)
        return processed

    def _scan_to_restore_state(self, scan_to_pos: int):

        if scan_to_pos == 0:
            self.in_string_mode = False
            self.string_quote_char = None
            self.is_triple_string = False
            self.triple_closing_match_count = 0
            self.is_escape_sequence_char = False
            self.last_scanned_pos = 0
            return

        if scan_to_pos < self.last_scanned_pos:
            self._scan_to_restore_state(0)

        scan_from = self.last_scanned_pos
        if scan_from >= scan_to_pos:
            return

        text_to_scan = self.editor.text(scan_from, scan_to_pos)

        self.generate_tokens(text_to_scan)
        
        while True:
            curr_token = self.next_tok()
            if curr_token is None:
                break

            tok_str = curr_token[0]

            if self.in_string_mode:
                if self.is_triple_string:
                    if tok_str == self.string_quote_char:
                        self.triple_closing_match_count += 1
                        if self.triple_closing_match_count == 3:
                            self.in_string_mode = False
                            self.is_triple_string = False
                    else:
                        self.triple_closing_match_count = 0
                else:
                    if self.is_escape_sequence_char:
                        self.is_escape_sequence_char = False
                    elif tok_str == '\\':
                        self.is_escape_sequence_char = True
                    elif tok_str == self.string_quote_char:
                        self.in_string_mode = False
                continue

            if tok_str in ['"', "'"]:
                p1, p2 = self.peek_tok(0), self.peek_tok(1)
                if p1 and p2 and p1[0] == tok_str and p2[0] == tok_str:
                    _, _ = self.next_tok(), self.next_tok()
                    self.in_string_mode = True
                    self.is_triple_string = True
                    self.string_quote_char = tok_str
                    self.triple_closing_match_count = 0
                else:
                    self.in_string_mode = True
                    self.is_triple_string = False
                    self.string_quote_char = tok_str
        
        self.last_scanned_pos = scan_to_pos

    def styleText(self, start: int, end: int) -> None:
        if start >= end:
            return

        full_text = self.editor.text()
        if not full_text:
            return
        
        self.update_definitions(full_text)

        self._scan_to_restore_state(start)

        self.startStyling(start)
        
        visible_text = full_text[start : min(end, len(full_text))]
        self.generate_tokens(visible_text)
        
        line_comment_active = False
        if start > 0:
            previous_style = self.editor.SendScintilla(self.editor.SCI_GETSTYLEAT, start - 1)
            if previous_style == self.COMMENTS and full_text[start-1] != '\n':
                line_comment_active = True

        while True:
            curr_token = self.next_tok()
            if curr_token is None:
                break

            tok_str: str = curr_token[0]
            tok_len: int = curr_token[1]

            if line_comment_active:
                self.setStyling(tok_len, self.COMMENTS)
                if "\n" in tok_str: line_comment_active = False
                continue

            if self.in_string_mode:
                self.setStyling(tok_len, self.STRING)
                if self.is_triple_string:
                    if tok_str == self.string_quote_char:
                        self.triple_closing_match_count += 1
                        if self.triple_closing_match_count == 3:
                            self.in_string_mode = False
                            self.is_triple_string = False
                    else:
                        self.triple_closing_match_count = 0
                else:
                    if self.is_escape_sequence_char: self.is_escape_sequence_char = False
                    elif tok_str == '\\': self.is_escape_sequence_char = True
                    elif tok_str == self.string_quote_char: self.in_string_mode = False
                continue

            if tok_str == "#":
                self.setStyling(tok_len, self.COMMENTS)
                line_comment_active = True
                continue

            if tok_str in ['"', "'"]:
                p1, p2 = self.peek_tok(0), self.peek_tok(1)
                if p1 and p2 and p1[0] == tok_str and p2[0] == tok_str:
                    combined_len = tok_len + p1[1] + p2[1]
                    self.setStyling(combined_len, self.STRING)
                    _, _ = self.next_tok(), self.next_tok()
                    self.in_string_mode = True
                    self.is_triple_string = True
                    self.string_quote_char = tok_str
                    self.triple_closing_match_count = 0
                else:
                    self.setStyling(tok_len, self.STRING)
                    self.in_string_mode = True
                    self.is_triple_string = False
                    self.string_quote_char = tok_str
                continue

            if tok_str == "defun":
                name_candidate, num_tokens = self.skip_spaces_peek()
                if name_candidate and name_candidate[0].isidentifier():
                    self.setStyling(tok_len, self.KEYWORD)
                    for _ in range(num_tokens - 1): self.setStyling(self.next_tok()[1], self.DEFAULT)
                    self.setStyling(self.next_tok()[1], self.FUNCTION_AND_CLASS_DEF)
                else: self.setStyling(tok_len, self.KEYWORD)
            elif tok_str in self.keywords_list: self.setStyling(tok_len, self.KEYWORD)
            elif tok_str in self.available_functions or tok_str in self.user_functions: self.setStyling(tok_len, self.FUNCTIONS)
            elif tok_str.isnumeric() or (tok_str.count('.') == 1 and tok_str.replace('.', '').isnumeric()): self.setStyling(tok_len, self.CONSTANTS)
            elif tok_str in self.types or tok_str in self.literals: self.setStyling(tok_len, self.TYPES)
            elif tok_str in "()[]": self.setStyling(tok_len, self.BRACKETS)
            elif tok_str in self.operators:
                self.setStyling(tok_len, self.TYPES)
            else: self.setStyling(tok_len, self.DEFAULT)
        
        self.last_scanned_pos = end
