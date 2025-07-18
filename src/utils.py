from colorama import init, Fore, Style

init(autoreset=True)


class Token:
    __slots__ = ["type", "value", "pos_start", "pos_end"]

    def __init__(self, type_, value=None, pos_start=None, pos_end=None):
        self.type = type_
        self.value = value

        if pos_start:
            self.pos_start = pos_start.copy()
            self.pos_end = pos_start.copy()
            self.pos_end.advance()

        if pos_end:
            self.pos_end = pos_end.copy()

    def matches(self, type_, value):
        return self.type == type_ and self.value == value

    def __repr__(self):
        if self.value:
            if self.type == "STRING":
                return (
                    f"{Style.BRIGHT}{Fore.LIGHTYELLOW_EX}STRING{Fore.RESET}{Style.RESET_ALL}: {Fore.CYAN}'{self.value}'".replace(
                        "\n", "\\n"
                    )
                    .replace("\t", "\\t")
                    .replace("\r", "\\r")
                    .replace("\\", "\\\\")
                    if self.value.find("'") == -1
                    else f'{Style.BRIGHT}{Fore.LIGHTYELLOW_EX}STRING{Fore.RESET}{Style.RESET_ALL}: {Fore.CYAN}"{self.value}"'.replace(
                        "\n", "\\n"
                    )
                    .replace("\t", "\\t")
                    .replace("\r", "\\r")
                    .replace("\\", "\\\\")
                )
            elif (
                self.value == "INT"
                or self.value == "FLOAT"
                or self.value == "IDENTIFIER"
                or self.value == "KEYWORD"
            ):
                return f"{Style.BRIGHT}{Fore.LIGHTYELLOW_EX}{self.type}{Fore.RESET}{Style.RESET_ALL}: {Fore.CYAN}{self.value}{Fore.RESET}{Style.RESET_ALL}"
            return f"{Style.BRIGHT}{Fore.LIGHTYELLOW_EX}{self.type}{Fore.RESET}{Style.RESET_ALL}: {Fore.CYAN}{self.value}"
        return f"{Style.BRIGHT}{Fore.LIGHTYELLOW_EX}{self.type}"


class Position:
    __slots__ = ["idx", "ln", "col", "fn", "ftxt"]

    def __init__(self, idx, ln, col, fn, ftxt):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.fn = fn
        self.ftxt = ftxt

    def advance(self, current_char=None):
        self.idx += 1
        self.col += 1

        if current_char == "\n":
            self.ln += 1
            self.col = 0

        return self

    def copy(self):
        return Position(self.idx, self.ln, self.col, self.fn, self.ftxt)


class RTResult:

    def __init__(self):
        self.reset()

    def reset(self):
        self.value = None
        self.error = None
        self.func_return_value = None
        self.loop_should_continue = False
        self.loop_should_break = False

    def register(self, res):
        self.error = res.error
        self.func_return_value = res.func_return_value
        self.loop_should_continue = res.loop_should_continue
        self.loop_should_break = res.loop_should_break
        return res.value

    def success(self, value):
        self.reset()
        self.value = value
        return self

    def success_return(self, value):
        self.reset()
        self.func_return_value = value
        return self

    def success_continue(self):
        self.reset()
        self.loop_should_continue = True
        return self

    def success_break(self):
        self.reset()
        self.loop_should_break = True
        return self

    def failure(self, error):
        self.reset()
        self.error = error
        return self

    def should_return(self):
        return (
            self.error
            or self.func_return_value
            or self.loop_should_continue
            or self.loop_should_break
        )
