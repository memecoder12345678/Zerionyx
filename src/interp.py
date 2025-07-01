import os
import sys
import time
import random
import math
from .parser import *
from .nodes import *
from .datatypes import *
from .consts import *
from .errors import TError, IOError, MError, Error, RTError
from shutil import rmtree, copy
from functools import lru_cache
from .lexer import Lexer, RTResult

from getpass import getpass
import requests
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

from colorama import init, Fore, Style

init()
ssl._create_default_https_context = ssl._create_unverified_context
BUILTIN_FUNCTIONS = []
global_symbol_table = SymbolTable()


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
            or NoneObject.none
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

    def no_visit_method(self, _, __):
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
            return RTResult().success(NoneObject.none)

        print(repr(exec_ctx.symbol_table.get("value")))
        return RTResult().success(NoneObject.none)

    execute_println.arg_names = ["value"]

    def execute_print(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        if isinstance(value, String):
            print(value.value, end="")
            return RTResult().success(NoneObject.none)

        print(repr(exec_ctx.symbol_table.get("value")), end="")
        return RTResult().success(NoneObject.none)

    execute_print.arg_names = ["value"]

    def execute_input(self, exec_ctx):
        prompt = exec_ctx.symbol_table.get("prompt")
        if not isinstance(prompt, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'input' must be a string",
                    exec_ctx,
                )
            )
        text = input(prompt.value)
        return RTResult().success(String(text))

    execute_input.arg_names = ["prompt"]

    def execute_get_password(self, exec_ctx):
        prompt = exec_ctx.symbol_table.get("prompt")
        if not isinstance(prompt, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'input' must be a string",
                    exec_ctx,
                )
            )
        pass_ = getpass(prompt.value)
        return RTResult().success(String(pass_))

    execute_get_password.arg_names = ["prompt"]

    def execute_clear(self, _):
        os.system("cls" if os.name == "nt" else "clear")
        return RTResult().success(NoneObject.none)

    execute_clear.arg_names = []

    def execute_type(self, exec_ctx):
        data = exec_ctx.symbol_table.get("value")
        return RTResult().success(String(data.type()))

    execute_type.arg_names = ["value"]

    def execute_is_none(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        return RTResult().success(
            Number.true if isinstance(value, NoneObject) else Number.false
        )

    execute_is_none.arg_names = ["value"]

    def execute_is_num(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), Number)
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_num.arg_names = ["value"]

    def execute_is_bool(self, exec_ctx):
        is_bool = isinstance(exec_ctx.symbol_table.get("value"), Bool)
        return RTResult().success(Number.true if is_bool else Number.false)

    execute_is_bool.arg_names = ["value"]

    def execute_is_str(self, exec_ctx):
        is_str = isinstance(exec_ctx.symbol_table.get("value"), String)
        return RTResult().success(Number.true if is_str else Number.false)

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
        if not isinstance(reverse, Bool):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'sort' must be a boolean",
                    exec_ctx,
                )
            )

        if int(reverse.value) == 1:
            lst.elements.sort(key=lambda x: x.value, reverse=True)
        elif int(reverse.value) == 0:
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
        return RTResult().success(NoneObject.none)

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
        return RTResult().success(NoneObject.none)

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
        return RTResult().success(NoneObject.none)

    execute_sleep_fp.arg_names = ["seconds"]

    def execute_exit_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        sys.exit(int(value.value))

    execute_exit_fp.arg_names = ["value"]

    def execute_slice(self, exec_ctx):
        l = exec_ctx.symbol_table.get("l")
        start = exec_ctx.symbol_table.get("start")
        end = exec_ctx.symbol_table.get("end")
        step = exec_ctx.symbol_table.get("step")
        if not isinstance(l, String | List | HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'slice' must be a string or list",
                    exec_ctx,
                )
            )

        if not isinstance(start, Number) and not isinstance(start, NoneObject):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'slice' must be a number or none",
                    exec_ctx,
                )
            )

        if not isinstance(end, Number) and not isinstance(end, NoneObject):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'slice' must be a number or none",
                    exec_ctx,
                )
            )
        if not isinstance(step, Number) and not isinstance(step, NoneObject):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Fourth argument of 'slice' must be a number or none",
                    exec_ctx,
                )
            )
        a = int(start.value) if not isinstance(start, NoneObject) else None
        b = int(end.value) if not isinstance(end, NoneObject) else None
        s = int(step.value) if not isinstance(step, NoneObject) else None

        if isinstance(l, String):
            sliced_l = l.value[a:b:s]
            return RTResult().success(String(sliced_l))
        elif isinstance(l, HashMap):
            sliced_l = dict(l.values.items()[a:b:s])
            return RTResult().success(HashMap(sliced_l))
        sliced_l = l.elements[a:b:s]
        return RTResult().success(List(sliced_l))

    execute_slice.arg_names = ["l", "start", "end", "step"]

    def execute_open_fp(self, exec_ctx):
        file_path = exec_ctx.symbol_table.get("file_path")

        try:
            file_name = os.path.splitext(file_path.value)[0]
            return RTResult().success(File(file_name, file_path.value))
        except Exception as e:
            return RTResult().failure(
                IOError(
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
                IOError(
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
                IOError(
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
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if file exists '{file_path}': " + str(e),
                    exec_ctx,
                )
            )

    execute_exists_fp.arg_names = ["file_path"]

    def execute_time_fp(self, _):
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
            return RTResult().success(NoneObject.none)
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

    def execute_get_cdir_fp(self, exec_ctx):
        try:
            return RTResult().success(String(os.getcwd()))
        except Exception as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get current directory: " + str(e),
                    exec_ctx,
                )
            )

    execute_get_cdir_fp.arg_names = []

    def execute_set_cdir_fp(self, exec_ctx):
        name = exec_ctx.symbol_table.get("name")

        if not isinstance(name, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'set_cdir' must be a string",
                    exec_ctx,
                )
            )

        if not os.path.exists(name.value):
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Directory '{name.value}' does not exist",
                    exec_ctx,
                )
            )

        try:
            os.chdir(name.value)
            return RTResult().success(NoneObject.none)
        except Exception as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to set current directory to '{name.value}': " + str(e),
                    exec_ctx,
                )
            )

    execute_set_cdir_fp.arg_names = ["name"]

    def execute_rand_fp(self, _):
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

        if not isinstance(supress_error, Bool):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'to_int' must be a boolean",
                    exec_ctx,
                )
            )
        if int(supress_error.value) == 1:
            supress_error_ = True
        elif int(supress_error.value) == 0:
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

        if not isinstance(supress_error, Bool):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'to_float' must be a boolean",
                    exec_ctx,
                )
            )

        if int(supress_error.value) == 1:
            supress_error_ = True
        elif int(supress_error.value) == 0:
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
                String(sep.value.join([str(element) for element in iterables.elements]))
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

        return RTResult().success(NoneObject.none)

    execute_system_fp.arg_names = ["command"]

    def execute_osystem_fp(self, exec_ctx):
        cmd = exec_ctx.symbol_table.get("cmd")
        result = subprocess.run(
            cmd.value,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return RTResult().success(
            List(
                [
                    String(result.stdout),
                    String(result.stderr),
                    Number(result.returncode),
                ]
            )
        )

    execute_osystem_fp.arg_names = ["command"]

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
                    "Second argument of 'panic' must be a string ('RT': 'Runtime Error', 'M': 'Math Error', 'IO': 'IO Error' or 'T': 'Type Error')",
                    exec_ctx,
                )
            )

        err_type_value = err_type.value.upper().strip()

        if err_type_value == "RT":
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, msg, exec_ctx)
            )
        elif err_type_value == "M":
            return RTResult().failure(
                MError(self.pos_start, self.pos_end, msg, exec_ctx)
            )
        elif err_type_value == "IO":
            return RTResult().failure(
                IOError(self.pos_start, self.pos_end, msg, exec_ctx)
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
                    "Second argument of 'panic' must be a string ('RT': 'Runtime Error', 'M': 'Math Error', 'IO': 'IO Error' or 'T': 'Type Error')",
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
                IOError(
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
                IOError(
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
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Directory '{value.value}' already exists",
                    exec_ctx,
                )
            )
        os.mkdir(value.value)
        return RTResult().success(NoneObject.none)

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
                IOError(
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
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to remove file: " + str(e),
                    exec_ctx,
                )
            )
        return RTResult().success(NoneObject.none)

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
                IOError(
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
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to rename file: {e}",
                    exec_ctx,
                )
            )
        return RTResult().success(NoneObject.none)

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
                IOError(
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
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to remove directory: {e}",
                    exec_ctx,
                )
            )
        return RTResult().success(NoneObject.none)

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
                IOError(
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
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to copy file: {e}",
                    exec_ctx,
                )
            )
        return RTResult().success(NoneObject.none)

    execute_copy_fp.arg_names = ["src_path", "dst_path"]

    def execute_keyboard_write_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")

        if not isinstance(text, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'write' must be a string",
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
                    "keyboard module not available\nTip: Install with: pip install keyboard",
                    exec_ctx,
                )
            )

        return RTResult().success(NoneObject.none)

    execute_keyboard_write_fp.arg_names = ["text"]

    def execute_keyboard_press_fp(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")

        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'press' must be a string",
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
                    "keyboard module not available\nTip: Install with: pip install keyboard",
                    exec_ctx,
                )
            )

        return RTResult().success(NoneObject.none)

    execute_keyboard_press_fp.arg_names = ["key"]

    def execute_keyboard_release_fp(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")

        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'release' must be a string",
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
                    "keyboard module not available\nTip: Install with: pip install keyboard",
                    exec_ctx,
                )
            )

        return RTResult().success(NoneObject.none)

    execute_keyboard_release_fp.arg_names = ["key"]

    def execute_keyboard_wait_fp(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")

        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'wait' must be a string",
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
                    "keyboard module not available\nTip: Install with: pip install keyboard",
                    exec_ctx,
                )
            )

        return RTResult().success(NoneObject.none)

    execute_keyboard_wait_fp.arg_names = ["key"]

    def execute_keyboard_is_pressed_fp(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")

        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'is_pressed' must be a string",
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
                    "keyboard module not available\nTip: Install with: pip install keyboard",
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
                    "First argument of 'start' must be a function",
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
                    "First argument of 'sleep' must be a number",
                    exec_ctx,
                )
            )

        try:
            import time

            time.sleep(seconds.value)
            return RTResult().success(NoneObject.none)
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
                    "First argument of 'join' must be a thread",
                    exec_ctx,
                )
            )

        if not isinstance(timeout, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'join' must be a number",
                    exec_ctx,
                )
            )

        try:
            thread.join(timeout.value)
            return RTResult().success(NoneObject.none)
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
                    "First argument of 'is_alive' must be a thread",
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
                    "First argument of 'cancel' must be a thread",
                    exec_ctx,
                )
            )

        try:
            thread.cancel()
            return RTResult().success(NoneObject.none)
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
                return RTResult().success(String(res_.read().decode()))
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
                ["ping", "-n", "1", host], stderr=subprocess.DEVnone
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
            filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
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
            req = urllib.request.Request(
                url.value,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=timeout.value) as response:
                cd = response.headers.get("Content-Disposition")
                if cd:
                    fname = re.findall('filename="(.+)"', cd)
                    name = (
                        sanitize_filename(fname[0])
                        if fname
                        else url.value.split("/")[-1]
                    )
                else:
                    name = url.value.split("/")[-1]

                name = sanitize_filename(name)
                if not name:
                    name = "downl_" + hex(time.time_ns())[2:]

                with open(name, "wb") as out_file:
                    out_file.write(response.read())
            return RTResult().success(String(os.path.abspath(name)))
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
            return RTResult().success(String(socket.gethostname()))
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
        return RTResult().success(
            String(str(hashlib.md5(text.value.encode()).hexdigest()))
        )

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
        return RTResult().success(
            String(str(hashlib.sha1(text.value.encode()).hexdigest()))
        )

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
        return RTResult().success(
            String(str(hashlib.sha256(text.value.encode()).hexdigest()))
        )

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
        return RTResult().success(
            String(str(hashlib.sha512(text.value.encode()).hexdigest()))
        )

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
        return RTResult().success(
            String(str(format(zlib.crc32(text.value.encode()) & 0xFFFFFFFF, "08x")))
        )

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
            return RTResult().success(NoneObject.none)
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
            if res.error and isinstance(res.error, (RTError, IOError, MError, TError)):
                err_str = str(res.error)
                err_line = err_str.strip().split("\n")[-1]
                return RTResult().success(List([NoneObject.none, String(err_line)]))
            elif res.error:
                return RTResult().failure(res.error)
            else:
                return RTResult().success(List([res.value, NoneObject.none]))
        except (RTError, IOError, MError, TError) as err:
            err_str = str(err)
            err_line = err_str.strip().split("\n")[-1]
            return RTResult().success(List([NoneObject.none, String(err_line)]))
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
            if res.error and isinstance(res.error, (RTError, IOError, MError, TError)):
                err_str = str(res.error)
                err_line = err_str.strip().split("\n")[-1]
                return RTResult().success(List([NoneObject.none, String(err_line)]))
            elif res.error:
                return RTResult().failure(res.error)
            else:
                return RTResult().success(List([res.value, NoneObject.none]))
        except (RTError, IOError, MError, TError) as err:
            try:
                final_func.execute(final_args.elements)
            except Exception:
                pass
            err_str = str(err)
            err_line = err_str.strip().split("\n")[-1]
            return RTResult().success(List([NoneObject.none, String(err_line)]))
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
            a, b = b, a + b  # this is the most Pythonic bullshit I've ever seen 🐍
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

    def validate_pyexec_result(self, obj):
        allowed = (bool, int, float, str)
        if obj is None:
            return NoneObject.none
        elif isinstance(obj, allowed):
            if isinstance(obj, bool):
                if obj:
                    return Number.true
                else:
                    return Number.false
            elif isinstance(obj, int):
                return Number(obj)
            elif isinstance(obj, float):
                return Number(obj)
            else:
                return String(obj)
        elif isinstance(obj, list):
            items = []
            for item in obj:
                if not isinstance(
                    item, (bool, int, float, str, list, dict, tuple, type(None))
                ):
                    items.append(String(str(item)))
                else:
                    items.append(self.validate_pyexec_result(item))
            return List(items)
        elif isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                if not isinstance(k, (str, int, float, bool)):
                    key = String(str(k))
                    value = String(str(v))
                else:
                    key = self.validate_pyexec_result(k)
                    value = self.validate_pyexec_result(v)

                new_dict[key] = value

            return HashMap(new_dict)
        elif isinstance(obj, tuple):
            items = []
            for item in obj:
                if not isinstance(
                    item, (bool, int, float, str, list, dict, tuple, type(None))
                ):
                    items.append(self.validate_pyexec_result(String(str(obj))))
                else:
                    items.append(self.validate_pyexec_result(item))
            return List(items)
        else:
            return String(str(obj))

    def execute_pyexec(self, exec_ctx):
        code = exec_ctx.symbol_table.get("code")
        if not isinstance(code, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'pyexec' must be a string",
                    exec_ctx,
                )
            )
        try:
            local_env = {}
            exec(code.value, {}, local_env)
            fr = self.validate_pyexec_result(local_env)
            return RTResult().success(fr)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error executing code: {e}",
                    exec_ctx,
                )
            )

    execute_pyexec.arg_names = ["code"]

    def execute_abs_path_fp(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        if not isinstance(path, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'abs_path' must be a string",
                    exec_ctx,
                )
            )
        try:
            return RTResult().success(String(os.path.abspath(path.value)))
        except Exception as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get absolute path for '{path.value}': {str(e)}",
                    exec_ctx,
                )
            )

    execute_abs_path_fp.arg_names = ["path"]

    def execute_dir_name_fp(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        if not isinstance(path, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'dir_name' must be a string",
                    exec_ctx,
                )
            )
        try:
            return RTResult().success(String(os.path.dirname(path.value)))
        except Exception as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get directory name for '{path.value}': {str(e)}",
                    exec_ctx,
                )
            )

    execute_dir_name_fp.arg_names = ["path"]

    def execute_base_name_fp(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        if not isinstance(path, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'base_name' must be a string",
                    exec_ctx,
                )
            )
        try:
            return RTResult().success(String(os.path.basename(path.value)))
        except Exception as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get base name for '{path.value}': {str(e)}",
                    exec_ctx,
                )
            )

    execute_base_name_fp.arg_names = ["path"]

    def execute_symlink_fp(self, exec_ctx):
        src = exec_ctx.symbol_table.get("src")
        dst = exec_ctx.symbol_table.get("dst")

        if not isinstance(src, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'symlink' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(dst, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'symlink' must be a string",
                    exec_ctx,
                )
            )
        try:
            if hasattr(os, "symlink"):
                os.symlink(src.value, dst.value)
                return RTResult().success(NoneObject.none)
            else:
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        "Symbolic links are not supported on this system or require special privileges",
                        exec_ctx,
                    )
                )
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"OS error creating symlink '{src.value}' -> '{dst.value}': {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error creating symlink: {str(e)}",
                    exec_ctx,
                )
            )

    execute_symlink_fp.arg_names = ["src", "dst"]

    def execute_readlink_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'readlink' must be a string",
                    exec_ctx,
                )
            )
        try:
            if hasattr(os, "readlink"):
                target_path = os.readlink(path_arg.value)
                return RTResult().success(String(target_path))
            else:
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        "Reading symbolic links is not supported on this system",
                        exec_ctx,
                    )
                )
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"OS error reading link '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error reading link: {str(e)}",
                    exec_ctx,
                )
            )

    execute_readlink_fp.arg_names = ["path"]

    def _format_stat_result_to_list(self, stat_res, context):
        return List(
            [
                Number(stat_res.st_mode),
                Number(stat_res.st_ino),
                Number(stat_res.st_dev),
                Number(stat_res.st_nlink),
                Number(stat_res.st_uid),
                Number(stat_res.st_gid),
                Number(stat_res.st_size),
                Number(stat_res.st_atime),
                Number(stat_res.st_mtime),
                Number(stat_res.st_ctime),
            ]
        )

    def execute_stat_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'stat' must be a string",
                    exec_ctx,
                )
            )
        try:
            stat_res_obj = os.stat(path_arg.value)
            return RTResult().success(
                self._format_stat_result_to_list(stat_res_obj, exec_ctx)
            )
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"OS error getting stat for '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error getting stat: {str(e)}",
                    exec_ctx,
                )
            )

    execute_stat_fp.arg_names = ["path"]

    def execute_lstat_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'lstat' must be a string",
                    exec_ctx,
                )
            )
        try:
            stat_res_obj = None
            if hasattr(os, "lstat"):
                stat_res_obj = os.lstat(path_arg.value)
            else:
                stat_res_obj = os.stat(path_arg.value)
            return RTResult().success(
                self._format_stat_result_to_list(stat_res_obj, exec_ctx)
            )
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"OS error getting lstat for '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error getting lstat: {str(e)}",
                    exec_ctx,
                )
            )

    execute_lstat_fp.arg_names = ["path"]

    def execute_walk_fp(self, exec_ctx):
        top_path = exec_ctx.symbol_table.get("top")
        if not isinstance(top_path, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'walk' must be a string",
                    exec_ctx,
                )
            )
        try:
            walk_results_list_of_lists = []
            for root, dirs, files in os.walk(top_path.value):
                fun_root = String(root)
                fun_dirs = List([String(d) for d in dirs])
                fun_files = List([String(f) for f in files])
                walk_results_list_of_lists.append(List([fun_root, fun_dirs, fun_files]))
            return RTResult().success(List(walk_results_list_of_lists))
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error during directory walk starting at '{top_path.value}': {str(e)}",
                    exec_ctx,
                )
            )

    execute_walk_fp.arg_names = ["top"]

    def execute_chmod_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        mode_arg = exec_ctx.symbol_table.get("mode")

        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'chmod' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(mode_arg, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'chmod' must be a number",
                    exec_ctx,
                )
            )
        try:
            os.chmod(path_arg.value, int(mode_arg.value))
            return RTResult().success(NoneObject.none)
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"OS error changing mode for '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error changing mode: {str(e)}",
                    exec_ctx,
                )
            )

    execute_chmod_fp.arg_names = ["path", "mode"]

    def execute_chown_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        uid_arg = exec_ctx.symbol_table.get("uid")
        gid_arg = exec_ctx.symbol_table.get("gid")

        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'chown' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(uid_arg, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'chown' must be a number",
                    exec_ctx,
                )
            )
        if not isinstance(gid_arg, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'chown' must be a number",
                    exec_ctx,
                )
            )
        try:
            if hasattr(os, "chown"):
                os.chown(path_arg.value, int(uid_arg.value), int(gid_arg.value))
                return RTResult().success(NoneObject.none)
            else:
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        "Changing file ownership (chown) is not supported on this system",
                        exec_ctx,
                    )
                )
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"OS error changing ownership for '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error changing ownership: {str(e)}",
                    exec_ctx,
                )
            )

    execute_chown_fp.arg_names = ["path", "uid", "gid"]

    def execute_utime_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        times_arg = exec_ctx.symbol_table.get("times")

        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'utime' must be a string",
                    exec_ctx,
                )
            )

        actual_times_tuple = None
        if isinstance(times_arg, List):
            if (
                len(times_arg.elements) == 2
                and isinstance(times_arg.elements[0], Number)
                and isinstance(times_arg.elements[1], Number)
            ):
                actual_times_tuple = (
                    times_arg.elements[0].value,
                    times_arg.elements[1].value,
                )
            else:
                return RTResult().failure(
                    TError(
                        self.pos_start,
                        self.pos_end,
                        "Second argument of 'utime', if a list, must contain two numbers (access_time, modification_time)",
                        exec_ctx,
                    )
                )
        elif isinstance(times_arg, NoneObject):
            actual_times_tuple = None
        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'utime' must be a list of two numbers or none",
                    exec_ctx,
                )
            )

        try:
            os.utime(path_arg.value, actual_times_tuple)
            return RTResult().success(NoneObject.none)
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"OS error setting times for '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error setting times: {str(e)}",
                    exec_ctx,
                )
            )

    execute_utime_fp.arg_names = ["path", "times"]

    def execute_link_fp(self, exec_ctx):
        src = exec_ctx.symbol_table.get("src")
        dst = exec_ctx.symbol_table.get("dst")

        if not isinstance(src, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'link' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(dst, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'link' must be a string",
                    exec_ctx,
                )
            )
        try:
            if hasattr(os, "link"):
                os.link(src.value, dst.value)
                return RTResult().success(NoneObject.none)
            else:
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        "Creating hard links is not supported on this system or requires special privileges",
                        exec_ctx,
                    )
                )
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"OS error creating hard link '{src.value}' -> '{dst.value}': {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error creating hard link: {str(e)}",
                    exec_ctx,
                )
            )

    execute_link_fp.arg_names = ["src", "dst"]

    def execute_unlink_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'unlink' must be a string",
                    exec_ctx,
                )
            )

        if os.path.isdir(path_arg.value):
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Cannot unlink '{path_arg.value}': It is a directory\nTip: Use 'remove_dir' instead.",
                    exec_ctx,
                )
            )
        if not os.path.exists(path_arg.value) and not os.path.islink(path_arg.value):
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"File or link '{path_arg.value}' does not exist",
                    exec_ctx,
                )
            )
        try:
            os.unlink(path_arg.value)
            return RTResult().success(NoneObject.none)
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to remove file: {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error unlinking file/link: {str(e)}",
                    exec_ctx,
                )
            )

    execute_unlink_fp.arg_names = ["path"]

    def execute_chdir_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'chdir' must be a string",
                    exec_ctx,
                )
            )
        if not os.path.isdir(path_arg.value):
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Directory '{path_arg.value}' does not exist or is not a directory",
                    exec_ctx,
                )
            )
        try:
            os.chdir(path_arg.value)
            return RTResult().success(NoneObject.none)
        except OSError as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to set current directory to '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error changing directory: {str(e)}",
                    exec_ctx,
                )
            )

    execute_chdir_fp.arg_names = ["path"]

    def execute_access_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        mode_arg = exec_ctx.symbol_table.get("mode")

        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'access' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(mode_arg, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'access' must be a number",
                    exec_ctx,
                )
            )
        try:
            has_access = os.access(path_arg.value, int(mode_arg.value))
            return RTResult().success(Number.true if has_access else Number.false)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error checking access for '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )

    execute_access_fp.arg_names = ["path", "mode"]

    def execute_path_join_fp(self, exec_ctx):
        args_list_obj = exec_ctx.symbol_table.get("args")

        if not isinstance(args_list_obj, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'path_join' must be a list of path components",
                    exec_ctx,
                )
            )

        path_components_str = []
        for i, item in enumerate(args_list_obj.elements):
            if not isinstance(item, String):
                return RTResult().failure(
                    TError(
                        self.pos_start,
                        self.pos_end,
                        f"All path components for 'path_join' must be strings (component at index {i} is not)",
                        exec_ctx,
                    )
                )
            path_components_str.append(item.value)

        if not path_components_str:
            return RTResult().success(String(""))
        try:
            joined_path = os.path.join(*path_components_str)
            return RTResult().success(String(joined_path))
        except TypeError as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error joining path components: {str(e)}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Unexpected error joining path: {str(e)}",
                    exec_ctx,
                )
            )

    execute_path_join_fp.arg_names = ["args"]

    def execute_is_file_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'is_file' must be a string",
                    exec_ctx,
                )
            )
        try:
            is_file = os.path.isfile(path_arg.value)
            return RTResult().success(Number.true if is_file else Number.false)
        except Exception as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if path is file '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )

    execute_is_file_fp.arg_names = ["path"]

    def execute_is_dir_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'is_dir' must be a string",
                    exec_ctx,
                )
            )
        try:
            is_dir = os.path.isdir(path_arg.value)
            return RTResult().success(Number.true if is_dir else Number.false)
        except Exception as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if path is directory '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )

    execute_is_dir_fp.arg_names = ["path"]

    def execute_is_link_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'is_link' must be a string",
                    exec_ctx,
                )
            )
        try:
            is_link = os.path.islink(path_arg.value)
            return RTResult().success(Number.true if is_link else Number.false)
        except Exception as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if path is symlink '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )

    execute_is_link_fp.arg_names = ["path"]

    def execute_is_mount_fp(self, exec_ctx):
        path_arg = exec_ctx.symbol_table.get("path")
        if not isinstance(path_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'is_mount' must be a string",
                    exec_ctx,
                )
            )
        try:
            is_mount = os.path.ismount(path_arg.value)
            return RTResult().success(Number.true if is_mount else Number.false)
        except Exception as e:
            return RTResult().failure(
                IOError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if path is mount point '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )

    execute_is_mount_fp.arg_names = ["path"]

    def execute_request_fp(self, exec_ctx):
        url_arg = exec_ctx.symbol_table.get("url")
        method_arg = exec_ctx.symbol_table.get("method")
        headers_arg = exec_ctx.symbol_table.get("headers")
        data_arg = exec_ctx.symbol_table.get("data")
        timeout_arg = exec_ctx.symbol_table.get("timeout")
        if not isinstance(url_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'request' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(method_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'request' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(headers_arg, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'request' must be a list",
                    exec_ctx,
                )
            )
        if not isinstance(data_arg, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Fourth argument of 'request' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(timeout_arg, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Fifth argument of 'request' must be a number",
                    exec_ctx,
                )
            )
        try:
            response = requests.request(
                method_arg.value,
                url_arg.value,
                headers=headers_arg.elements,
                data=data_arg.value,
                timeout=timeout_arg.value,
            )
            return RTResult().success(self.validate_pyexec_result(response.json()))
        except requests.exceptions.RequestException as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Can not make request: {e}",
                    exec_ctx,
                )
            )

    execute_request_fp.arg_names = ["url", "method", "headers", "data", "timeout"]

    def execute_keys(self, exec_ctx):
        hm = exec_ctx.symbol_table.get("hm")
        if not isinstance(hm, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'keys' must be a hashmap",
                    exec_ctx,
                )
            )
        return RTResult().success(List(hm.values.keys()))

    execute_keys.arg_names = ["hm"]

    def execute_values(self, exec_ctx):
        hm = exec_ctx.symbol_table.get("hm")
        if not isinstance(hm, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'values' must be a hashmap",
                    exec_ctx,
                )
            )
        return RTResult().success(List(hm.values.values()))

    execute_values.arg_names = ["hm"]

    def execute_items(self, exec_ctx):
        hm = exec_ctx.symbol_table.get("hm")
        if not isinstance(hm, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'items' must be a hashmap",
                    exec_ctx,
                )
            )
        return RTResult().success(List(hm.values.items()))

    execute_items.arg_names = ["hm"]

    def execute_has(self, exec_ctx):
        hm = exec_ctx.symbol_table.get("hm")
        key = exec_ctx.symbol_table.get("key")
        if not isinstance(hm, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'has' must be a hashmap",
                    exec_ctx,
                )
            )
        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'has' must be a string",
                    exec_ctx,
                )
            )
        return RTResult().success(Bool(hm.values.has(key.value)))

    execute_has.arg_names = ["hm", "key"]
    def execute_get(self, exec_ctx):
        hm = exec_ctx.symbol_table.get("hm")
        key = exec_ctx.symbol_table.get("key")
        default = exec_ctx.symbol_table.get("default")

        if not isinstance(hm, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'get' must be a hashmap",
                    exec_ctx,
                )
            )

        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'get' must be a string",
                    exec_ctx,
                )
            )

        for k, v in hm.values.items():
            if k.value == key.value:
                return RTResult().success(v)

        return RTResult().success(default)
    execute_get.arg_names = ["hm", "key", "default"]



    def execute_set(self, exec_ctx):
        hm = exec_ctx.symbol_table.get("hm")
        key = exec_ctx.symbol_table.get("key")
        value = exec_ctx.symbol_table.get("value")

        if not isinstance(hm, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'set' must be a hashmap",
                    exec_ctx,
                )
            )
        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'set' must be a string",
                    exec_ctx,
                )
            )
        return RTResult().success(HashMap(hm.set_index(key, value)))

    execute_set.arg_names = ["hm", "key", "value"]

    def execute_del(self, exec_ctx):
        hm = exec_ctx.symbol_table.get("hm")
        key = exec_ctx.symbol_table.get("key")

        if not isinstance(hm, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'del' must be a hashmap",
                    exec_ctx,
                )
            )
        if not isinstance(key, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'del' must be a string",
                    exec_ctx,
                )
            )
        if key.value in hm.values:
            del hm.values[key.value]
            return RTResult().success(hm)
        return RTResult().success(NoneObject.none)


    execute_del.arg_names = ["hm", "key"]


for method_name in [m for m in dir(BuiltInFunction) if m.startswith("execute_")]:
    func_name = method_name[8:]
    method = getattr(BuiltInFunction, method_name)
    if hasattr(method, "arg_names"):
        setattr(BuiltInFunction, func_name, BuiltInFunction(func_name))
        BUILTIN_FUNCTIONS.append(func_name)


@lru_cache(maxsize=None)
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

    def visit_VarAssignAsNode(self, node, context: Context):
        res = RTResult()
        orig_name  = node.var_name_tok.value
        alias_name = node.var_name_tok2.value

        value = context.symbol_table.get(orig_name)
        if value is None:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Variable '{orig_name}' is not defined",
                context
            ))

        context.symbol_table.set(alias_name, value)
        context.private_symbol_table.set(alias_name, value)

        return res.success(value)

    def initialize_namespace(self, namespace_obj):
        if namespace_obj.get("initialized_"):
            return  # Đã chạy rồi

        stmts = namespace_obj.get("statements_")
        ns_context = namespace_obj.get("context_")

        for stmt in stmts:
            _ = self.visit(stmt, ns_context)

        for k, v in ns_context.symbol_table.symbols.items():
            namespace_obj.set(k, v)
        for k, v in ns_context.private_symbol_table.symbols.items():
            namespace_obj.set(k, v)

        namespace_obj.set("initialized_", True)

    
    def visit_CallMemberAccessNode(self, node, context):
        res = RTResult()
        obj = res.register(self.visit(node.object_node, context))
        if res.should_return(): return res

        if isinstance(obj, NameSpace) and not obj.get("__initialized__"):
            self.initialize_namespace(obj)

        member = obj.get(node.member_name)
        if member is None:
            return res.failure(
                RTError(node.pos_start, node.pos_end,
                        f"'{obj}' has no member '{node.member_name}'", context)
            )

        if isinstance(member, Error):
            return res.failure(member)
        if not isinstance(member, Function):
            return res.failure(
                RTError(node.pos_start, node.pos_end,
                        f"'{node.member_name}' is not a function", context)
            )

        args = []
        for arg_node in node.arg_nodes:
            args.append(res.register(self.visit(arg_node, context)))
            if res.should_return():
                return res
        return_value = res.register(member.execute(args))
        if res.should_return():
            return res
        return res.success(return_value)

    
    def visit_NameSpaceNode(self, node, context):
        res = RTResult()
        namespace = NameSpace(node.namespace_name)
        namespace.set_pos(node.pos_start, node.pos_end)
        namespace.set_context(context)

        ns_context = Context(node.namespace_name, context, node.pos_start)
        ns_context.symbol_table = SymbolTable(context.symbol_table)
        ns_context.private_symbol_table = SymbolTable(context.private_symbol_table)

        stmts = node.statements
        if hasattr(stmts, "element_nodes"):
            stmts = stmts.element_nodes

        namespace.set("statements_", stmts)
        namespace.set("context_", ns_context)
        namespace.set("initialized_", False)

        context.symbol_table.set(node.namespace_name, namespace)
        context.private_symbol_table.set(node.namespace_name, namespace)

        return res.success(namespace)

    
    def visit_MemberAccessNode(self, node, context):
        res = RTResult()
        obj = res.register(self.visit(node.object_node, context))
        if res.should_return(): return res

        if isinstance(obj, NameSpace) and not obj.get("initialized_"):
            self.initialize_namespace(obj)

        member = obj.get(node.member_name)
        if member is None:
            return res.failure(
                RTError(node.pos_start, node.pos_end,
                    f"'{obj}' has no member '{node.member_name}'", context)
            )

        if isinstance(member, Error):
            return res.failure(member)

        return res.success(member)




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
                return res.success(NoneObject.none if should_return_none else expr_value)

        if node.else_case:
            expr, should_return_none = node.else_case
            expr_value = res.register(self.visit(expr, context))
            if res.should_return():
                return res
            return res.success(NoneObject.none if should_return_none else expr_value)

        return res.success(NoneObject.none)

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

        if not should_return_none:
            elements = []

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
            return res.success(NoneObject.none)
        else:
            return res.success(
                List(elements)
                .set_context(context)
                .set_pos(node.pos_start, node.pos_end)
            )

    def visit_WhileNode(self, node, context):
        res = RTResult()
        should_return_none = node.should_return_none
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
            return res.success(NoneObject.none)
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
            value = NoneObject.none

        return res.success_return(value)

    def visit_ContinueNode(self, _, __):
        return RTResult().success_continue()

    def visit_BreakNode(self, _, __):
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

    def visit_HashMapNode(self, node, context):
        res = RTResult()
        values = {}

        for key_node, value_node in node.pairs:
            key = res.register(self.visit(key_node, context))
            if res.should_return():
                return res

            if not isinstance(key, String):
                return res.failure(
                    RTError(
                        key_node.pos_start,
                        key_node.pos_end,
                        f"Non-string key for hashmap: '{key!r}'",
                        context,
                    )
                )

            value = res.register(self.visit(value_node, context))
            if res.should_return():
                return res
            assert value is not None

            values[key.value] = value

        return res.success(HashMap(values))

    def visit_ForInNode(self, node: ForInNode, context: Context) -> RTResult:
        res = RTResult()
        var_name = node.var_name_tok.value
        body = node.body_node
        should_return_none = node.should_return_none

        iterable = res.register(self.visit(node.iterable_node, context))
        if res.should_return():
            return res

        iterator, error = iterable.iter()
        if error:
            return res.failure(error)

        elements = []

        try:
            while True:
                current = next(iterator)
                context.symbol_table.set(var_name, current)

                value = res.register(self.visit(body, context))
                if (
                    res.should_return()
                    and not res.loop_should_continue
                    and not res.loop_should_break
                ):
                    return res

                if res.loop_should_break:
                    break

                if res.loop_should_continue:
                    continue

                if not should_return_none:
                    elements.append(value)
        except StopIteration:
            pass

        if should_return_none:
            return res.success(NoneObject.none)
        else:
            return res.success(
                List(elements)
                .set_context(context)
                .set_pos(node.pos_start, node.pos_end)
            )


global_symbol_table.set("argv_fp", List([String(e) for e in sys.argv[1:]]))
global_symbol_table.set("os_sep_fp", String(os.sep))
global_symbol_table.set("none", NoneObject.none)
global_symbol_table.set("false", Number.false)
global_symbol_table.set("true", Number.true)
global_symbol_table.set("list", String("<list>"))
global_symbol_table.set("str", String("<str>"))
global_symbol_table.set("int", String("<int>"))
global_symbol_table.set("float", String("<float>"))
global_symbol_table.set("func", String("<func>"))
global_symbol_table.set("bool", String("<bool>"))
global_symbol_table.set("hashmap", String("<hashmap>"))
global_symbol_table.set("thread", String("<thread>"))
global_symbol_table.set("os_name_fp", String(os.name))
global_symbol_table.set("PI_fp", Number(math.pi))
global_symbol_table.set("E_fp", Number(math.e))
global_symbol_table.set("none_type", String("<none>"))

for func in BUILTIN_FUNCTIONS:
    global_symbol_table.set(func, getattr(BuiltInFunction, func))

private_symbol_table = SymbolTable()
private_symbol_table.set("is_main", Number(0))


def run(fn, text):
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error:
        return None, error
    # for token in tokens:
    #     print(token)
    result = None
    context = None
    try:
        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return None, ast.error
        # print(astpretty(ast.node))
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
