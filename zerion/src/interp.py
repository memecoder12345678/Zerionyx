import os
import sys
import time
import random
import math

from .nodes import *
from .types_ import *
from .consts import *
from .errors import (
    TError,
    FError,
    MError,
    Error,
    RTError,
    InvalidSyntaxError,
)
from .utils import Token
from shutil import rmtree, copy
from .lex import Lexer, RTResult

import urllib.request
import urllib.error
from urllib.parse import unquote
import re
import subprocess
import socket
import uuid
import time
import ssl
import hashlib
import zlib

from colorama import init

init()
ssl._create_default_https_context = ssl._create_unverified_context
BUILTIN_FUNCTIONS = []
global_symbol_table = SymbolTable()


class ThreadWrapper(Object):
    def __init__(self, thread):
        super().__init__()
        self.thread = thread

    def copy(self):
        copy = ThreadWrapper(self.thread)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def type(self):
        return "<thread>"

    def __str__(self):
        return f"<thread id={self.thread.ident} active={self.thread.is_alive()}>"

    def __repr__(self):
        return self.__str__()

    def join(self, timeout=None):
        return self.thread.join(timeout)

    def is_alive(self):
        return self.thread.is_alive()

    def cancel(self):
        if self.thread.is_alive():
            self.thread._stop()


def load_module(fn, interpreter, context):
    result = None
    with open(fn, "r", encoding="utf-8") as f:
        text = f.read()
    text = text.splitlines()
    for i in range(len(text)):
        text[i] = text[i].strip()

    lexer = Lexer(fn, "\n".join(text))
    tokens, error = lexer.make_tokens()
    if error:
        return None, error

    try:
        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return None, ast.error

        context = Context("<module>")
        context.symbol_table = global_symbol_table
        context.private_symbol_table = SymbolTable()
        context.private_symbol_table.set("is_main", Number(0))
        result = interpreter.visit(ast.node, context)
        result.value = "" if str(result.value) == "none" else result.value
        return result.value, result.error
    except KeyboardInterrupt:
        print("Interrupt Error: User Terminated")
        sys.exit(2)


class Function(BaseFunction):
    __slots__ = ("body_node", "arg_names", "should_auto_return")

    def __init__(self, name, body_node, arg_names, should_auto_return):
        super().__init__(name)
        self.body_node = body_node
        self.arg_names = arg_names
        self.should_auto_return = should_auto_return

    def execute(self, args):
        res = RTResult()
        interpreter = Interpreter()
        exec_ctx = self.generate_new_context()

        res.register(self.check_and_populate_args(self.arg_names, args, exec_ctx))
        if res.should_return():
            return res

        value = res.register(interpreter.visit(self.body_node, exec_ctx))
        if res.should_return() and res.func_return_value == None:
            return res

        ret_value = (
            (value if self.should_auto_return else None)
            or res.func_return_value
            or None_.none
        )
        return res.success(ret_value)

    def copy(self):
        copy = Function(
            self.name, self.body_node, self.arg_names, self.should_auto_return
        )
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def type(self):
        return "<func>"

    def __repr__(self):
        return f"<func {self.name}>"


class BuiltInFunction(BaseFunction):

    def __init__(self, name):
        super().__init__(name)

    def execute(self, args):
        res = RTResult()
        exec_ctx = self.generate_new_context()

        method_name = f"execute_{self.name}"
        method = getattr(self, method_name, self.no_visit_method)

        res.register(self.check_and_populate_args(method.arg_names, args, exec_ctx))
        if res.should_return():
            return res

        return_value = res.register(method(exec_ctx))
        if res.should_return():
            return res
        return res.success(return_value)

    def no_visit_method(self, node, context):
        raise Exception(f"No execute_{self.name} method defined")

    def copy(self):
        copy = BuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in func {self.name}>"

    def execute_println(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        if isinstance(value, String):
            print(value.value)
            return RTResult().success(None_.none)

        print(repr(exec_ctx.symbol_table.get("value")))
        return RTResult().success(None_.none)

    execute_println.arg_names = ["value"]

    def execute_print(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        if isinstance(value, String):
            print(value.value, end="")
            return RTResult().success(None_.none)

        print(repr(exec_ctx.symbol_table.get("value")), end="")
        return RTResult().success(None_.none)

    execute_print.arg_names = ["value"]

    def execute_input(self, exec_ctx):
        prompt = exec_ctx.symbol_table.get("prompt")
        text = input(prompt)
        return RTResult().success(String(text))

    execute_input.arg_names = ["prompt"]

    def execute_clear(self, exec_ctx):
        os.system("cls" if os.name == "nt" else "clear")
        return RTResult().success(None_.none)

    execute_clear.arg_names = []

    def execute_type(self, exec_ctx):
        data = exec_ctx.symbol_table.get("value")
        if isinstance(data, None_):
            return RTResult().success(None_.none)
        return RTResult().success(String(data.type()))

    execute_type.arg_names = ["value"]

    def execute_is_none(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        return RTResult().success(
            Number.true if isinstance(value, None_) else Number.false
        )

    execute_is_none.arg_names = ["value"]

    def execute_is_num(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), Number)
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_num.arg_names = ["value"]

    def execute_is_str(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), String)
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_str.arg_names = ["value"]

    def execute_is_list(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), List)
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_list.arg_names = ["value"]

    def execute_is_func(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), BaseFunction)
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_func.arg_names = ["value"]

    def execute_sort_fp(self, exec_ctx):
        lst = exec_ctx.symbol_table.get("value")
        reverse = exec_ctx.symbol_table.get("reverse")
        if not isinstance(lst, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'sort' must be a list",
                    exec_ctx,
                )
            )
        if not isinstance(reverse, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'sort' must be a number",
                    exec_ctx,
                )
            )

        if reverse.value == 1:
            lst.elements.sort(key=lambda x: x.value, reverse=True)
        elif reverse.value == 0:
            lst.elements.sort(key=lambda x: x.value)
        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'sort' must be a boolean",
                    exec_ctx,
                )
            )
        return RTResult().success(lst)

    execute_sort_fp.arg_names = ["value", "reverse"]

    def execute_append(self, exec_ctx):
        obj_ = exec_ctx.symbol_table.get("object")
        value = exec_ctx.symbol_table.get("value")

        if isinstance(obj_, List):
            obj_.elements.append(value)
            return RTResult().success(value)
        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'append' must be a list",
                    exec_ctx,
                )
            )

    execute_append.arg_names = ["object", "value"]

    def execute_pop(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list")
        index = exec_ctx.symbol_table.get("index")
        if not isinstance(list_, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'pop' must be a list",
                    exec_ctx,
                )
            )

        if not isinstance(index, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'pop' must be a number",
                    exec_ctx,
                )
            )

        try:
            element = list_.elements.pop(int(index.value))
        except:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Element at this index could not be removed from list because index is out of bounds",
                    exec_ctx,
                )
            )
        return RTResult().success(element)

    execute_pop.arg_names = ["list", "index"]

    def execute_extend(self, exec_ctx: Context):
        listA = exec_ctx.symbol_table.get("listA")
        listB = exec_ctx.symbol_table.get("listB")

        if not isinstance(listA, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'extend' must be a list",
                    exec_ctx,
                )
            )

        if not isinstance(listB, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'extend' must be a list",
                    exec_ctx,
                )
            )

        listA.elements.extend(listB.elements)
        return RTResult().success(None_.none)

    execute_extend.arg_names = ["listA", "listB"]

    def execute_insert(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list_")
        element = exec_ctx.symbol_table.get("element")
        index = exec_ctx.symbol_table.get("index")
        if not isinstance(list_, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'insert' must be a list",
                    exec_ctx,
                )
            )

        if not isinstance(index, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'insert' must be a number",
                    exec_ctx,
                )
            )
        list_.elements.insert(int(index.value), element)
        return RTResult().success(None_.none)

    execute_insert.arg_names = ["list_", "index", "element"]

    def execute_replace_fp(self, exec_ctx):
        string = exec_ctx.symbol_table.get("string")
        value = exec_ctx.symbol_table.get("value")
        with_val = exec_ctx.symbol_table.get("with")

        if not isinstance(string, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'replace' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'replace' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(with_val, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'replace' must be a string",
                    exec_ctx,
                )
            )
        val = string.value.replace(value.value, with_val.value)
        return RTResult().success(String(val))

    execute_replace_fp.arg_names = ["string", "value", "with"]

    def execute_len(self, exec_ctx):
        value_ = exec_ctx.symbol_table.get("value")

        if isinstance(value_, List):
            return RTResult().success(Number(len(value_.elements)))
        elif isinstance(value_, String):
            return RTResult().success(Number(len(value_.value)))
        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'len' must be a list or string",
                    exec_ctx,
                )
            )

    execute_len.arg_names = ["value"]

    def execute_sleep_fp(self, exec_ctx):
        seconds = exec_ctx.symbol_table.get("seconds")

        if not isinstance(seconds, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'sleep' must be a number",
                    exec_ctx,
                )
            )

        time.sleep(seconds.value)
        return RTResult().success(None_.none)

    execute_sleep_fp.arg_names = ["seconds"]

    def execute_exit_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        sys.exit(int(value.value))

    execute_exit_fp.arg_names = ["value"]

    def execute_str_slice_fp(self, exec_ctx):
        string = exec_ctx.symbol_table.get("string")
        start = exec_ctx.symbol_table.get("start")
        end = exec_ctx.symbol_table.get("end")

        if not isinstance(string, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'str_slice' must be a string",
                    exec_ctx,
                )
            )

        if not isinstance(start, Number) and not isinstance(start, None_):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'str_slice' must be a number or none",
                    exec_ctx,
                )
            )

        if not isinstance(end, Number) and not isinstance(end, None_):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'str_slice' must be a number or none",
                    exec_ctx,
                )
            )

        sliced_string = string.value[int(start.value) if not isinstance(start, None_) else None : int(end.value) if not isinstance(end, None_) else None]
        return RTResult().success(String(sliced_string))

    execute_str_slice_fp.arg_names = ["string", "start", "end"]

    def execute_open_fp(self, exec_ctx):
        file_path = exec_ctx.symbol_table.get("file_path")

        try:
            file_name = os.path.splitext(file_path.value)[0]
            return RTResult().success(File(file_name, file_path.value))
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to open file "{file_path.value}": ' + str(e),
                    exec_ctx,
                )
            )

    execute_open_fp.arg_names = ["file_path"]

    def execute_read_fp(self, exec_ctx):
        file = exec_ctx.symbol_table.get("file")

        try:
            with open(file.path.__str__(), "r", encoding="utf-8") as f:
                return RTResult().success(String(f.read()))
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to read file "{file.path}"\n' + str(e),
                    exec_ctx,
                )
            )

    execute_read_fp.arg_names = ["file"]

    def execute_write_fp(self, exec_ctx):
        file = exec_ctx.symbol_table.get("file")
        mode = exec_ctx.symbol_table.get("mode")
        text = exec_ctx.symbol_table.get("text")

        try:
            with open(file.path.__str__(), mode.__str__(), encoding="utf-8") as f:
                f.write(text.value)
            return RTResult().success(Number.none)
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to write to file "{file.path}": ' + str(e),
                    exec_ctx,
                )
            )

    execute_write_fp.arg_names = ["file", "mode", "text"]

    def execute_exists_fp(self, exec_ctx):
        file_path = exec_ctx.symbol_table.get("file_path")

        if isinstance(file_path, String):
            file_path = file_path.value

        elif isinstance(file_path, File):
            file_path = file_path.path

        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'exists' must be a string",
                    exec_ctx,
                )
            )

        try:
            return RTResult().success(
                Number.true if os.path.exists(file_path) else Number.false
            )
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if file exists '{file_path}': " + str(e),
                    exec_ctx,
                )
            )

    execute_exists_fp.arg_names = ["file_path"]

    def execute_time_fp(self, exec_ctx):
        return RTResult().success(Number(time.time()))

    execute_time_fp.arg_names = []

    def execute_get_env_fp(self, exec_ctx):
        name = exec_ctx.symbol_table.get("name")

        if not isinstance(name, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'get_env' must be a string",
                    exec_ctx,
                )
            )

        value = os.getenv(name.value)

        if value is None:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Environment variable '{name.value}' does not exist",
                    exec_ctx,
                )
            )

        return RTResult().success(String(value))

    execute_get_env_fp.arg_names = ["name"]

    def execute_set_env_fp(self, exec_ctx):
        name = exec_ctx.symbol_table.get("name")
        value = exec_ctx.symbol_table.get("value")

        if not isinstance(name, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'set_env' must be a string",
                    exec_ctx,
                )
            )

        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'set_env' must be a string",
                    exec_ctx,
                )
            )

        try:
            os.environ[name.value] = value.value
            return RTResult().success(None_.none)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to set environment variable '{name.value}': " + str(e),
                    exec_ctx,
                )
            )

    execute_set_env_fp.arg_names = ["name", "value"]

    def execute_get_dir_fp(self, exec_ctx):
        try:
            return RTResult().success(String(os.getcwd()))
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get current directory: " + str(e),
                    exec_ctx,
                )
            )

    execute_get_dir_fp.arg_names = []

    def execute_set_dir_fp(self, exec_ctx):
        name = exec_ctx.symbol_table.get("name")

        if not isinstance(name, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'set_dir' must be a string",
                    exec_ctx,
                )
            )

        if not os.path.exists(name.value):
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Directory '{name.value}' does not exist",
                    exec_ctx,
                )
            )

        try:
            os.chdir(name.value)
            return RTResult().success(None_.none)
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to set current directory to '{name.value}': " + str(e),
                    exec_ctx,
                )
            )

    execute_set_dir_fp.arg_names = ["name"]

    def execute_rand_fp(self, exec_ctx):
        return RTResult().success(Number(random.random()))

    execute_rand_fp.arg_names = []

    def execute_rand_int_fp(self, exec_ctx):
        min = exec_ctx.symbol_table.get("min")
        max = exec_ctx.symbol_table.get("max")

        if not isinstance(min, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'rand_int' must be a number",
                    exec_ctx,
                )
            )

        if not isinstance(max, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'rand_int' must be a number",
                    exec_ctx,
                )
            )

        return RTResult().success(
            Number(random.randint(int(min.value), int(max.value)))
        )

    execute_rand_int_fp.arg_names = ["min", "max"]

    def execute_rand_float_fp(self, exec_ctx):
        min = exec_ctx.symbol_table.get("min")
        max = exec_ctx.symbol_table.get("max")

        if not isinstance(min, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'rand_float' must be a number",
                    exec_ctx,
                )
            )

        if not isinstance(max, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'rand_float' must be a number",
                    exec_ctx,
                )
            )

        return RTResult().success(Number(random.randint(min.value, max.value)))

    execute_rand_float_fp.arg_names = ["min", "max"]

    def execute_rand_choice_fp(self, exec_ctx):
        arr = exec_ctx.symbol_table.get("arr")

        if not isinstance(arr, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'rand_choice' must be a list",
                    exec_ctx,
                )
            )

        if len(arr.elements) == 0:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Array passed to 'rand_choice' is empty",
                    exec_ctx,
                )
            )

        return RTResult().success(
            arr.elements[random.randrange(0, len(arr.elements) - 1)]
        )

    execute_rand_choice_fp.arg_names = ["arr"]

    def execute_to_str(self, exec_ctx):
        return RTResult().success(String(str(exec_ctx.symbol_table.get("value"))))

    execute_to_str.arg_names = ["value"]

    def execute_to_int(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        supress_error = exec_ctx.symbol_table.get("supress_error")

        if not isinstance(supress_error, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'to_int' must be a number",
                    exec_ctx,
                )
            )
        if supress_error.value == 1:
            supress_error_ = True
        elif supress_error.value == 0:
            supress_error_ = False
        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'to_int' must be a boolean",
                    exec_ctx,
                )
            )

        if isinstance(value, Number):
            return RTResult().success(Number(int(value.value)))
        elif isinstance(value, String):
            try:
                return RTResult().success(Number(int(value.value)))
            except ValueError:
                if supress_error_:
                    return RTResult().success(Number.none)
                else:
                    return RTResult().failure(
                        RTError(
                            self.pos_start,
                            self.pos_end,
                            f"Failed to convert '{value.value}' of type '{value.type()}' to integer",
                            exec_ctx,
                        )
                    )
        else:
            if supress_error_:
                return RTResult().success(Number.none)
            else:
                return RTResult().failure(
                    TError(
                        self.pos_start,
                        self.pos_end,
                        f"Failed to convert value of type '{value.type()}' to integer",
                        exec_ctx,
                    )
                )

    execute_to_int.arg_names = ["value", "supress_error"]

    def execute_to_float(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        supress_error = exec_ctx.symbol_table.get("supress_error")

        if not isinstance(supress_error, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'to_float' must be a number",
                    exec_ctx,
                )
            )

        if supress_error.value == 1:
            supress_error_ = True
        elif supress_error.value == 0:
            supress_error_ = False
        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'to_float' must be a boolean",
                    exec_ctx,
                )
            )

        if isinstance(value, Number):
            return RTResult().success(Number(float(value.value)))
        elif isinstance(value, String):
            try:
                return RTResult().success(Number(float(value.value)))
            except ValueError:
                if supress_error_:
                    return RTResult().success(Number.none)
                else:
                    return RTResult().failure(
                        RTError(
                            self.pos_start,
                            self.pos_end,
                            f"Failed to convert '{value.value}' of type '{value.type()}' to float",
                            exec_ctx,
                        )
                    )
        else:
            if supress_error_:
                return RTResult().success(Number.none)
            else:
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        f"Failed to convert value of type '{value.type()}' to float",
                        exec_ctx,
                    )
                )

    execute_to_float.arg_names = ["value", "supress_error"]

    def execute_join_fp(self, exec_ctx):
        sep = exec_ctx.symbol_table.get("sep")
        iterables = exec_ctx.symbol_table.get("elements")
        if not isinstance(sep, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'join' must be a string",
                    exec_ctx,
                )
            )

        if isinstance(iterables, List):
            if len(iterables.elements) == 0:
                return RTResult().success(String(""))

            return RTResult().success(
                String(
                    sep.value.join(
                        [str(element) for element in iterables.elements]
                    )
                )
            )
        elif isinstance(iterables, String):
            if len(iterables) == 0:
                return RTResult().success(String(""))
            return RTResult().success(
                String(sep.value.join([str(element) for element in iterables.value]))
            )
        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'join' must be a list or a string",
                    exec_ctx,
                )
            )

    execute_join_fp.arg_names = ["sep", "elements"]

    def execute_system_fp(self, exec_ctx):
        command = exec_ctx.symbol_table.get("command")

        if not isinstance(command, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'system' must be a string",
                    exec_ctx,
                )
            )

        try:
            os.system(command.value)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to execute '{command.value}': " + str(e),
                    exec_ctx,
                )
            )

        return RTResult().success(None_.none)

    execute_system_fp.arg_names = ["command"]

    def execute_panic(self, exec_ctx):
        msg = exec_ctx.symbol_table.get("message")
        err_type = exec_ctx.symbol_table.get("err_type")

        if not isinstance(msg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'panic' must be a string",
                    exec_ctx,
                )
            )

        if not isinstance(err_type, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'panic' must be a string ['RT' (Runtime Error), 'M' (Math Error), 'F' (File Error) or 'T' (Type Error)]",
                    exec_ctx,
                )
            )

        err_type_value = err_type.value.upper()

        if err_type_value == "RT":
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, msg, exec_ctx)
            )
        elif err_type_value == "M":
            return RTResult().failure(
                MError(self.pos_start, self.pos_end, msg, exec_ctx)
            )
        elif err_type_value == "F":
            return RTResult().failure(
                FError(self.pos_start, self.pos_end, msg, exec_ctx)
            )
        elif err_type_value == "T":
            return RTResult().failure(
                TError(self.pos_start, self.pos_end, msg, exec_ctx)
            )
        else:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'panic' must be a 'RT' (Runtime Error), 'M' (Math Error), 'F' (File Error) or 'T' (Type Error)",
                    exec_ctx,
                )
            )

    execute_panic.arg_names = ["message", "err_type"]

    def execute_split_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("string")
        sep = exec_ctx.symbol_table.get("sep")

        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'split' must be a string",
                    exec_ctx,
                )
            )

        if not isinstance(sep, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'split' must be a string",
                    exec_ctx,
                )
            )

        if len(sep.value) == 0:
            return RTResult().success(
                List([String(string) for string in list(value.value)])
            )

        return RTResult().success(
            List([String(string) for string in value.value.split(sep.value)])
        )

    execute_split_fp.arg_names = ["string", "sep"]

    def execute_strip_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("string")
        sep = exec_ctx.symbol_table.get("sep")

        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'strip' must be a string",
                    exec_ctx,
                )
            )

        if not isinstance(sep, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'strip' must be a string",
                    exec_ctx,
                )
            )
        return RTResult().success(String(value.value.strip(sep.value)))

    execute_strip_fp.arg_names = ["string", "sep"]

    def execute_to_upper_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("string")

        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'to_upper' must be a string",
                    exec_ctx,
                )
            )
        return RTResult().success(String(value.value.upper()))

    execute_to_upper_fp.arg_names = ["string"]

    def execute_to_lower_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("string")

        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'to_lower' must be a string",
                    exec_ctx,
                )
            )
        return RTResult().success(String(value.value.lower()))

    execute_to_lower_fp.arg_names = ["string"]

    def execute_ctime_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("time")
        if not isinstance(value, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'ctime' must be a number",
                    exec_ctx,
                )
            )
        return RTResult().success(String(time.ctime(int(value.value))))

    execute_ctime_fp.arg_names = ["time"]

    def execute_list_dir_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("dir_path")
        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'list_dir' must be a string",
                    exec_ctx,
                )
            )
        if not os.path.isdir(value.value):
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Directory '{value.value}' does not exist",
                    exec_ctx,
                )
            )
        try:
            return RTResult().success(
                List([String(string) for string in os.listdir(value.value)])
            )
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to list directory: {e}",
                    exec_ctx,
                )
            )

    execute_list_dir_fp.arg_names = ["dir_path"]

    def execute_mkdir_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("dir_path")
        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'make_dir' must be a string",
                    exec_ctx,
                )
            )
        if os.path.exists(value.value):
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Directory '{value.value}' already exists",
                    exec_ctx,
                )
            )
        os.mkdir(value.value)
        return RTResult().success(None_.none)

    execute_mkdir_fp.arg_names = ["dir_path"]

    def execute_remove_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("file_path")
        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'remove_file' must be a string",
                    exec_ctx,
                )
            )
        if not os.path.exists(value.value):
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"File '{value.value}' does not exist",
                    exec_ctx,
                )
            )
        try:
            os.remove(value.value)
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to remove file: " + str(e),
                    exec_ctx,
                )
            )
        return RTResult().success(None_.none)

    execute_remove_fp.arg_names = ["file_path"]

    def execute_rename_fp(self, exec_ctx):
        value1 = exec_ctx.symbol_table.get("old_file_path")
        value2 = exec_ctx.symbol_table.get("new_file_path")
        if not isinstance(value1, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'rename' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(value2, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'rename' must be a string",
                    exec_ctx,
                )
            )

        if not os.path.exists(value1.value):
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"File or directory '{value1.value}' does not exist",
                    exec_ctx,
                )
            )
        try:
            os.rename(value1.value, value2.value)
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to rename file: {e}",
                    exec_ctx,
                )
            )
        return RTResult().success(None_.none)

    execute_rename_fp.arg_names = ["old_file_path", "new_file_path"]

    def execute_rmtree_fp(self, exec_ctx):
        value1 = exec_ctx.symbol_table.get("dir_path")
        if not isinstance(value1, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'remove_dir' must be a string",
                    exec_ctx,
                )
            )
        if not os.path.isdir(value1.value):
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"'{value1.value}' is not a directory",
                    exec_ctx,
                )
            )
        try:
            rmtree(value1.value)
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to remove directory: {e}",
                    exec_ctx,
                )
            )
        return RTResult().success(None_.none)

    execute_rmtree_fp.arg_names = ["dir_path"]

    def execute_copy_fp(self, exec_ctx):
        value1 = exec_ctx.symbol_table.get("src_path")
        value2 = exec_ctx.symbol_table.get("dst_path")
        if not isinstance(value1, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'copy' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(value2, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'copy' must be a string",
                    exec_ctx,
                )
            )
        if not os.path.exists(value1.value):
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"'{value1.value}' does not exist",
                    exec_ctx,
                )
            )
        try:
            copy(value1.value, value2.value)
        except Exception as e:
            return RTResult().failure(
                FError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to copy file: {e}",
                    exec_ctx,
                )
            )
        return RTResult().success(None_.none)

    execute_copy_fp.arg_names = ["src_path", "dst_path"]

    def execute_keyboard_write_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")

        if not isinstance(text, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'keyboard_write' must be a string",
                    exec_ctx,
                )
            )

        try:
            import keyboard

            keyboard.write(text.value)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available. Install with: pip install keyboard",
                    exec_ctx,
                )
            )

        return RTResult().success(None_.none)

    execute_keyboard_write_fp.arg_names = ["text"]

    def execute_keyboard_press_fp(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")

        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'keyboard_press' must be a string",
                    exec_ctx,
                )
            )

        try:
            import keyboard

            keyboard.press(key.value)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available. Install with: pip install keyboard",
                    exec_ctx,
                )
            )

        return RTResult().success(None_.none)

    execute_keyboard_press_fp.arg_names = ["key"]

    def execute_keyboard_release_fp(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")

        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'keyboard_release' must be a string",
                    exec_ctx,
                )
            )

        try:
            import keyboard

            keyboard.release(key.value)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available. Install with: pip install keyboard",
                    exec_ctx,
                )
            )

        return RTResult().success(None_.none)

    execute_keyboard_release_fp.arg_names = ["key"]

    def execute_keyboard_wait_fp(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")

        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'keyboard_wait' must be a string",
                    exec_ctx,
                )
            )

        try:
            import keyboard

            keyboard.wait(key.value)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available. Install with: pip install keyboard",
                    exec_ctx,
                )
            )

        return RTResult().success(None_.none)

    execute_keyboard_wait_fp.arg_names = ["key"]

    def execute_keyboard_is_pressed_fp(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")

        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'keyboard_is_pressed' must be a string",
                    exec_ctx,
                )
            )

        try:
            import keyboard

            is_pressed = keyboard.is_pressed(key.value)
            return RTResult().success(Number.true if is_pressed else Number.false)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available. Install with: pip install keyboard",
                    exec_ctx,
                )
            )

    execute_keyboard_is_pressed_fp.arg_names = ["key"]

    def execute_thread_start_fp(self, exec_ctx):
        func = exec_ctx.symbol_table.get("func")
        args = exec_ctx.symbol_table.get("args")

        if not isinstance(func, BaseFunction):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'thread_start' must be a function",
                    exec_ctx,
                )
            )

        if not isinstance(args, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'thread_start' must be a list",
                    exec_ctx,
                )
            )

        try:
            import threading

            new_context = Context("<thread>")
            new_context.symbol_table = SymbolTable()
            new_context.private_symbol_table = SymbolTable()
            new_context.private_symbol_table.set("is_main", Number.false)

            def thread_wrapper():
                context = func.generate_new_context()
                context.private_symbol_table.set("is_main", Number.false)
                func.check_and_populate_args(func.arg_names, args.elements, context)
                interpreter = Interpreter()
                return interpreter.visit(func.body_node, context)

            thread = threading.Thread(target=thread_wrapper, daemon=True)
            thread.start()
            return RTResult().success(ThreadWrapper(thread))

        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "threading module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to start thread: {str(e)}",
                    exec_ctx,
                )
            )

    execute_thread_start_fp.arg_names = ["func", "args"]

    def execute_thread_sleep_fp(self, exec_ctx):
        seconds = exec_ctx.symbol_table.get("seconds")

        if not isinstance(seconds, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'thread_sleep' must be a number",
                    exec_ctx,
                )
            )

        try:
            import time

            time.sleep(seconds.value)
            return RTResult().success(None_.none)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to sleep thread: {str(e)}",
                    exec_ctx,
                )
            )

    execute_thread_sleep_fp.arg_names = ["seconds"]

    def execute_thread_join_fp(self, exec_ctx):
        thread = exec_ctx.symbol_table.get("thread")
        timeout = exec_ctx.symbol_table.get("timeout")

        if not isinstance(thread, ThreadWrapper):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'thread_join' must be a thread",
                    exec_ctx,
                )
            )

        if not isinstance(timeout, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'thread_join' must be a number",
                    exec_ctx,
                )
            )

        try:
            thread.join(timeout.value)
            return RTResult().success(None_.none)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to join thread: {str(e)}",
                    exec_ctx,
                )
            )

    execute_thread_join_fp.arg_names = ["thread", "timeout"]

    def execute_thread_is_alive_fp(self, exec_ctx):
        thread = exec_ctx.symbol_table.get("thread")

        if not isinstance(thread, ThreadWrapper):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'thread_is_alive' must be a thread",
                    exec_ctx,
                )
            )

        return RTResult().success(Number.true if thread.is_alive() else Number.false)

    execute_thread_is_alive_fp.arg_names = ["thread"]

    def execute_thread_cancel_fp(self, exec_ctx):
        thread = exec_ctx.symbol_table.get("thread")

        if not isinstance(thread, ThreadWrapper):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'thread_cancel' must be a thread",
                    exec_ctx,
                )
            )

        try:
            thread.cancel()
            return RTResult().success(None_.none)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to cancel thread: {str(e)}",
                    exec_ctx,
                )
            )

    execute_thread_cancel_fp.arg_names = ["thread"]

    def execute_is_thread(self, exec_ctx):
        thread = exec_ctx.symbol_table.get("thread")
        return RTResult().success(
            Number.true if isinstance(thread, ThreadWrapper) else Number.false
        )

    execute_is_thread.arg_names = ["thread"]

    def execute_ord_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")

        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'ord' must be a string",
                    exec_ctx,
                )
            )

        if len(value.value) != 1:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "String passed to 'ord' must be a single character",
                    exec_ctx,
                )
            )

        return RTResult().success(Number(ord(value.value)))

    execute_ord_fp.arg_names = ["value"]

    def execute_chr_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")

        if not isinstance(value, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'char' must be a number",
                    exec_ctx,
                )
            )

        try:
            return RTResult().success(String(chr(int(value.value))))
        except ValueError:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Value passed to 'char' is out of range",
                    exec_ctx,
                )
            )

    execute_chr_fp.arg_names = ["value"]

    def execute_get_ip_fp(self, exec_ctx):
        try:
            with urllib.request.urlopen("https://api.ipify.org") as res_:
                return RTResult.success(String(res_.read().decode()))
        except:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Failed to retrieve IP address",
                    exec_ctx,
                )
            )

    execute_get_ip_fp.arg_names = []

    def execute_get_mac_fp(self, exec_ctx):
        try:
            mac = uuid.getnode()
            mac_addr = ":".join(
                ["{:02x}".format((mac >> ele) & 0xFF) for ele in range(40, -1, -8)]
            )
            return RTResult().success(String(mac_addr))
        except:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Failed to retrieve MAC address",
                    exec_ctx,
                )
            )

    execute_get_mac_fp.arg_names = []

    def execute_ping_fp(self, exec_ctx):
        host = exec_ctx.symbol_table.get("host")
        if not isinstance(host, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'ping' must be a string",
                    exec_ctx,
                )
            )
        try:
            t0 = time.time()
            subprocess.check_output(
                ["ping", "-n", "1", host], stderr=subprocess.DEVNULL
            )
            t1 = time.time()
            return [str(round((t1 - t0) * 1000)) + " ms"]
        except:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to ping {host}",
                    exec_ctx,
                )
            )

    execute_ping_fp.arg_names = ["host"]

    def execute_downl_fp(self, exec_ctx):
        def sanitize_filename(filename):
            filename = unquote(filename)
            filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
            return filename or "downl_" + hex(time.time_ns())[2:]
        url: String = exec_ctx.symbol_table.get("url")
        timeout: Number = exec_ctx.symbol_table.get("timeout")
        if not isinstance(url, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'downl' must be a string",
                    exec_ctx,
                )
            )
        try:
            req = urllib.request.Request(url.value, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=timeout.value) as response:
                cd = response.headers.get('Content-Disposition')
                if cd:
                    fname = re.findall('filename="(.+)"', cd)
                    name = sanitize_filename(fname[0]) if fname else url.value.split("/")[-1]
                else:
                    name = url.value.split("/")[-1]

                name = sanitize_filename(name)
                if not name:
                    name = "downl_" + hex(time.time_ns())[2:]

                with open(name, 'wb') as out_file:
                    out_file.write(response.read())
            return RTResult().success(File(name, path=os.path.abspath(name)))
        except urllib.error.HTTPError as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"HTTP Error {e.code}: Failed to download {url}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to download {url}: {str(e)}",
                    exec_ctx,
                )
            )

    execute_downl_fp.arg_names = ["url", "timeout"]


    def execute_get_local_ip_fp(self, exec_ctx):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return RTResult().success(String(ip))
        except:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Failed to retrieve local IP address",
                    exec_ctx,
                )
            )

    execute_get_local_ip_fp.arg_names = []

    def execute_get_hostname_fp(self, exec_ctx):
        try:
            return RTResult.success(String(socket.gethostname()))
        except:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Failed to retrieve hostname",
                    exec_ctx,
                )
            )

    execute_get_hostname_fp.arg_names = []

    def execute_md5_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'md5' must be a string",
                    exec_ctx,
                )
            )
        return hashlib.md5(text.encode()).hexdigest()

    execute_md5_fp.arg_names = ["text"]

    def execute_sha1_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'sha1' must be a string",
                    exec_ctx,
                )
            )
        return hashlib.sha1(text.encode()).hexdigest()

    execute_sha1_fp.arg_names = ["text"]

    def execute_sha256_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'sha256' must be a string",
                    exec_ctx,
                )
            )
        return hashlib.sha256(text.encode()).hexdigest()

    execute_sha256_fp.arg_names = ["text"]

    def execute_sha512_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'sha512' must be a string",
                    exec_ctx,
                )
            )
        return hashlib.sha512(text.encode()).hexdigest()

    execute_sha512_fp.arg_names = ["text"]

    def execute_crc32_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'crc32' must be a string",
                    exec_ctx,
                )
            )
        return format(zlib.crc32(text.encode()) & 0xFFFFFFFF, "08x")

    execute_crc32_fp.arg_names = ["text"]

    def execute_find_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        substring = exec_ctx.symbol_table.get("substring")

        if not isinstance(text, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'find' must be a string",
                    exec_ctx,
                )
            )

        if not isinstance(substring, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'find' must be a string",
                    exec_ctx,
                )
            )

        index = text.value.find(substring.value)
        if index == -1:
            return RTResult().success(None_.none)
        return RTResult().success(Number(index))

    execute_find_fp.arg_names = ["text", "substring"]

    def execute_catch(self, exec_ctx):
        func = exec_ctx.symbol_table.get("func")
        args = exec_ctx.symbol_table.get("args")
        if not isinstance(func, BaseFunction):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'catch' must be a function",
                    exec_ctx,
                )
            )
        if not isinstance(args, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'catch' must be a list",
                    exec_ctx,
                )
            )
        try:
            res = func.execute(args.elements)
            if res.error and isinstance(res.error, (RTError, FError, MError, TError)):
                err_str = str(res.error)
                err_line = err_str.strip().split('\n')[-1]
                return RTResult().success(List([None_.none, String(err_line)]))
            elif res.error:
                return RTResult().failure(res.error)
            else:
                return RTResult().success(List([res.value, None_.none]))
        except (RTError, FError, MError, TError) as err:
            err_str = str(err)
            err_line = err_str.strip().split('\n')[-1]
            return RTResult().success(List([None_.none, String(err_line)]))
        except Exception as err:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Unexpected error in 'catch': {err}",
                    exec_ctx,
                )
            )

    execute_catch.arg_names = ["func", "args"]

    def execute_finally(self, exec_ctx):
        func = exec_ctx.symbol_table.get("func")
        args = exec_ctx.symbol_table.get("args")
        final_func = exec_ctx.symbol_table.get("final_func")
        final_args = exec_ctx.symbol_table.get("final_args")
        if not isinstance(func, BaseFunction):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'finally' must be a function",
                    exec_ctx,
                )
            )
        if not isinstance(args, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'finally' must be a list",
                    exec_ctx,
                )
            )
        if not isinstance(final_func, BaseFunction):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'finally' must be a function",
                    exec_ctx,
                )
            )
        if not isinstance(final_args, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Fourth argument of 'finally' must be a list",
                    exec_ctx,
                )
            )
        try:
            res = func.execute(args.elements)
            try:
                final_func.execute(final_args.elements)
            except Exception:
                pass
            if res.error and isinstance(res.error, (RTError, FError, MError, TError)):
                err_str = str(res.error)
                err_line = err_str.strip().split('\n')[-1]
                return RTResult().success(List([None_.none, String(err_line)]))
            elif res.error:
                return RTResult().failure(res.error)
            else:
                return RTResult().success(List([res.value, None_.none]))
        except (RTError, FError, MError, TError) as err:
            try:
                final_func.execute(final_args.elements)
            except Exception:
                pass
            err_str = str(err)
            err_line = err_str.strip().split('\n')[-1]
            return RTResult().success(List([None_.none, String(err_line)]))
        except Exception as err:
            try:
                final_func.execute(final_args.elements)
            except Exception:
                pass
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Unexpected error in 'finally': {err}",
                    exec_ctx,
                )
            )

    execute_finally.arg_names = ["func", "args", "final_func", "final_args"]
    def execute_is_file_fp(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        if not isinstance(path, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'is_file' must be a string",
                    exec_ctx,
                )
            )
        return RTResult().success(
            Number.true if os.path.isfile(path.value) else Number.false
        )
    execute_is_file_fp.arg_names = ["path"]
    def execute_set_reusable(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        reusable = exec_ctx.symbol_table.get("reusable")
        if not isinstance(value, Number) and not isinstance(value, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'set_reusable' must be a list or a number",
                    exec_ctx,
                )
            )
        if not isinstance(reusable, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'set_reusable' must be a number",
                    exec_ctx,
                )
            )
        if reusable.value == 0:
            if isinstance(value, List):
                return RTResult().success(List(value.elements, reusable=False))
            elif isinstance(value, Number):
                return RTResult().success(Number(value.value, reusable=False))
        elif reusable.value == 1:
            if isinstance(value, List):
                return RTResult().success(List(value.elements, reusable=True))
            elif isinstance(value, Number):
                return RTResult().success(Number(value.value, reusable=True))
        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'set_reusable' must be a boolean",
                    exec_ctx,
                )
            )
    execute_set_reusable.arg_names = ["value", "reusable"]
    def execute_sqrt_fp(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        return RTResult().success(Number(math.sqrt(a.value)))
    execute_sqrt_fp.arg_names = ["a"]

    def execute_abs_fp(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        return RTResult().success(Number(abs(a.value)))
    execute_abs_fp.arg_names = ["a"]

    def execute_sin_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.sin(x.value)))
    execute_sin_fp.arg_names = ["x"]

    def execute_cos_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.cos(x.value)))
    execute_cos_fp.arg_names = ["x"]

    def execute_tan_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.tan(x.value)))
    execute_tan_fp.arg_names = ["x"]
    def execute_fact_fp(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        return RTResult().success(Number(math.factorial(n.value)))
    execute_fact_fp.arg_names = ["n"]
    def execute_gcd_fp(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        b = exec_ctx.symbol_table.get("b")
        return RTResult().success(Number(math.gcd(a.value, b.value)))
    execute_gcd_fp.arg_names = ["a", "b"]
    def execute_lcm_fp(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        b = exec_ctx.symbol_table.get("b")
        return RTResult().success(Number(math.lcm(a.value, b.value)))
    execute_fact_fp.arg_names = ["a", "b"]
    def execute_fib_fp(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        if n.value == 0:
            return RTResult().success(Number(0))
        a, b = 0, 1
        for _ in range(n.value + 1):
            a, b = b, a + b # this is the most Pythonic bullshit I've ever seen 🐍
        return RTResult().success(Number(b))
    execute_fib_fp.arg_names = ["n"]

    def execute_is_prime_fp(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        n = n.value
        if n < 2:
            return RTResult().success(Number.false)
        if n == 2 or n == 3:
            return RTResult().success(Number.true)
        if n % 2 == 0 or n % 3 == 0:
            return RTResult().success(Number.false)
        i = 5
        while i * i <= n:
            if n % i == 0 or n % (i + 2) == 0:
                return RTResult().success(Number.false)
            i += 6
        return RTResult().success(Number.true)

    def execute_deg2rad_fp(self, exec_ctx):
        d = exec_ctx.symbol_table.get("d")
        return RTResult().success(Number(math.radians(d.value)))
    execute_deg2rad_fp.arg_names = ["d"]
    def execute_rad2deg_fp(self, exec_ctx):
        r = exec_ctx.symbol_table.get("r")
        return RTResult().success(Number(math.degrees(r.value)))
    execute_rad2deg_fp.arg_names = ["r"]
    def execute_exp_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.exp(x.value)))
    execute_exp_fp.arg_names = ["x"]
    def execute_log_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.log(x.value)))
    execute_log_fp.arg_names = ["x"]
    def execute_sinh_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.sinh(x.value)))
    execute_sinh_fp.arg_names = ["x"]
    def execute_cosh_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.cosh(x.value)))
    execute_cosh_fp.arg_names = ["x"]
    def execute_tanh_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.tanh(x.value)))
    execute_tanh_fp.arg_names = ["x"]
    def execute_round_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(round(x.value)))
    execute_round_fp.arg_names = ["x"]
for method_name in [m for m in dir(BuiltInFunction) if m.startswith("execute_")]:
    func_name = method_name[8:]
    method = getattr(BuiltInFunction, method_name)
    if hasattr(method, "arg_names"):
        setattr(BuiltInFunction, func_name, BuiltInFunction(func_name))
        BUILTIN_FUNCTIONS.append(func_name)


class ParseResult:

    def __init__(self):
        self.error = None
        self.node = None
        self.last_registered_advance_count = 0
        self.advance_count = 0
        self.to_reverse_count = 0

    def register_advancement(self):
        self.last_registered_advance_count = 1
        self.advance_count += 1

    def register(self, res):
        self.last_registered_advance_count = res.advance_count
        self.advance_count += res.advance_count
        if res.error:
            self.error = res.error
        return res.node

    def try_register(self, res):
        if res.error:
            self.to_reverse_count = res.advance_count
            return None
        return self.register(res)

    def success(self, node):
        self.node = node
        return self

    def failure(self, error):
        if not self.error or self.last_registered_advance_count == 0:
            self.error = error
        return self


class Parser:
    __slots__ = ("tokens", "tok_idx", "current_tok")

    def __init__(self, tokens):
        self.tokens = tokens
        self.tok_idx = -1
        self.advance()

    def advance(self):
        self.tok_idx += 1
        self.update_current_tok()
        return self.current_tok

    def reverse(self, amount=1):
        self.tok_idx -= amount
        self.update_current_tok()
        return self.current_tok

    def update_current_tok(self):
        if self.tok_idx >= 0 and self.tok_idx < len(self.tokens):
            self.current_tok: Token = self.tokens[self.tok_idx]

    def parse(self):
        res = self.statements()
        if not res.error and self.current_tok.type != TT_EOF:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Token cannot appear after previous tokens",
                )
            )
        return res

    def statements(self):
        res = ParseResult()
        statements = []
        pos_start = self.current_tok.pos_start.copy()

        while self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

        statement = res.register(self.statement())
        if res.error:
            return res
        statements.append(statement)

        more_statements = True

        while True:
            newline_count = 0
            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()
                newline_count += 1
            if newline_count == 0:
                more_statements = False

            if not more_statements:
                break
            statement = res.try_register(self.statement())
            if not statement:
                self.reverse(res.to_reverse_count)
                more_statements = False
                continue
            statements.append(statement)

        return res.success(
            ListNode(statements, pos_start, self.current_tok.pos_end.copy())
        )

    def statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.matches(TT_KEYWORD, "return"):
            res.register_advancement()
            self.advance()

            expr = res.try_register(self.expr())
            if not expr:
                self.reverse(res.to_reverse_count)
            return res.success(
                ReturnNode(expr, pos_start, self.current_tok.pos_start.copy())
            )

        if self.current_tok.matches(TT_KEYWORD, "continue"):
            res.register_advancement()
            self.advance()
            return res.success(
                ContinueNode(pos_start, self.current_tok.pos_start.copy())
            )

        if self.current_tok.matches(TT_KEYWORD, "break"):
            res.register_advancement()
            self.advance()
            return res.success(BreakNode(pos_start, self.current_tok.pos_start.copy()))

        expr = res.register(self.expr())
        if res.error:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'return', 'continue', 'break', 'let', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[' or 'not'",
                )
            )
        return res.success(expr)

    def peek_tok(self) -> Token:
        if self.tok_idx + 1 >= len(self.tokens):
            return None
        return self.tokens[self.tok_idx + 1]

    def peek_tok_back(self) -> Token:
        if self.tok_idx - 1 < 0:
            return None
        return self.tokens[self.tok_idx - 1]

    def expr(self):
        res = ParseResult()

        if self.current_tok.matches(TT_KEYWORD, "let"):
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected identifier",
                    )
                )

            var_name = self.current_tok
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_EQ:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected '='",
                    )
                )

            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error:
                return res
            return res.success(VarAssignNode(var_name, expr))

        if self.current_tok.matches(TT_KEYWORD, "load"):
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_STRING:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected string",
                    )
                )

            module = self.current_tok
            v2 = module.value
            module.value = module.value.replace(".", os.sep)
            if module.value.endswith(os.sep):
                module.value = module.value[:-1]
            if not module.value.endswith(".zer"):
                module.value += ".zer"
            if os.path.basename(os.path.dirname(module.value)) != "libs":
                return res.failure(
                    InvalidSyntaxError(
                        module.pos_start,
                        module.pos_end,
                        f"Expected module to be in 'libs' directory, got '{v2}'",
                    )
                )
            res.register_advancement()
            self.advance()
            return res.success(LoadNode(module))

        node = res.register(
            self.bin_op(self.comp_expr, ((TT_KEYWORD, "and"), (TT_KEYWORD, "or")))
        )

        if res.error:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'let', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[' or 'not'",
                )
            )

        return res.success(node)

    def comp_expr(self):
        res = ParseResult()

        if self.current_tok.matches(TT_KEYWORD, "not"):
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()

            node = res.register(self.comp_expr())
            if res.error:
                return res
            return res.success(UnaryOpNode(op_tok, node))

        node = res.register(
            self.bin_op(self.arith_expr, (TT_EE, TT_NE, TT_LT, TT_GT, TT_LTE, TT_GTE))
        )

        if res.error:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected int, float, identifier, '+', '-', '(', '[', 'if', 'for', 'while', 'defun' or 'not'",
                )
            )

        return res.success(node)

    def arith_expr(self):
        return self.bin_op(self.term, (TT_PLUS, TT_MINUS))

    def term(self):
        return self.bin_op(self.factor, (TT_MUL, TT_DIV, TT_FLOORDIV, TT_MOD))

    def factor(self):
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TT_PLUS, TT_MINUS):
            res.register_advancement()
            self.advance()
            factor = res.register(self.factor())
            if res.error:
                return res
            return res.success(UnaryOpNode(tok, factor))

       

        return self.power()

    def power(self):
        return self.bin_op(self.call, (TT_POW,), self.factor)

    def call(self):
        res = ParseResult()
        atom = res.register(self.atom())
        if res.error:
            return res

        if self.current_tok.type == TT_LPAREN:
            res.register_advancement()
            self.advance()
            arg_nodes = []

            if self.current_tok.type == TT_RPAREN:
                res.register_advancement()
                self.advance()
            else:
                arg_nodes.append(res.register(self.expr()))
                if res.error:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected ')', 'let', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[' or 'not'",
                        )
                    )

                while self.current_tok.type == TT_COMMA:
                    res.register_advancement()
                    self.advance()

                    arg_nodes.append(res.register(self.expr()))
                    if res.error:
                        return res

                if self.current_tok.type != TT_RPAREN:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            f"Expected ',' or ')'",
                        )
                    )

                res.register_advancement()
                self.advance()
            return res.success(CallNode(atom, arg_nodes))
        return res.success(atom)

    def atom(self):
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TT_INT, TT_FLOAT):
            res.register_advancement()
            self.advance()
            return res.success(NumberNode(tok))

        elif tok.type == TT_STRING:
            res.register_advancement()
            self.advance()
            return res.success(StringNode(tok))

        elif tok.type == TT_IDENTIFIER:
            res.register_advancement()
            self.advance()
            return res.success(VarAccessNode(tok))

        elif tok.type == TT_LPAREN:
            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error:
                return res
            if self.current_tok.type == TT_RPAREN:
                res.register_advancement()
                self.advance()
                return res.success(expr)
            else:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ')'",
                    )
                )

        elif tok.type == TT_LSQUARE:
            list_expr = res.register(self.list_expr())
            if res.error:
                return res
            return res.success(list_expr)

        elif tok.matches(TT_KEYWORD, "if"):
            if_expr = res.register(self.if_expr())
            if res.error:
                return res
            return res.success(if_expr)

        elif tok.matches(TT_KEYWORD, "for"):
            for_expr = res.register(self.for_expr())
            if res.error:
                return res
            return res.success(for_expr)

        elif tok.matches(TT_KEYWORD, "while"):
            while_expr = res.register(self.while_expr())
            if res.error:
                return res
            return res.success(while_expr)

        elif tok.matches(TT_KEYWORD, "defun"):
            func_def = res.register(self.func_def())
            if res.error:
                return res
            return res.success(func_def)

        return res.failure(
            InvalidSyntaxError(
                tok.pos_start,
                tok.pos_end,
                "Expected int, float, identifier, '+', '-', '(', '[', 'if', 'for', 'while', 'defun'",
            )
        )

    def list_expr(self):
        res = ParseResult()
        element_nodes = []
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_LSQUARE:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected '['",
                )
            )

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_RSQUARE:
            res.register_advancement()
            self.advance()
        else:
            element_nodes.append(res.register(self.expr()))
            if res.error:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ']', 'let', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[' or 'not'",
                    )
                )

            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                element_nodes.append(res.register(self.expr()))
                if res.error:
                    return res

            if self.current_tok.type != TT_RSQUARE:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        f"Expected ',' or ']'",
                    )
                )

            res.register_advancement()
            self.advance()

        return res.success(
            ListNode(element_nodes, pos_start, self.current_tok.pos_end.copy())
        )

    def if_expr(self):
        res = ParseResult()

        all_cases = res.register(self.if_expr_cases("if"))
        if res.error:
            return res
        cases, else_case = all_cases
        return res.success(IfNode(cases, else_case))

    def if_expr_b(self):
        return self.if_expr_cases("elif")

    def if_expr_c(self):
        res = ParseResult()
        else_case = None

        if self.current_tok.matches(TT_KEYWORD, "else"):
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

                statements = res.register(self.statements())
                if res.error:
                    return res
                else_case = (statements, True)

                if self.current_tok.matches(TT_KEYWORD, "done"):
                    res.register_advancement()
                    self.advance()
                else:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected 'done'",
                        )
                    )
            else:
                expr = res.register(self.statement())
                if res.error:
                    return res
                else_case = (expr, False)

        return res.success(else_case)

    def if_expr_b_or_c(self):
        res = ParseResult()
        cases, else_case = [], None

        if self.current_tok.matches(TT_KEYWORD, "elif"):
            all_cases = res.register(self.if_expr_b())
            if res.error:
                return res
            cases, else_case = all_cases
        else:
            else_case = res.register(self.if_expr_c())
            if res.error:
                return res

        return res.success((cases, else_case))

    def if_expr_cases(self, case_keyword):
        res = ParseResult()
        cases = []
        else_case = None

        if self.current_tok.value == "let":
            res.register_advancement()
            self.advance()

        if not self.current_tok.matches(TT_KEYWORD, case_keyword):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected '{case_keyword}'",
                )
            )

        res.register_advancement()
        self.advance()

        condition = res.register(self.expr())
        if res.error:
            return res

        if not self.current_tok.matches(TT_KEYWORD, "do"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'do'",
                )
            )

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            statements = res.register(self.statements())
            if res.error:
                return res
            cases.append((condition, statements, True))

            if self.current_tok.matches(TT_KEYWORD, "done"):
                res.register_advancement()
                self.advance()
            else:
                all_cases = res.register(self.if_expr_b_or_c())
                if res.error:
                    return res
                new_cases, else_case = all_cases
                cases.extend(new_cases)
        else:
            expr = res.register(self.statement())
            if res.error:
                return res
            cases.append((condition, expr, False))

            all_cases = res.register(self.if_expr_b_or_c())
            if res.error:
                return res
            new_cases, else_case = all_cases
            cases.extend(new_cases)

        return res.success((cases, else_case))

    def for_expr(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "for"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'for'",
                )
            )

        res.register_advancement()
        self.advance()
        if self.current_tok.value == "let":
            res.register_advancement()
            self.advance()
        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected identifier",
                )
            )

        var_name = self.current_tok
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_EQ:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected '='",
                )
            )

        res.register_advancement()
        self.advance()

        start_value = res.register(self.expr())
        if res.error:
            return res

        if not self.current_tok.matches(TT_KEYWORD, "to"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'to'",
                )
            )

        res.register_advancement()
        self.advance()

        end_value = res.register(self.expr())
        if res.error:
            return res

        if self.current_tok.matches(TT_KEYWORD, "step"):
            res.register_advancement()
            self.advance()

            step_value = res.register(self.expr())
            if res.error:
                return res
        else:
            step_value = None

        if not self.current_tok.matches(TT_KEYWORD, "do"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'do'",
                )
            )

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            body = res.register(self.statements())
            if res.error:
                return res

           

            if not self.current_tok.matches(TT_KEYWORD, "done"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        f"Expected 'done'",
                    )
                )

            res.register_advancement()
            self.advance()

            return res.success(
                ForNode(var_name, start_value, end_value, step_value, body, True)
            )

        body = res.register(self.statement())
        if res.error:
            return res

        return res.success(
            ForNode(var_name, start_value, end_value, step_value, body, False)
        )

    def while_expr(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "while"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'while'",
                )
            )

        res.register_advancement()
        self.advance()

        condition = res.register(self.expr())
        if res.error:
            return res

        if not self.current_tok.matches(TT_KEYWORD, "do"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'do'",
                )
            )

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            body = res.register(self.statements())
            if res.error:
                return res

            if not self.current_tok.matches(TT_KEYWORD, "done"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        f"Expected 'done'",
                    )
                )

            res.register_advancement()
            self.advance()

            return res.success(WhileNode(condition, body, True))

        body = res.register(self.statement())
        if res.error:
            return res

        return res.success(WhileNode(condition, body, False))

    def func_def(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "defun"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'defun'",
                )
            )

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_IDENTIFIER:
            var_name_tok = self.current_tok
            res.register_advancement()
            self.advance()
            if self.current_tok.type != TT_LPAREN:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        f"Expected '('",
                    )
                )
        else:
            var_name_tok = None
            if self.current_tok.type != TT_LPAREN:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        f"Expected identifier or '('",
                    )
                )

        res.register_advancement()
        self.advance()
        arg_name_toks = []

        if self.current_tok.type == TT_IDENTIFIER:
            arg_name_toks.append(self.current_tok)
            res.register_advancement()
            self.advance()

            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            f"Expected identifier",
                        )
                    )

                arg_name_toks.append(self.current_tok)
                res.register_advancement()
                self.advance()

            if self.current_tok.type != TT_RPAREN:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        f"Expected ',' or ')'",
                    )
                )
        else:
            if self.current_tok.type != TT_RPAREN:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        f"Expected identifier or ')'",
                    )
                )

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_ARROW:
            res.register_advancement()
            self.advance()

            body = res.register(self.expr())
            if res.error:
                return res

            return res.success(FuncDefNode(var_name_tok, arg_name_toks, body, True))

        if self.current_tok.type != TT_NEWLINE:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected '->' or NEWLINE",
                )
            )

        res.register_advancement()
        self.advance()

        body = res.register(self.statements())
        if res.error:
            return res

        if not self.current_tok.matches(TT_KEYWORD, "done"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'done'",
                )
            )

        res.register_advancement()
        self.advance()

        return res.success(FuncDefNode(var_name_tok, arg_name_toks, body, False))

    def bin_op(self, func_a, ops, func_b=None):
        if func_b == None:
            func_b = func_a

        res = ParseResult()
        left = res.register(func_a())
        if res.error:
            return res

        while (
            self.current_tok.type in ops
            or (self.current_tok.type, self.current_tok.value) in ops
        ):
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()
            right = res.register(func_b())
            if res.error:
                return res
            left = BinOpNode(left, op_tok, right)

        return res.success(left)


class Interpreter:

    def visit(self, node, context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)

    def no_visit_method(self, node, context):
        raise Exception(f"No visit_{type(node).__name__} method defined")

    def visit_NumberNode(self, node, context: Context):
        return RTResult().success(
            Number(node.tok.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_StringNode(self, node, context: Context):
        return RTResult().success(
            String(node.tok.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_ListNode(self, node, context: Context):
        res = RTResult()
        elements = []

        for element_node in node.element_nodes:
            elements.append(res.register(self.visit(element_node, context)))
            if res.should_return():
                return res

        return res.success(
            List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_VarAccessNode(self, node, context: Context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = context.symbol_table.get(var_name)

        if value is None:
            value = context.private_symbol_table.get(var_name)
            if value is None:
                return res.failure(
                    RTError(
                        node.pos_start,
                        node.pos_end,
                        f"'{var_name}' is not defined",
                        context,
                    )
                )

        value = value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
        return res.success(value)

    def visit_VarAssignNode(self, node, context: Context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = res.register(self.visit(node.value_node, context))
        if res.should_return():
            return res

        context.symbol_table.set(var_name, value)
        context.private_symbol_table.set(var_name, value)
        return res.success(value)

    def visit_BinOpNode(self, node, context):
        res = RTResult()
        left = res.register(self.visit(node.left_node, context))
        if res.should_return():
            return res
        right = res.register(self.visit(node.right_node, context))
        if res.should_return():
            return res

        if node.op_tok.type == TT_PLUS:
            result, error = left.added_to(right)
        elif node.op_tok.type == TT_MINUS:
            result, error = left.subbed_by(right)
        elif node.op_tok.type == TT_MUL:
            result, error = left.multed_by(right)
        elif node.op_tok.type == TT_DIV:
            result, error = left.dived_by(right)
        elif node.op_tok.type == TT_POW:
            result, error = left.powed_by(right)
        elif node.op_tok.type == TT_MOD:
            result, error = left.moduled_by(right)
        elif node.op_tok.type == TT_EE:
            result, error = left.get_comparison_eq(right)
        elif node.op_tok.type == TT_NE:
            result, error = left.get_comparison_ne(right)
        elif node.op_tok.type == TT_LT:
            result, error = left.get_comparison_lt(right)
        elif node.op_tok.type == TT_GT:
            result, error = left.get_comparison_gt(right)
        elif node.op_tok.type == TT_LTE:
            result, error = left.get_comparison_lte(right)
        elif node.op_tok.type == TT_GTE:
            result, error = left.get_comparison_gte(right)
        elif node.op_tok.matches(TT_KEYWORD, "and"):
            result, error = left.anded_by(right)
        elif node.op_tok.matches(TT_KEYWORD, "or"):
            result, error = left.ored_by(right)
        elif node.op_tok.type == TT_FLOORDIV:
            result, error = left.floordived_by(right)

        if error:
            return res.failure(error)
        else:
            return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_UnaryOpNode(self, node, context):
        res = RTResult()
        number = res.register(self.visit(node.node, context))
        if res.should_return():
            return res

        # Guard: prevent unary operations on none

        if isinstance(number, Number) and number.value is None:
            return res.failure(
                TError(
                    node.pos_start,
                    node.pos_end,
                    "Cannot perform arithmetic or logical operation on 'none'",
                    context,
                )
            )

        error = None

        if node.op_tok.type == TT_MINUS:
            number, error = number.multed_by(Number(-1))
        elif node.op_tok.matches(TT_KEYWORD, "not"):
            number, error = number.notted()

        if error:
            return res.failure(error)
        else:
            return res.success(number.set_pos(node.pos_start, node.pos_end))

    def visit_IfNode(self, node, context):
        res = RTResult()

        for condition, expr, should_return_none in node.cases:
            condition_value = res.register(self.visit(condition, context))
            if res.should_return():
                return res

            if condition_value.is_true():
                expr_value = res.register(self.visit(expr, context))
                if res.should_return():
                    return res
                return res.success(None_.none if should_return_none else expr_value)

        if node.else_case:
            expr, should_return_none = node.else_case
            expr_value = res.register(self.visit(expr, context))
            if res.should_return():
                return res
            return res.success(None_.none if should_return_none else expr_value)

        return res.success(None_.none)

    def visit_ForNode(self, node, context):
        res = RTResult()
        start_value = res.register(self.visit(node.start_value_node, context))
        if res.should_return():
            return res

        end_value = res.register(self.visit(node.end_value_node, context))
        if res.should_return():
            return res

        if node.step_value_node:
            step_value = res.register(self.visit(node.step_value_node, context))
            if res.should_return():
                return res
        else:
            step_value = Number(1)

        i = start_value.value
        end = end_value.value
        step = step_value.value
        should_return_none = node.should_return_none

        # Tối ưu: chỉ tạo list nếu cần trả về list
        if not should_return_none:
            elements = []

        # Tối ưu điều kiện lặp
        if step >= 0:
            cond = lambda: i < end
        else:
            cond = lambda: i > end

        while cond():
            context.symbol_table.set(node.var_name_tok.value, Number(i))
            i += step

            value = res.register(self.visit(node.body_node, context))
            if (
                res.should_return()
                and not res.loop_should_continue
                and not res.loop_should_break
            ):
                return res

            if res.loop_should_continue:
                continue

            if res.loop_should_break:
                break

            if not should_return_none:
                elements.append(value)

        if should_return_none:
            return res.success(None_.none)
        else:
            return res.success(
                List(elements)
                .set_context(context)
                .set_pos(node.pos_start, node.pos_end)
            )

    def visit_WhileNode(self, node, context):
        res = RTResult()
        should_return_none = node.should_return_none
        # Tối ưu: chỉ tạo list nếu cần trả về list
        if not should_return_none:
            elements = []

        while True:
            condition = res.register(self.visit(node.condition_node, context))
            if res.should_return():
                return res

            if not condition.is_true():
                break

            value = res.register(self.visit(node.body_node, context))
            if (
                res.should_return()
                and not res.loop_should_continue
                and not res.loop_should_break
            ):
                return res

            if res.loop_should_continue:
                continue

            if res.loop_should_break:
                break

            if not should_return_none:
                elements.append(value)

        if should_return_none:
            return res.success(None_.none)
        else:
            return res.success(
                List(elements)
                .set_context(context)
                .set_pos(node.pos_start, node.pos_end)
            )

    def visit_FuncDefNode(self, node, context):
        res = RTResult()

        func_name = node.var_name_tok.value if node.var_name_tok else None
        body_node = node.body_node
        arg_names = [arg_name.value for arg_name in node.arg_name_toks]
        func_value = (
            Function(func_name, body_node, arg_names, node.should_auto_return)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

        if node.var_name_tok:
            context.symbol_table.set(func_name, func_value)

        return res.success(func_value)

    def visit_CallNode(self, node, context):
        try:
            res = RTResult()
            args = []

            value_to_call = res.register(self.visit(node.node_to_call, context))
            if res.should_return():
                return res
            value_to_call = value_to_call.copy().set_pos(node.pos_start, node.pos_end)

            for arg_node in node.arg_nodes:
                args.append(res.register(self.visit(arg_node, context)))
                if res.should_return():
                    return res

            return_value = res.register(value_to_call.execute(args))
            if res.should_return():
                return res
            return_value = (
                return_value.copy()
                .set_pos(node.pos_start, node.pos_end)
                .set_context(context)
            )

            return res.success(return_value)
        except RecursionError:
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Maximum recursion depth exceeded ({sys.getrecursionlimit()})",
                    context,
                )
            )

    def visit_ReturnNode(self, node, context):
        res = RTResult()

        if node.node_to_return:
            value = res.register(self.visit(node.node_to_return, context))
            if res.should_return():
                return res
        else:
            value = None_.none

        return res.success_return(value)

    def visit_ContinueNode(self, node, context):
        return RTResult().success_continue()

    def visit_BreakNode(self, node, context):
        return RTResult().success_break()

    def visit_LoadNode(self, node: LoadNode, context: Context):
        res = RTResult()
        path = node.file_path

        if not os.path.isfile(path):
            tmp_path = os.path.join(LIBS_PATH, node.file_path)
            if os.path.isfile(tmp_path):
                path = os.path.join(LIBS_PATH, node.file_path)
            else:
                return res.failure(
                    RTError(
                        node.pos_start,
                        node.pos_end,
                        f"No module named '{tmp_path}'",
                        context,
                    )
                )

        result, err = load_module(path, self, context)
        if err:
            if isinstance(err, Error):
                return res.failure(err)
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    err.error.details,
                    context,
                )
            )

        return res.success(result)

global_symbol_table.set("argv_fp", List(sys.argv))

global_symbol_table.set("none", None_.none)
global_symbol_table.set("false", Number.false)
global_symbol_table.set("true", Number.true)
global_symbol_table.set("list", String("<list>"))
global_symbol_table.set("str", String("<str>"))
global_symbol_table.set("int", String("<int>"))
global_symbol_table.set("float", String("<float>"))
global_symbol_table.set("func", String("<func>"))
global_symbol_table.set("os_name_fp", String(os.name))
global_symbol_table.set("PI_fp", Number(math.pi))
global_symbol_table.set("E_fp", Number(math.e))
for func in BUILTIN_FUNCTIONS:
    global_symbol_table.set(func, getattr(BuiltInFunction, func))

private_symbol_table = SymbolTable()
private_symbol_table.set("is_main", Number(0))


def run(fn, text):
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    # print("--- Tokens ---")
    # for token in tokens:
    #     print(token)
    if error:
        return None, error
    result = None
    context = None
    try:
        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return None, ast.error
        # print("--- AST ---")
        # print(ast.node)
        interpreter = Interpreter()
        context = Context("<program>")
        context.symbol_table = global_symbol_table
        context.private_symbol_table = private_symbol_table
        context.private_symbol_table.set("is_main", Number(1))
        result = interpreter.visit(ast.node, context)
        result.value = "" if str(result.value) == "none" else result.value
        return result.value, result.error
    except KeyboardInterrupt:
        print("Interrupt Error: User Terminated")
        sys.exit(2)
