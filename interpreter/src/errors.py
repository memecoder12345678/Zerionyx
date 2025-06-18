from colorama import init, Fore, Style

init(autoreset=True)


def string_with_arrows(text, pos_start, pos_end, indent):
    result = " " * indent
    idx_start = max(text.rfind("\n", 0, pos_start.idx), 0)
    idx_end = text.find("\n", idx_start + 1)
    if idx_end < 0:
        idx_end = len(text)
    line_count = pos_end.ln - pos_start.ln + 1
    for i in range(line_count):
        line = text[idx_start:idx_end]
        col_start = pos_start.col if i == 0 else 0
        col_end = pos_end.col if i == line_count - 1 else len(line) - 1
        line: str
        result += line.replace("\n", "") + "\n"
        result += " " * (col_start + indent) + f"{Fore.LIGHTRED_EX}^{Fore.RESET}" * (
            col_end - col_start
        )
        idx_start = idx_end
        idx_end = text.find("\n", idx_start + 1)
        if idx_end < 0:
            idx_end = len(text)
    return result.replace("\t", "")


class Error:
    __slots__ = ["pos_start", "pos_end", "error_name", "details"]

    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def __str__(self):
        result = f"File {Fore.MAGENTA}'{self.pos_start.fn}'{Fore.RESET}, line {Fore.MAGENTA}{self.pos_start.ln + 1}{Fore.RESET}\n"
        result += (
            string_with_arrows(
                self.pos_start.ftxt, self.pos_start, self.pos_end, 2
            ).rstrip()
            + Fore.RESET
        )
        result += f"\n{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{self.error_name}{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{self.details}"
        return result


class IllegalCharError(Error):

    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Illegal Character", details)


class ExpectedCharError(Error):

    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Expected Character", details)


class InvalidSyntaxError(Error):

    def __init__(self, pos_start, pos_end, details=""):
        super().__init__(pos_start, pos_end, "Invalid Syntax", details)


class RTError(Error):

    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, "Runtime Error", details)
        self.context = context

    def __str__(self):
        result = self.generate_traceback()
        result += string_with_arrows(
            self.pos_start.ftxt, self.pos_start, self.pos_end, 4
        ).rstrip()
        result += f"\n{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{self.error_name}{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{self.details}"
        return result

    def generate_traceback(self):
        result = ""
        pos = self.pos_start
        ctx = self.context

        while ctx:
            if pos:
                result = (
                    f"  File {Fore.MAGENTA}'{pos.fn}'{Fore.RESET}, line {Fore.MAGENTA}{str(pos.ln + 1)}{Fore.RESET}, in {Fore.MAGENTA}{ctx.display_name}{Fore.RESET}\n"
                    + result
                )
                pos = ctx.parent_entry_pos
            ctx = ctx.parent

        return "Traceback (most recent call last):\n" + result


class MError(Error):

    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, "Math Error", details)
        self.context = context

    def __str__(self):
        result = self.generate_traceback()
        result += string_with_arrows(
            self.pos_start.ftxt, self.pos_start, self.pos_end, 4
        ).rstrip()
        result += f"\n{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{self.error_name}{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{self.details}"
        return result

    def generate_traceback(self):
        result = ""
        pos = self.pos_start
        ctx = self.context

        while ctx:
            if pos:
                result = (
                    f"  File {Fore.MAGENTA}'{pos.fn}'{Fore.RESET}, line {Fore.MAGENTA}{str(pos.ln + 1)}{Fore.RESET}, in {Fore.MAGENTA}{ctx.display_name}{Fore.RESET}\n"
                    + result
                )
                pos = ctx.parent_entry_pos
            ctx = ctx.parent

        return "Traceback (most recent call last):\n" + result


class IOError(Error):

    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, "IO Error", details)
        self.context = context

    def __str__(self):
        result = self.generate_traceback()
        result += string_with_arrows(
            self.pos_start.ftxt, self.pos_start, self.pos_end, 4
        ).rstrip()
        result += f"\n{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{self.error_name}{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{self.details}"
        return result

    def generate_traceback(self):
        result = ""
        pos = self.pos_start
        ctx = self.context

        while ctx:
            if pos:
                result = (
                    f"  File {Fore.MAGENTA}'{pos.fn}'{Fore.RESET}, line {Fore.MAGENTA}{str(pos.ln + 1)}{Fore.RESET}, in {Fore.MAGENTA}{ctx.display_name}{Fore.RESET}\n"
                    + result
                )
                pos = ctx.parent_entry_pos
            ctx = ctx.parent

        return "Traceback (most recent call last):\n" + result


class TError(Error):

    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, "Type Error", details)
        self.context = context

    def __str__(self):
        result = self.generate_traceback()
        result += string_with_arrows(
            self.pos_start.ftxt, self.pos_start, self.pos_end, 4
        ).rstrip()
        result += f"\n{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{self.error_name}{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{self.details}"
        return result

    def generate_traceback(self):
        result = ""
        pos = self.pos_start
        ctx = self.context

        while ctx:
            if pos:
                result = (
                    f"  File {Fore.MAGENTA}'{pos.fn}'{Fore.RESET}, line {Fore.MAGENTA}{str(pos.ln + 1)}{Fore.RESET}, in {Fore.MAGENTA}{ctx.display_name}{Fore.RESET}\n"
                    + result
                )
                pos = ctx.parent_entry_pos
            ctx = ctx.parent

        return "Traceback (most recent call last):\n" + result
