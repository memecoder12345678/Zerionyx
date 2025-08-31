import os
import sys
from src.interp import run, INFO, Fore, Style
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

G = """

PROGRAM ::= (STATEMENT NEWLINE*)*

STATEMENT ::= SIMPLE_STATEMENT | COMPOUND_STATEMENT

SIMPLE_STATEMENT ::=
"load" STRING
| "return" EXPR
| "continue"
| "break"
| EXPR

COMPOUND_STATEMENT ::=
IF_EXPR
| FOR_EXPR
| WHILE_EXPR
| DEF_FUNC

EXPR ::=
"let" IDENTIFIER "=" EXPR
| IDENTIFIER "=" EXPR
| "let" IDENTIFIER "as" EXPR
| IDENTIFIER "as" EXPR
| IDENTIFIER ("+=" | "-=" | "*=" | "/=" | "//=" | "%=" | "^=") EXPR
| COMP_EXPR (("and" | "or") COMP_EXPR)*

COMP_EXPR ::=
ARITH_EXPR (("==" | "&lt;" | "&gt;" | "&lt;=" | "&gt;=" | "!=") ARITH_EXPR)*
| "not" COMP_EXPR

ARITH_EXPR ::= TERM (("+" | "-") TERM)*

TERM ::= FACTOR (("*" | "/" | "//" | "%") FACTOR)*

FACTOR ::= ("+" | "-") FACTOR
| "*" EXPR
| "**" EXPR
| POWER

POWER ::= CALL ("^" FACTOR)*

CALL ::= ATOM ("(" ARG_LIST? ")")?

ARG_LIST ::= ARG ("," ARG)*
ARG ::= EXPR

ATOM ::=
INT | FLOAT | STRING | IDENTIFIER
| "(" EXPR ")"
| "await" CALL
| LIST_EXPR
| IF_EXPR
| FOR_EXPR
| FOR_IN_EXPR
| HASHMAP_EXPR
| NAMESPACE_EXPR
| WHILE_EXPR
| DEF_FUNC
| COMMENT
| USING_STATEMENT
| EXPR

USING_STATEMENT ::= "using" ("parent")? IDENTIFIER ("," IDENTIFIER)*

LIST_EXPR ::= "[" (EXPR ("," EXPR)*)? "]"

HASHMAP_EXPR ::= "{" (STRING ":" EXPR ("," STRING ":" EXPR)*)? "}"

NAMESPACE_EXPR ::=
"namespace" IDENTIFIER
NEWLINE STATEMENT NEWLINE "done"

IF_EXPR ::=
"if" EXPR "do" STATEMENT
(NEWLINE "elif" EXPR "do" STATEMENT)*
(NEWLINE "else" "do" STATEMENT)?
(NEWLINE "done")?

FOR_EXPR ::=
"for" IDENTIFIER "=" EXPR "to" EXPR
("step" EXPR)?
"do" STATEMENT
(NEWLINE "done")?

FOR_IN_EXPR ::=
"for" IDENTIFIER "in" EXPR
"do" STATEMENT
(NEWLINE "done")?

WHILE_EXPR ::=
"while" EXPR "do" STATEMENT
(NEWLINE "done")?

PARAM_LIST ::= (PARAMS ("," VAR_PARAMS)? | VAR_PARAMS)?

PARAMS ::= PARAM ("," PARAM)*
PARAM ::= ("let")? IDENTIFIER ("=" EXPR)?

VAR_PARAMS ::= VARARGS_PARAM ("," KWARGS_PARAM)? | KWARGS_PARAM
VARARGS_PARAM ::= "*" IDENTIFIER
KWARGS_PARAM ::= "**" IDENTIFIER

DECORATOR ::= "@" EXPR NEWLINE*

DEF_FUNC ::=
DECORATOR* ("async")? "defun" IDENTIFIER? "(" PARAM_LIST? ")" <span class="comment">-- SỬA ĐỔI: Thêm 'async' tùy chọn</span>
("-&gt;" EXPR)?
(NEWLINE STATEMENT NEWLINE "done")?

COMMENT ::= "#" /[^\n]*/

"""


def check_file_comments_or_empty(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
        all_empty_or_comments = True

        for line in lines:
            if not (
                line.strip() == ""
                or line.strip().startswith("#")
                or all(char == ";" for char in line.strip())
            ):
                all_empty_or_comments = False
                break
        if all_empty_or_comments:
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}The file is empty or only contains comments{Fore.RESET}{Style.RESET_ALL}"
            )
            sys.exit(0)


def main():
    if len(sys.argv) == 1:
        print(f"Zerionyx {INFO}")
        print(
            "Type 'grammar', 'copyright', 'credits', 'license', 'docs' for more information or 'exit' to exit."
        )
        try:
            while True:
                text = input(f"{Fore.LIGHTMAGENTA_EX}>>> {Fore.RESET}")
                if (
                    text.strip() == ""
                    or all(char == ";" for char in text.strip())
                    or text.strip().startswith("#")
                ):
                    continue
                if text.strip() == "exit":
                    print("exit...")
                    break
                if text.strip() == "grammar":
                    print(
                        ("=" * 96)
                        + G
                        + ("=" * 96)
                        + "\n\nPlease scroll up to read from the beginning.\n"
                    )
                    continue
                if text.strip() == "license":
                    print(
                        ("=" * 96)
                        + '\n\nMIT License\n\nWARNING: This project contains code adapted from multiple public sources.\n\nSome components are originally based on David Callanan\'s interpreter tutorial (2019),\nlicensed under the MIT License. Other parts are believed to derive from Fus3n\'s version,\nwhich did not include an explicit license but was publicly shared for free use and modification.\n\nOnly modifications made by MemeCoder are explicitly claimed under copyright.\nReasonable efforts have been made to trace original authors.\nIf you are an original author and believe attribution or licensing is missing,\nplease contact MemeCoder.\n\nCredits:\n- David Callanan (2019)\n- Fus3n (2022, no license stated)\n- Modified by angelcaru (2024)\n- Further modified by MemeCoder (2025)\n\nCopyright (c) 2019-2025\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the "Software"), to deal\nin the Software without restriction, including without limitation the rights\nto use, copy, modify, merge, publish, distribute, sublicense, and/or sell\ncopies of the Software, and to permit persons to whom the Software is\nfurnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all\ncopies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\nFITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\nAUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\nLIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\nOUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\nSOFTWARE.\n\n'
                        + ("=" * 96)
                        + "\n\nPlease scroll up to read from the beginning.\n"
                    )
                    continue
                if text.strip() == "copyright":
                    print("Copyright (c) 2019-2025\nAll Rights Reserved.")
                    continue
                if text.strip() == "credits":
                    print(
                        "Credits:\n- David Callanan (2019)\n- Fus3n (2022, no license stated)\n- Modified by angelcaru (2024)\n- Further modified by MemeCoder (2025)"
                    )
                    continue
                if text.strip() == "docs":
                    print(
                        "Documentation: https://memecoder12345678.github.io/Zerionyx/docs.html"
                    )
                    continue
                result, error = run("<stdin>", text)
                if error:
                    if hasattr(error, "as_string"):
                        print(f"{error.as_string()}")
                    else:
                        print(f"{error}")
                elif result:
                    if len(result.value) == 1:
                        print(f"{repr(result.value[0])}")
                    else:
                        print(f"{repr(result)}")
        except (KeyboardInterrupt, EOFError):
            print("\nexit...")
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Interpreter Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{e}{Fore.RESET}"
            )
    elif len(sys.argv) == 2 and sys.argv[1] == "--version":
        print(f"Zerionyx {INFO}")
        return
    else:
        file_name = os.path.abspath(sys.argv[1])
        if not file_name.endswith(".zyx"):
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}The file must have a '.zyx' extension{Fore.RESET}{Style.RESET_ALL}"
            )
            return
        if not os.path.isfile(file_name) or not os.path.exists(file_name):
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}File '{os.path.abspath(file_name)}' does not exist{Fore.RESET}{Style.RESET_ALL}"
            )
            return
        try:
            check_file_comments_or_empty(file_name)
            with open(file_name, "r", encoding="utf-8") as file:
                text = file.read()
            text = text.splitlines()
            for i in range(len(text)):
                text[i] = text[i].strip()
            result, error = run(file_name, "\n".join(text))
            if error:
                if hasattr(error, "as_string"):
                    print(f"{error.as_string()}")
                else:
                    print(f"{error}")
                sys.exit(1)
            elif result:
                if len(result.value) == 1:
                    print(f"{repr(result.value[0])}")
                else:
                    print(f"{repr(result)}")
        except IOError as e:
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{e}{Fore.RESET}"
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Interpreter Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{e}{Fore.RESET}"
            )
            return


if __name__ == "__main__":
    main()
