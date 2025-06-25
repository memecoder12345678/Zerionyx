import os
import sys
from src.interp import run, INFO, Fore, Style


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
            print("Error: The file is empty or only contains comments.")
            sys.exit(0)


def main():
    if len(sys.argv) == 1:
        print(f"Zerionyx {INFO}")
        print(
            "Type 'grammar', 'copyright', 'license' for more information or 'exit' to exit."
        )
        try:
            while True:
                text = input(f"{Fore.LIGHTMAGENTA_EX}>>> {Fore.RESET}")
                text += " \n"
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
                        + '\n\\nPROGRAM            ::= (STATEMENT NEWLINE*)*\n\nSTATEMENT          ::= SIMPLE_STATEMENT | COMPOUND_STATEMENT\n\nSIMPLE_STATEMENT   ::=\n      "load" STRING\n    | "return" EXPR\n    | "continue"\n    | "break"\n    | EXPR\n\nCOMPOUND_STATEMENT ::=\n      IF_EXPR\n    | FOR_EXPR\n    | WHILE_EXPR\n    | DEF_FUNC\n\nEXPR               ::= \n      "let" IDENTIFIER "=" EXPR\n    | IDENTIFIER "=" EXPR\n      "let" IDENTIFIER "as" EXPR\n    | IDENTIFIER "as" EXPR\n    | IDENTIFIER ("+=" | "-=" | "*=" | "/=" | "//=" | "%=" | "^=") EXPR\n    | COMP_EXPR (("and" | "or") COMP_EXPR)*\n\nCOMP_EXPR          ::= \n      ARITH_EXPR (("==" | "<" | ">" | "<=" | ">=" | "!=") ARITH_EXPR)*\n    | "not" COMP_EXPR\n\nARITH_EXPR         ::= TERM (("+" | "-") TERM)*\n\nTERM               ::= FACTOR (("*" | "/" | "//" | "%") FACTOR)*\n\nFACTOR             ::= ("+" | "-") FACTOR | POWER\n\nPOWER              ::= CALL ("^" FACTOR)*\n\nCALL               ::= ATOM ("(" (EXPR ("," EXPR)*)? ")")?\n\nATOM               ::= \n      INT | FLOAT | STRING | IDENTIFIER\n    | "(" EXPR ")"\n    | LIST_EXPR\n    | LIST_INDEX\n    | IF_EXPR\n    | FOR_EXPR\n    | WHILE_EXPR\n    | DEF_FUNC\n    | COMMENT\n\nGET_INDEX         ::= IDENTIFIER "." EXPR\n\nLIST_EXPR         ::= "[" (EXPR ("," EXPR)*)? "]"\n\nHASHMAP_EXPR      ::= "{" (EXPR ("," STRING ":" EXPR)*)? "}"\n\nIF_EXPR           ::= \n      "if" EXPR "do" STATEMENT\n      (NEWLINE "elif" EXPR "do" STATEMENT)*\n      (NEWLINE "else" STATEMENT)?\n      NEWLINE "done"\n\nFOR_EXPR          ::=\n      "for" IDENTIFIER "=" EXPR "to" EXPR\n      ("step" EXPR)?\n      "do" STATEMENT\n      NEWLINE "done"\n\nWHILE_EXPR        ::= \n      "while" EXPR "do" STATEMENT\n      NEWLINE "done"\n\nDEF_FUNC          ::= \n      "defun" IDENTIFIER "(" (IDENTIFIER ("," IDENTIFIER)*)? ")"\n      ("->" EXPR)?\n      NEWLINE STATEMENT NEWLINE "done"\n\nCOMMENT           ::= "#" /[^\n]*/\n\n'
                        + ("=" * 96)
                        + "\n\nPlease scroll up to read from the beginning.\n"
                    )
                    continue
                if text.strip() == "license":
                    print(
                        ("=" * 96)
                        + '\n\nMIT License\n\nCopyright (c) 2025 MemeCoder\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the "Software"), to deal\nin the Software without restriction, including without limitation the rights\nto use, copy, modify, merge, publish, distribute, sublicense, and/or sell\ncopies of the Software, and to permit persons to whom the Software is\nfurnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all\ncopies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\nFITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\nAUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\nLIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\nOUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\nSOFTWARE.\n\n'
                        + ("=" * 96)
                        + "\n\nPlease scroll up to read from the beginning.\n"
                    )
                    continue
                if text.strip() == "copyright":
                    print("Copyright (c) 2025 MemeCoder.\nAll Rights Reserved.")
                    continue
                result, error = run("<stdin>", text)
                if error:
                    if hasattr(error, "as_string"):
                        print(f"{error.as_string()}")
                    else:
                        print(f"{error}")
                elif result:
                    if len(result.elements) == 1:
                        print(f"{repr(result.elements[0])}")
                    else:
                        print(f"{repr(result)}")
        except KeyboardInterrupt:
            print("\nexit...")
        except Exception as e:
            print(f"Shell error: {e}")
    elif len(sys.argv) == 2 and sys.argv[1] == "--version":
        print(f"Zerionyx {INFO}")
        return
    else:
        file_name = os.path.abspath(sys.argv[1])
        if not file_name.endswith(".zer"):
            print("Error: The file must have a '.zer' extension.")
            return
        if not os.path.isfile(file_name):
            print(f"Error: File '{os.path.abspath(file_name)}' does not exist.")
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
                if len(result.elements) == 1:
                    print(f"{repr(result.elements[0])}")
                else:
                    print(f"{repr(result)}")
        except IOError as e:
            print(f"Error reading file '{file_name}': {e}.")
            return
        except Exception as e:
            print(f"Interpreter error: {e}.")
            return


if __name__ == "__main__":
    main()
