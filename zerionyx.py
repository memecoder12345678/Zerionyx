import os
import sys
from src.interp import run, INFO, Fore, Style
from typing import TYPE_CHECKING
import io
import zipfile
import tempfile
import shutil
import atexit


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

if os.name != "nt" and not TYPE_CHECKING:
    try:
        import readline

        readline.parse_and_bind(r'"\e[A": history-search-backward')
        readline.parse_and_bind(r'"\e[B": history-search-forward')
        readline.parse_and_bind(r'"\e[C": forward-char')
        readline.parse_and_bind(r'"\e[D": backward-char')
    except ImportError:
        pass

MAGIC = b"ZEX-[</>]?"
MANIFEST_NAME = "__main__.zex.manifest"
_temp_dirs_to_clean = []
G = """

PROGRAM ::= STATEMENTS

STATEMENTS ::= STATEMENT (NEWLINE+ STATEMENT)* NEWLINE*

STATEMENT ::= SIMPLE_STATEMENT | COMPOUND_STATEMENT

SIMPLE_STATEMENT ::=
    "load" STRING
  | "return" [EXPR]
  | "continue"
  | "break"
  | "using" ["parent"] IDENTIFIER ("," IDENTIFIER)*
  | "del" IDENTIFIER ("," IDENTIFIER)*
  | EXPR

COMPOUND_STATEMENT ::=
    IF_EXPR
  | FOR_EXPR
  | WHILE_EXPR
  | NAMESPACE_EXPR
  | (DECORATOR+ DEF_FUNC)
  | DEF_FUNC

BODY ::= STATEMENT | (NEWLINE STATEMENTS "done")

EXPR ::= ASSIGNMENT_EXPR

ASSIGNMENT_EXPR ::=
    (IDENTIFIER ("," IDENTIFIER)* "=" EXPR)
  | (IDENTIFIER AUG_ASSIGN_OP EXPR)
  | (IDENTIFIER "as" IDENTIFIER)
  | LOGIC_EXPR

AUG_ASSIGN_OP ::= "+=" | "-=" | "*=" | "/=" | "//=" | "%=" | "^="

LOGIC_EXPR ::= COMP_EXPR (("and" | "or") COMP_EXPR)*

COMP_EXPR ::=
    "not" COMP_EXPR
  | ARITH_EXPR (("==" | "!=" | "<" | ">" | "<=" | ">=") ARITH_EXPR)*

ARITH_EXPR ::= TERM (("+" | "-") TERM)*

TERM ::= FACTOR (("*" | "/" | "//" | "%") FACTOR)*

FACTOR ::=
    "-" FACTOR
  | "*" FACTOR                      (* vargs unpacking *) 
  | "**" FACTOR                     (* kargs unpacking *)
  | DOLLAR_EXPR

DOLLAR_EXPR ::= POWER ("$" POWER)*  (* $ is for indexing instead of [] *)

POWER ::= CALL ("^" FACTOR)*        (* power operator *)

CALL ::= ATOM ( ("." IDENTIFIER) | ("(" [ARG_LIST] ")") )*

ARG_LIST ::= ARG ("," ARG)*

ARG ::= EXPR | (IDENTIFIER "=" EXPR)

ATOM ::=
    INT | FLOAT | STRING | IDENTIFIER
  | "(" EXPR ")"
  | LIST_EXPR
  | HASHMAP_EXPR
  | IF_EXPR
  | FOR_EXPR
  | WHILE_EXPR
  | DEF_FUNC
  | NAMESPACE_EXPR

LIST_EXPR ::= "[" [EXPR ("," EXPR)*] "]"

HASHMAP_EXPR ::= "{" [EXPR ":" EXPR ("," EXPR ":" EXPR)*] "}"

NAMESPACE_EXPR ::= "namespace" IDENTIFIER NEWLINE STATEMENTS "done"

IF_EXPR ::=
    "if" EXPR "do" BODY
    ("elif" EXPR "do" BODY)*
    ["else" "do" BODY]?

FOR_EXPR ::=
    ("for" FOR_IN_CLAUSE | FOR_RANGE_CLAUSES) "do" BODY

FOR_IN_CLAUSE ::= IDENTIFIER ("," IDENTIFIER)* "in" EXPR

FOR_RANGE_CLAUSES ::= FOR_RANGE_CLAUSE ("," FOR_RANGE_CLAUSE)*

FOR_RANGE_CLAUSE ::= IDENTIFIER ["=" EXPR] "to" EXPR ["step" EXPR]

WHILE_EXPR ::= "while" EXPR "do" BODY

DECORATOR ::= "&" EXPR NEWLINE*

DEF_FUNC ::=
    "defun" [IDENTIFIER] "(" [PARAM_LIST] ")" ("->" EXPR | (NEWLINE STATEMENTS "done"))

PARAM_LIST ::= (PARAMS ["," VAR_PARAMS]) | VAR_PARAMS

PARAMS ::= PARAM ("," PARAM)*

PARAM ::= IDENTIFIER ["=" EXPR]

VAR_PARAMS ::= (VARARGS_PARAM ["," KWARGS_PARAM]) | KWARGS_PARAM

VARARGS_PARAM ::= "*" IDENTIFIER

KWARGS_PARAM ::= "**" IDENTIFIER

"""
L = """

MIT License

WARNING: This project contains code adapted from multiple public sources.

Some components are originally based on David Callanan's interpreter tutorial (2019),
licensed under the MIT License. Other parts are believed to derive from Fus3n's version,
which did not include an explicit license but was publicly shared for free use and modification.

Only modifications made by MemeCoder are explicitly claimed under copyright.
Reasonable efforts have been made to trace original authors.
If you are an original author and believe attribution or licensing is missing,
please contact MemeCoder.

Credits:
- David Callanan (2019)
- Fus3n (2022, no license stated)
- Modified by angelcaru (2024)
- Further modified by MemeCoder (2025)

Copyright (c) 2019-2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""




def cleanup_temp_dirs():
    for path in _temp_dirs_to_clean:
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
            except OSError:
                pass


atexit.register(cleanup_temp_dirs)


def pack_zex(output_file, main_script, other_files):
    if not output_file.endswith(".zex"):
        print(
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}Output file must have a '.zex' extension{Fore.RESET}{Style.RESET_ALL}"
        )
        return

    all_files = [main_script] + other_files
    for f in all_files:
        if not os.path.isfile(f):
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}Input file '{os.path.abspath(f)}' not found{Fore.RESET}{Style.RESET_ALL}"
            )
            return

    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(MANIFEST_NAME, os.path.basename(main_script))
            for f in all_files:
                with open(f, "r", encoding="utf-8") as file:
                    content = file.read()

                lines = content.splitlines()
                processed_lines = [line.strip() for line in lines]
                processed_content = ";".join(processed_lines)

                zf.writestr(os.path.basename(f), processed_content)

        with open(output_file, "wb") as f:
            f.write(MAGIC)
            f.write(zip_buffer.getvalue())

        print(
            f"{Fore.GREEN}Successfully packed to '{os.path.abspath(output_file)}'{Fore.RESET}"
        )

    except Exception as e:
        print(
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Packing Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{e}{Fore.RESET}"
        )


def run_zex(file_path):
    temp_dir = tempfile.mkdtemp(prefix="zex_")
    _temp_dirs_to_clean.append(temp_dir)

    try:
        with open(file_path, "rb") as f:
            if f.read(len(MAGIC)) != MAGIC:
                print(
                    f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}Not a valid .zex file (invalid magic byte){Fore.RESET}{Style.RESET_ALL}"
                )
                sys.exit(1)

            with zipfile.ZipFile(f) as zf:
                if MANIFEST_NAME not in zf.namelist():
                    print(
                        f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}Manifest '{MANIFEST_NAME}' not found in the .zex archive{Fore.RESET}{Style.RESET_ALL}"
                    )
                    sys.exit(1)

                main_script_name = zf.read(MANIFEST_NAME).decode("utf-8").strip()

                zf.extractall(temp_dir)

                main_script_path = os.path.join(temp_dir, main_script_name)

                if not os.path.isfile(main_script_path):
                    print(
                        f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}Main script '{main_script_name}' specified in manifest not found in archive{Fore.RESET}{Style.RESET_ALL}"
                    )
                    sys.exit(1)

                with open(main_script_path, "r", encoding="utf-8") as file:
                    text = file.read()

                text = text.splitlines()
                for i in range(len(text)):
                    text[i] = text[i].strip()

                result, error = run(main_script_path, "\n".join(text))

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

    except zipfile.BadZipFile:
        print(
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}Invalid or corrupted .zex archive{Fore.RESET}{Style.RESET_ALL}"
        )
        sys.exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Interpreter Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}{e}{Fore.RESET}"
        )
        sys.exit(1)
    finally:
        if temp_dir in _temp_dirs_to_clean:
            _temp_dirs_to_clean.remove(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)


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
                        + L
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
    elif len(sys.argv) > 1 and sys.argv[1] == "--pack":
        if len(sys.argv) < 4:
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Usage{Fore.RESET}{Style.RESET_ALL}: {os.path.basename(sys.argv[0])} --pack <output.zex> <main_script.zyx> [other_files...]"
            )
            return
        output_file = sys.argv[2]
        main_script = sys.argv[3]
        try:
            other_files = sys.argv[4:]
        except IndexError:
            other_files = []
        pack_zex(output_file, main_script, other_files)
        return
    elif len(sys.argv) == 2 and sys.argv[1] == "--version":
        print(f"Zerionyx {INFO}")
        return
    else:
        file_name = os.path.abspath(sys.argv[1])

        if not file_name.endswith((".zyx", ".zex")):
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}The file must have a '.zyx' or '.zex' extension{Fore.RESET}{Style.RESET_ALL}"
            )
            return

        if not os.path.isfile(file_name) or not os.path.exists(file_name):
            print(
                f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Error{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}File '{os.path.abspath(file_name)}' does not exist{Fore.RESET}{Style.RESET_ALL}"
            )
            return

        if file_name.endswith(".zex"):
            run_zex(file_name)
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
