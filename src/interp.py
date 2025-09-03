import os
import sys
import time
import random
import math
import json
import asyncio
import platform
from .parser import *
from .nodes import *
from .datatypes import *

from .consts import *
from .errors import TError, IError, MError, Error, RTError
from shutil import rmtree, copy
from .lexer import Lexer, RTResult

from getpass import getpass
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


async def load_module(fn, interpreter, context):
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
        context.private_symbol_table.set("is_main", Number.false)
        result = await interpreter.visit(ast.node, context)
        result.value = "" if str(result.value) == "none" else result.value
        return result.value, result.error
    except KeyboardInterrupt:
        print(
            "\n---------------------------------------------------------------------------"
        )
        print(
            "InterruptError                            Traceback (most recent call last)\n"
        )
        print(
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}InterruptError{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}User Terminated{Fore.RESET}{Style.RESET_ALL}"
        )
        sys.exit(2)
    except OverflowError:
        print(
            "\n---------------------------------------------------------------------------"
        )
        print(
            "MemoryOverflowError                         Traceback (most recent call last)\n"
        )
        print(
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}MemoryOverflowError{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}Memory Overflow{Fore.RESET}{Style.RESET_ALL}"
        )
        sys.exit(2)


class BaseFunction(Object):
    __slots__ = "name"

    def __init__(self, name):
        super().__init__()
        self.name = name or "<anonymous>"

    def set_context(self, context=None):
        if hasattr(self, "context") and self.context:
            return self
        return super().set_context(context)

    def generate_new_context(self):
        new_context = Context(self.name, self.context, self.pos_start)
        new_context.symbol_table = SymbolTable(new_context.parent.symbol_table)
        new_context.private_symbol_table = SymbolTable(
            new_context.parent.private_symbol_table
        )
        return new_context

    async def handle_arguments(
        self,
        param_names,
        defaults,
        vargs_name,
        kargs_name,
        positional_args,
        keyword_args,
        exec_ctx,
    ):
        res = RTResult()
        interpreter = Interpreter()

        if not vargs_name and len(positional_args) > len(param_names):
            return res.failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Function takes {len(param_names)} positional arguments but {len(positional_args)} were given",
                    exec_ctx,
                )
            )

        for i, param_name in enumerate(param_names):
            if i < len(positional_args):
                exec_ctx.symbol_table.set(param_name, positional_args[i])
            elif param_name in keyword_args:
                exec_ctx.symbol_table.set(param_name, keyword_args.pop(param_name))
            elif i < len(param_names) - len(defaults):
                return res.failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        f"Missing required argument '{param_name}'",
                        exec_ctx,
                    )
                )
            else:
                default_index = i - (len(param_names) - len(defaults))
                default_value = defaults[default_index]

                is_node = not isinstance(default_value, Object)
                if is_node:
                    evaluated_default = res.register(
                        await interpreter.visit(default_value, exec_ctx)
                    )
                    if res.should_return():
                        return res
                    exec_ctx.symbol_table.set(param_name, evaluated_default)
                else:
                    final_default = (
                        default_value if default_value is not None else Number.none
                    )
                    exec_ctx.symbol_table.set(param_name, final_default)

        if vargs_name:
            remaining_pos_args = positional_args[len(param_names) :]
            vargs_list = List(remaining_pos_args)
            exec_ctx.symbol_table.set(vargs_name, vargs_list.set_context(exec_ctx))

        if kargs_name:
            kargs_map = HashMap(keyword_args)
            exec_ctx.symbol_table.set(kargs_name, kargs_map.set_context(exec_ctx))
        elif keyword_args:
            first_unknown = next(iter(keyword_args.keys()))
            return res.failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Function got an unexpected keyword argument '{first_unknown}'",
                    exec_ctx,
                )
            )

        return res.success(None)


class Function(BaseFunction):
    def __init__(
        self,
        name,
        body_node,
        arg_names,
        defaults,
        vargs_name_tok,
        kargs_name_tok,
        should_auto_return,
        is_async=False,
    ):
        super().__init__(name)
        self.body_node = body_node
        self.arg_names = arg_names
        self.defaults = defaults
        self.vargs_name = vargs_name_tok.value if vargs_name_tok else None
        self.kargs_name = kargs_name_tok.value if kargs_name_tok else None
        self.should_auto_return = should_auto_return
        self.is_async = is_async

    async def execute(self, positional_args, keyword_args):
        res = RTResult()
        interpreter = Interpreter()
        exec_ctx = self.generate_new_context()

        if self.is_async:
            return res.success(
                Coroutine(self, positional_args, keyword_args)
                .set_context(exec_ctx)
                .set_pos(self.pos_start, self.pos_end)
            )

        res.register(
            await self.handle_arguments(
                self.arg_names,
                self.defaults,
                self.vargs_name,
                self.kargs_name,
                positional_args,
                keyword_args,
                exec_ctx,
            )
        )
        if res.should_return():
            return res

        value = res.register(await interpreter.visit(self.body_node, exec_ctx))
        if res.should_return() and res.func_return_value is None:
            return res

        ret_value = (
            (value if self.should_auto_return else None)
            or res.func_return_value
            or Number.none
        )
        return res.success(ret_value)

    def copy(self):
        copy = Function(
            self.name,
            self.body_node,
            self.arg_names,
            self.defaults,
            Token(TT_IDENTIFIER, self.vargs_name) if self.vargs_name else None,
            Token(TT_IDENTIFIER, self.kargs_name) if self.kargs_name else None,
            self.should_auto_return,
            self.is_async,
        )
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return (
            f"<async function {self.name}>"
            if self.is_async
            else f"<function {self.name}>"
        )

    def type(self):
        return "<async_func>" if self.is_async else "<func>"


class BuiltInFunction(BaseFunction):
    __slots__ = ("name", "body_node", "arg_names", "defaults", "should_auto_return")

    def __init__(self, name):
        super().__init__(name)

    async def execute(self, positional_args, keyword_args):
        res = RTResult()
        exec_ctx = self.generate_new_context()
        method_name = f"execute_{self.name}"
        method = getattr(self, method_name, self.no_execute_method)

        if asyncio.iscoroutinefunction(method):
            return res.success(
                Coroutine(self, positional_args, keyword_args)
                .set_context(exec_ctx)
                .set_pos(self.pos_start, self.pos_end)
            )

        res.register(
            await self.handle_arguments(
                param_names=method.arg_names,
                defaults=method.defaults,
                vargs_name=None,
                kargs_name=None,
                positional_args=positional_args,
                keyword_args=keyword_args,
                exec_ctx=exec_ctx,
            )
        )
        if res.should_return():
            return res

        return_value = res.register(method(exec_ctx))

        if res.should_return():
            return res

        return res.success(return_value)

    def no_execute_method(self, _, __):
        raise Exception(f"No execute_{self.name} method defined")

    def copy(self):
        copy = BuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function {self.name}>"

    @staticmethod
    def set_args(arg_names, defaults=None):
        if defaults is None:
            defaults = [None] * len(arg_names)

        def _args(f):
            f.arg_names = arg_names
            f.defaults = defaults
            return f

        return _args

    @set_args(["seconds"])
    async def execute_sleep_async_fp(self, exec_ctx):
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
        await asyncio.sleep(seconds.value)
        return RTResult().success(Number.none)

    @set_args(["value"], [String("")])
    def execute_println(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        if isinstance(value, String):
            print(value.value, flush=True)
            return RTResult().success(Number.none)
        print(repr(exec_ctx.symbol_table.get("value")), flush=True)
        return RTResult().success(Number.none)

    @set_args(["value"], [String("")])
    def execute_print(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        if isinstance(value, String):
            print(value.value, end="", flush=True)
            return RTResult().success(Number.none)
        print(repr(exec_ctx.symbol_table.get("value")), end="", flush=True)
        return RTResult().success(Number.none)

    @set_args(["prompt"], [String("")])
    def execute_input(self, exec_ctx):
        prompt = exec_ctx.symbol_table.get("prompt")
        text = input(prompt.value)
        return RTResult().success(String(text))

    @set_args(["prompt"], [String("")])
    def execute_get_password(self, exec_ctx):
        prompt = exec_ctx.symbol_table.get("prompt")
        pass_ = getpass(prompt.value)
        return RTResult().success(String(pass_))

    @set_args([])
    def execute_clear(self, _):
        os.system("cls" if os.name == "nt" else "clear")
        return RTResult().success(Number.none)

    @set_args(["value"])
    def execute_type(self, exec_ctx):
        data = exec_ctx.symbol_table.get("value")
        return RTResult().success(String(data.type()))

    @set_args(["value"])
    def execute_is_none(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        return RTResult().success(
            Number.true if isinstance(value, NoneObject) else Number.false
        )

    @set_args(["value"])
    def execute_is_num(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), Number)
        return RTResult().success(Number.true if is_number else Number.false)

    @set_args(["value"])
    def execute_is_bool(self, exec_ctx):
        is_bool = isinstance(exec_ctx.symbol_table.get("value"), Bool)
        return RTResult().success(Number.true if is_bool else Number.false)

    @set_args(["value"])
    def execute_is_str(self, exec_ctx):
        is_str = isinstance(exec_ctx.symbol_table.get("value"), String)
        return RTResult().success(Number.true if is_str else Number.false)

    @set_args(["value"])
    def execute_is_list(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), List)
        return RTResult().success(Number.true if is_number else Number.false)

    @set_args(["value"])
    def execute_is_func(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), BaseFunction)
        return RTResult().success(Number.true if is_number else Number.false)

    @set_args(["value", "reverse"], [None, Number.false])
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
            lst.value.sort(key=lambda x: x.value, reverse=True)
        elif int(reverse.value) == 0:
            lst.value.sort(key=lambda x: x.value)
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

    @set_args(["object", "value"])
    def execute_append(self, exec_ctx):
        obj_ = exec_ctx.symbol_table.get("object")
        value = exec_ctx.symbol_table.get("value")

        if isinstance(obj_, List):
            obj_.value.append(value)
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

    @set_args(["list", "index"])
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
            element = list_.value.pop(int(index.value))
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

    @set_args(["listA", "listB"])
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
        listA.value.extend(listB.value)
        return RTResult().success(Number.none)

    @set_args(["list", "index", "element"])
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
        list_.value.insert(int(index.value), element)
        return RTResult().success(Number.none)

    @set_args(["string", "value", "with", "c"], [None, None, None, Number(-1)])
    def execute_replace_fp(self, exec_ctx):
        string = exec_ctx.symbol_table.get("string")
        value = exec_ctx.symbol_table.get("value")
        with_val = exec_ctx.symbol_table.get("with")
        c = exec_ctx.symbol_table.get("c")
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
        if not isinstance(with_val, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Fourth argument of 'replace' must be a string",
                    exec_ctx,
                )
            )
        val = string.value.replace(value.value, with_val.value, c)
        return RTResult().success(String(val))

    @set_args(["value"])
    def execute_len(self, exec_ctx):
        value_ = exec_ctx.symbol_table.get("value")
        if isinstance(value_, List | String | Bytes | HashMap):
            return RTResult().success(Number(len(value_.value)))
        else:
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'len' must be a list, string, hashmap or bytes",
                    exec_ctx,
                )
            )

    @set_args(["seconds"])
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
        return RTResult().success(Number.none)

    @set_args(["value"], [0])
    def execute_exit_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        sys.exit(int(value.value))

    @set_args(
        ["l", "start", "end", "step"], [None, Number.none, Number.none, Number.none]
    )
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
                    "First argument of 'slice' must be a string, list, hashmap or bytes",
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
            sliced_l = dict(l.value.items()[a:b:s])
            return RTResult().success(HashMap(sliced_l))
        elif isinstance(l, Bytes):
            sliced_l = l.value[a:b:s]
            return RTResult().success(Bytes(sliced_l))
        sliced_l = l.value[a:b:s]
        return RTResult().success(List(sliced_l))

    @set_args(["file_path"])
    def execute_open_fp(self, exec_ctx):
        file_path = exec_ctx.symbol_table.get("file_path")
        try:
            file_name = os.path.splitext(file_path.value)[0]
            return RTResult().success(File(file_name, file_path.value))
        except Exception as e:
            return RTResult().failure(
                IError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to open file "{file_path.value}": ' + str(e),
                    exec_ctx,
                )
            )

    @set_args(["file", "mode"])
    def execute_read_fp(self, exec_ctx):
        file = exec_ctx.symbol_table.get("file")
        mode = exec_ctx.symbol_table.get("mode")
        if mode.value == "r":
            try:
                with open(
                    file.path.__str__(),
                    mode.value,
                    encoding="utf-8" if "b" not in mode.value else None,
                ) as f:
                    return RTResult().success(String(f.read()))
            except Exception as e:
                return RTResult().failure(
                    IError(
                        self.pos_start,
                        self.pos_end,
                        f'Failed to read file "{file.path}"\n' + str(e),
                        exec_ctx,
                    )
                )
        elif mode.value == "rb":
            try:
                with open(file.path.__str__(), "rb") as f:
                    return RTResult().success(Bytes(f.read()))
            except Exception as e:
                return RTResult().failure(
                    IError(
                        self.pos_start,
                        self.pos_end,
                        f'Failed to read file "{file.path}": ' + str(e),
                        exec_ctx,
                    )
                )

    @set_args(["file", "mode", "text"])
    def execute_write_fp(self, exec_ctx):
        file = exec_ctx.symbol_table.get("file")
        mode = exec_ctx.symbol_table.get("mode")
        text = exec_ctx.symbol_table.get("text")
        try:
            with open(
                file.path.__str__(),
                mode.__str__(),
                encoding="utf-8" if "b" not in mode.value else None,
            ) as f:
                f.write(text.value)
            return RTResult().success(Number.none)
        except Exception as e:
            return RTResult().failure(
                IError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to write to file "{file.path}": ' + str(e),
                    exec_ctx,
                )
            )

    @set_args(["file_path"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if file exists '{file_path}': " + str(e),
                    exec_ctx,
                )
            )

    @set_args([])
    def execute_time_fp(self, _):
        return RTResult().success(Number(time.time()))

    @set_args(["name"])
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

    @set_args(["name", "value"])
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
            return RTResult().success(Number.none)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to set environment variable '{name.value}': " + str(e),
                    exec_ctx,
                )
            )

    @set_args([])
    def execute_get_cdir_fp(self, exec_ctx):
        try:
            return RTResult().success(String(os.getcwd()))
        except Exception as e:
            return RTResult().failure(
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get current directory: " + str(e),
                    exec_ctx,
                )
            )

    @set_args(["name"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Directory '{name.value}' does not exist",
                    exec_ctx,
                )
            )
        try:
            os.chdir(name.value)
            return RTResult().success(Number.none)
        except Exception as e:
            return RTResult().failure(
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to set current directory to '{name.value}': " + str(e),
                    exec_ctx,
                )
            )

    @set_args([])
    def execute_rand_fp(self, _):
        return RTResult().success(Number(random.random()))

    @set_args(["min", "max"])
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

    @set_args(["min", "max"])
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

    @set_args(["arr"])
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
        if len(arr.value) == 0:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Array passed to 'rand_choice' is empty",
                    exec_ctx,
                )
            )
        return RTResult().success(arr.value[random.randrange(0, len(arr.value) - 1)])

    @set_args(["value"])
    def execute_to_str(self, exec_ctx):
        return RTResult().success(String(str(exec_ctx.symbol_table.get("value"))))

    @set_args(["value", "supress_error"], [None, Number.false])
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
        if isinstance(value, Number | CFloat):
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

    @set_args(["value", "supress_error"], [None, Number.false])
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
        if isinstance(value, Number | CFloat):
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

    @set_args(["sep", "value"])
    def execute_join_fp(self, exec_ctx):
        sep = exec_ctx.symbol_table.get("sep")
        iterables = exec_ctx.symbol_table.get("value")
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
            if len(iterables.value) == 0:
                return RTResult().success(String(""))
            return RTResult().success(
                String(sep.value.join([str(element) for element in iterables.value]))
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

    @set_args(["command"])
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
        return RTResult().success(Number.none)

    @set_args(["command"])
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

    @set_args(["message", "err_type"], [None, String("RT")])
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
                IError(self.pos_start, self.pos_end, msg, exec_ctx)
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

    @set_args(["string", "sep"], [None, String("")])
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

    @set_args(["string", "sep"], [None, String(" ")])
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

    @set_args(["string"])
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

    @set_args(["string"])
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

    @set_args(["time"])
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

    @set_args(["dir_path"], [String(".")])
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
                IError(
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to list directory: {e}",
                    exec_ctx,
                )
            )

    @set_args(["dir_path"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Directory '{value.value}' already exists",
                    exec_ctx,
                )
            )
        os.mkdir(value.value)
        return RTResult().success(Number.none)

    @set_args(["file_path"])
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
                IError(
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to remove file: " + str(e),
                    exec_ctx,
                )
            )
        return RTResult().success(Number.none)

    @set_args(["old_file_path", "new_file_path"])
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
                IError(
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to rename file: {e}",
                    exec_ctx,
                )
            )
        return RTResult().success(Number.none)

    @set_args(["dir_path"])
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
                IError(
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to remove directory: {e}",
                    exec_ctx,
                )
            )
        return RTResult().success(Number.none)

    @set_args(["src_path", "dst_path"])
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
                IError(
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to copy file: {e}",
                    exec_ctx,
                )
            )
        return RTResult().success(Number.none)

    @set_args(["text"])
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
            import keyboard  # type: ignore

            keyboard.write(text.value)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available",
                    exec_ctx,
                )
            )
        return RTResult().success(Number.none)

    @set_args(["key"])
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
            import keyboard  # type: ignore

            keyboard.press(key.value)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available",
                    exec_ctx,
                )
            )
        return RTResult().success(Number.none)

    @set_args(["key"])
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
            import keyboard  # type: ignore

            keyboard.release(key.value)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available",
                    exec_ctx,
                )
            )
        return RTResult().success(Number.none)

    @set_args(["key"])
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
            import keyboard  # type: ignore

            keyboard.wait(key.value)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available",
                    exec_ctx,
                )
            )
        return RTResult().success(Number.none)

    @set_args(["key"])
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
            import keyboard  # type: ignore

            is_pressed = keyboard.is_pressed(key.value)
            return RTResult().success(Number.true if is_pressed else Number.false)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available",
                    exec_ctx,
                )
            )

    def _handle_panic_result(self, res, exec_ctx):
        if res.error:
            err = res.error
            if isinstance(err, RTError):
                err_str = str(err)
                err_line = err_str.strip().split("\n")[-1]
                err_name, err_msg = err_line.split(":", 1)
                err_name, err_msg = err_name.strip(), err_msg.strip()

                if "Runtime" in err_name:
                    err_name_short = "RT"
                elif "Math" in err_name:
                    err_name_short = "M"
                elif "IO" in err_name:
                    err_name_short = "IO"
                elif "Type" in err_name:
                    err_name_short = "T"
                else:
                    err_name_short = "UNKNOWN"

                return RTResult().success(
                    List([NoneObject.none, String(err_msg), String(err_name_short)])
                )
            else:
                return RTResult().failure(err)
        else:
            return RTResult().success(
                List([res.value, NoneObject.none, NoneObject.none])
            )

    @set_args(["func", "args", "kwargs"], [None, List([]), HashMap({})])
    def execute_is_panic(self, exec_ctx):
        func = exec_ctx.symbol_table.get("func")
        args = exec_ctx.symbol_table.get("args")
        kwargs = exec_ctx.symbol_table.get("kwargs")

        if not isinstance(func, BaseFunction):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'is_panic' must be a function",
                    exec_ctx,
                )
            )
        if not isinstance(args, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument 'args' must be a list",
                    exec_ctx,
                )
            )
        if not isinstance(kwargs, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument 'kwargs' must be a hashmap",
                    exec_ctx,
                )
            )

        try:
            positional_args = args.value
            keyword_args = kwargs.value

            res = func.execute(positional_args, keyword_args)

            return self._handle_panic_result(res, exec_ctx)

        except Exception as err:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Unexpected Python error in 'is_panic': {err}",
                    exec_ctx,
                )
            )

    @set_args(["func", "args", "kwargs"], [None, List([]), HashMap({})])
    async def execute_async_is_panic_fp(self, exec_ctx):
        func = exec_ctx.symbol_table.get("func")
        args = exec_ctx.symbol_table.get("args")
        kwargs = exec_ctx.symbol_table.get("kwargs")

        if not isinstance(func, BaseFunction):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'is_panic' must be a function",
                    exec_ctx,
                )
            )
        if not isinstance(args, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument 'args' must be a list",
                    exec_ctx,
                )
            )
        if not isinstance(kwargs, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument 'kwargs' must be a hashmap",
                    exec_ctx,
                )
            )

        try:
            positional_args = args.value
            keyword_args = kwargs.value

            res = await func.execute(positional_args, keyword_args)

            return self._handle_panic_result(res, exec_ctx)

        except Exception as err:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Unexpected Python error in 'async_is_panic': {err}",
                    exec_ctx,
                )
            )

    @set_args(["func", "args", "kwargs"], [None, List([]), HashMap({})])
    def execute_thread_start_fp(self, exec_ctx):
        func = exec_ctx.symbol_table.get("func")
        args = exec_ctx.symbol_table.get("args")
        kwargs = exec_ctx.symbol_table.get("kwargs")

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
                    "Second argument 'args' must be a list",
                    exec_ctx,
                )
            )
        if not isinstance(kwargs, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument 'kwargs' must be a hashmap",
                    exec_ctx,
                )
            )

        try:
            import threading

            positional_args = args.value
            keyword_args = kwargs.value

            def thread_wrapper():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(func.execute(positional_args, keyword_args))
                finally:
                    loop.close()

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

    @set_args(["seconds"])
    def execute_thread_sleep_fp(self, exec_ctx):
        seconds = exec_ctx.symbol_table.get("seconds")
        if not isinstance(seconds, Number | CFloat):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'sleep' must be a number or cfloat",
                    exec_ctx,
                )
            )
        try:
            import time

            time.sleep(seconds.value)
            return RTResult().success(Number.none)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to sleep thread: {str(e)}",
                    exec_ctx,
                )
            )

    @set_args(["thread", "timeout"], [None, Number(15)])
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
            return RTResult().success(Number.none)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to join thread: {str(e)}",
                    exec_ctx,
                )
            )

    @set_args(["thread"])
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

    @set_args(["thread"])
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
            return RTResult().success(Number.none)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to cancel thread: {str(e)}",
                    exec_ctx,
                )
            )

    @set_args(["thread"])
    def execute_is_thread(self, exec_ctx):
        thread = exec_ctx.symbol_table.get("thread")
        return RTResult().success(
            Number.true if isinstance(thread, ThreadWrapper) else Number.false
        )

    @set_args(["value"])
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

    @set_args(["value"])
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

    @set_args([])
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

    @set_args([])
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

    @set_args(["host"])
    def execute_ping_fp(self, exec_ctx):
        host = exec_ctx.symbol_table.get("host")
        if not isinstance(host, String):
            return RTResult().failure(
                TError(self.pos_start, self.pos_end, "Host must be a string", exec_ctx)
            )

        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", host.value]

        try:
            subprocess.check_call(
                command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return RTResult().success(Bool(True))
        except subprocess.CalledProcessError:
            return RTResult().success(Bool(False))
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error while pinging host: {e}",
                    exec_ctx,
                )
            )

    @set_args(["url", "timeout"], [None, Number(15)])
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
                    f"HTTP Error {e.code}: Failed to download {url.value}",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to download {url.value}: {str(e)}",
                    exec_ctx,
                )
            )

    @set_args([])
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

    @set_args([])
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

    @set_args(["text"])
    def execute_md5_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, Bytes):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'md5' must be a bytes",
                    exec_ctx,
                )
            )
        return RTResult().success(Bytes(hashlib.md5(text.value).hexdigest().encode()))

    @set_args(["text"])
    def execute_sha1_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, Bytes):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'sha1' must be a bytes",
                    exec_ctx,
                )
            )
        return RTResult().success(Bytes(hashlib.sha1(text.value).hexdigest().encode()))

    @set_args(["text"])
    def execute_sha256_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, Bytes):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'sha256' must be a bytes",
                    exec_ctx,
                )
            )
        return RTResult().success(
            Bytes(hashlib.sha256(text.value).hexdigest().encode())
        )

    @set_args(["text"])
    def execute_sha512_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, Bytes):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'sha512' must be a bytes",
                    exec_ctx,
                )
            )
        return RTResult().success(
            Bytes(hashlib.sha512(text.value).hexdigest().encode())
        )

    @set_args(["text"])
    def execute_crc32_fp(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, Bytes):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'crc32' must be a bytes",
                    exec_ctx,
                )
            )
        return RTResult().success(
            Bytes(format(zlib.crc32(text.value) & 0xFFFFFFFF, "08x").encode())
        )

    @set_args(["text", "substring"])
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
            return RTResult().success(Number.none)
        return RTResult().success(Number(index))

    @set_args(["path"])
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

    @set_args(["a"])
    def execute_sqrt_fp(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        return RTResult().success(Number(math.sqrt(a.value)))

    @set_args(["a"])
    def execute_abs_fp(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        return RTResult().success(Number(abs(a.value)))

    @set_args(["x"])
    def execute_sin_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.sin(x.value)))

    @set_args(["x"])
    def execute_cos_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.cos(x.value)))

    @set_args(["x"])
    def execute_tan_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.tan(x.value)))

    @set_args(["n"])
    def execute_fact_fp(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        return RTResult().success(Number(math.factorial(int(n.value))))

    @set_args(["a", "b"])
    def execute_gcd_fp(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        b = exec_ctx.symbol_table.get("b")
        return RTResult().success(Number(math.gcd(int(a.value), int(b.value))))

    @set_args(["a", "b"])
    def execute_lcm_fp(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        b = exec_ctx.symbol_table.get("b")
        return RTResult().success(Number(math.lcm(int(a.value), int(b.value))))

    @set_args(["n"])
    def execute_fib_fp(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        if n.value == 0:
            return RTResult().success(Number(0))
        a, b = 0, 1
        for _ in range(n.value):
            a, b = b, a + b
        return RTResult().success(Number(a))

    @set_args(["n"])
    def execute_is_prime_fp(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n").value
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

    @set_args(["d"])
    def execute_deg2rad_fp(self, exec_ctx):
        d = exec_ctx.symbol_table.get("d")
        return RTResult().success(Number(math.radians(d.value)))

    @set_args(["r"])
    def execute_rad2deg_fp(self, exec_ctx):
        r = exec_ctx.symbol_table.get("r")
        return RTResult().success(Number(math.degrees(r.value)))

    @set_args(["x"])
    def execute_exp_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.exp(x.value)))

    @set_args(["x"])
    def execute_log_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.log(x.value)))

    @set_args(["x"])
    def execute_sinh_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.sinh(x.value)))

    @set_args(["x"])
    def execute_cosh_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.cosh(x.value)))

    @set_args(["x"])
    def execute_tanh_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(math.tanh(x.value)))

    @set_args(["x"])
    def execute_round_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        return RTResult().success(Number(round(x.value)))

    def convert_zer_to_py(self, obj):
        if isinstance(obj, Number):
            return obj.value
        elif isinstance(obj, String):
            return obj.value
        elif isinstance(obj, CFloat):
            return obj.value
        elif isinstance(obj, NoneObject):
            return None
        elif isinstance(obj, List):
            return [self.convert_zer_to_py(e) for e in obj.value]
        elif isinstance(obj, HashMap):
            result = {}
            for k, v in obj.value.items():
                key = self.convert_zer_to_py(k)
                val = self.convert_zer_to_py(v)
                result[key] = val
            return result
        elif isinstance(obj, PyObject):
            return obj.get_obj()
        elif isinstance(obj, Bytes):
            return obj.value
        else:
            return str(obj)

    def validate_pyexec_result(self, obj):
        allowed = (bool, int, float, str, Fraction)
        if obj is None:
            return Number.none
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
            elif isinstance(obj, bytes):
                return Bytes(obj)
            elif isinstance(obj, Fraction):
                return CFloat(obj)
            else:
                return String(obj)
        elif isinstance(obj, list):
            items = []
            for item in obj:
                if not isinstance(
                    item, (bool, int, float, str, list, dict, tuple, type(None), bytes)
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
            return PyObject(obj)

    @set_args(["code", "args"], [None, HashMap({})])
    def execute_pyexec(self, exec_ctx):
        code = exec_ctx.symbol_table.get("code")
        args = exec_ctx.symbol_table.get("args")
        if not isinstance(code, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'pyexec' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(args, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'pyexec' must be a hashmap",
                    exec_ctx,
                )
            )
        try:
            local_env = self.convert_zer_to_py(args)
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

    @set_args(["path"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get absolute path for '{path.value}': {str(e)}",
                    exec_ctx,
                )
            )

    @set_args(["path"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get directory name for '{path.value}': {str(e)}",
                    exec_ctx,
                )
            )

    @set_args(["path"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get base name for '{path.value}': {str(e)}",
                    exec_ctx,
                )
            )

    @set_args(["src", "dst"])
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
                return RTResult().success(Number.none)
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
                IError(
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

    @set_args(["path"])
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
                IError(
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

    @set_args(["path"])
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
                IError(
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

    @set_args(["path"])
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
                IError(
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

    @set_args(["top"])
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

    @set_args(["path", "mode"])
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
            return RTResult().success(Number.none)
        except OSError as e:
            return RTResult().failure(
                IError(
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

    @set_args(["path", "uid", "gid"])
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
                return RTResult().success(Number.none)
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
                IError(
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

    @set_args(["path", "times"])
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
                len(times_arg.value) == 2
                and isinstance(times_arg.value[0], Number)
                and isinstance(times_arg.value[1], Number)
            ):
                actual_times_tuple = (
                    times_arg.value[0].value,
                    times_arg.value[1].value,
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
            return RTResult().success(Number.none)
        except OSError as e:
            return RTResult().failure(
                IError(
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

    @set_args(["src", "dst"])
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
                return RTResult().success(Number.none)
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
                IError(
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

    @set_args(["path"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Cannot unlink '{path_arg.value}': It is a directory",
                    exec_ctx,
                )
            )
        if not os.path.exists(path_arg.value) and not os.path.islink(path_arg.value):
            return RTResult().failure(
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"File or link '{path_arg.value}' does not exist",
                    exec_ctx,
                )
            )
        try:
            os.unlink(path_arg.value)
            return RTResult().success(Number.none)
        except OSError as e:
            return RTResult().failure(
                IError(
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

    @set_args(["path", "mode"])
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

    @set_args(["args"])
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
        for i, item in enumerate(args_list_obj.value):
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

    @set_args(["path"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if path is directory '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )

    @set_args(["path"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if path is symlink '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )

    @set_args(["path"])
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
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to check if path is mount point '{path_arg.value}': {str(e)}",
                    exec_ctx,
                )
            )

    @set_args(
        ["url", "method", "headers", "data", "timeout"],
        [None, None, None, None, Number(15)],
    )
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
            import requests  # type: ignore

            response = requests.request(
                method_arg.value,
                url_arg.value,
                headers=self.convert_zer_to_py(headers_arg),
                data=self.convert_zer_to_py(data_arg),
                timeout=timeout_arg.value,
            )
            return RTResult().success(self.validate_pyexec_result(response.json()))
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "requests module not available",
                    exec_ctx,
                )
            )
        except requests.exceptions.RequestException as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Can not make request: {e}",
                    exec_ctx,
                )
            )

    @set_args(["hm"])
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
        return RTResult().success(List([String(k) for k in hm.value.keys()]))

    @set_args(["hm"])
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
        return RTResult().success(List(list(hm.value.values())))

    @set_args(["hm"])
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
        return RTResult().success(
            List([List([String(k), v]) for k, v in hm.value.items()])
        )

    @set_args(["hm", "key"])
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
        found = any(
            k.value == key.value for k in hm.value.keys() if hasattr(k, "value")
        )
        return RTResult().success(Number.true if found else Number.false)

    @set_args(["hm", "key", "default"], [None, None, Number.none])
    def execute_get(self, exec_ctx):
        hm = exec_ctx.symbol_table.get("hm")
        key = exec_ctx.symbol_table.get("key")
        default = exec_ctx.symbol_table.get("default")
        if not isinstance(hm, (HashMap, List)):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'get' must be a hashmap or list",
                    exec_ctx,
                )
            )
        if isinstance(hm, HashMap):
            if not isinstance(key, String):
                return RTResult().failure(
                    TError(
                        self.pos_start,
                        self.pos_end,
                        "Second argument of 'get' must be a string when first argument is a hashmap",
                        exec_ctx,
                    )
                )
            for k, v in hm.value.items():
                if hasattr(k, "value") and k.value == key.value:
                    return RTResult().success(v)
        else:
            if not isinstance(key, Number):
                return RTResult().failure(
                    TError(
                        self.pos_start,
                        self.pos_end,
                        "Second argument of 'get' must be a number when first argument is a list",
                        exec_ctx,
                    )
                )
            if 0 <= key.value < len(hm.value):
                return RTResult().success(hm.value[int(key.value)])
        return RTResult().success(default)

    @set_args(["hm", "key"])
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
        key_to_del = None
        for k in hm.value.keys():
            if hasattr(k, "value") and k.value == key.value:
                key_to_del = k
                break
        if key_to_del is not None:
            del hm.value[key_to_del]
            return RTResult().success(hm)
        return RTResult().success(Number.none)

    @set_args(["x", "y"])
    def execute_mouse_move_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        y = exec_ctx.symbol_table.get("y")
        if not isinstance(x, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'move' must be a number",
                    exec_ctx,
                )
            )
        if not isinstance(y, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'move' must be a number",
                    exec_ctx,
                )
            )
        try:
            import pyautogui  # type: ignore

            pyautogui.moveTo(int(x.value), int(y.value))
            return RTResult().success(Number.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "pyautogui module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args([])
    def execute_mouse_click_fp(self, exec_ctx):
        try:
            import pyautogui  # type: ignore

            pyautogui.click()
            return RTResult().success(Number.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "pyautogui module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args([])
    def execute_mouse_right_click_fp(self, exec_ctx):
        try:
            import pyautogui  # type: ignore

            pyautogui.rightClick()
            return RTResult().success(Number.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "pyautogui module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args(["amount"])
    def execute_mouse_scroll_fp(self, exec_ctx):
        amount = exec_ctx.symbol_table.get("amount")
        if not isinstance(amount, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'scroll' must be a number",
                    exec_ctx,
                )
            )
        try:
            import pyautogui  # type: ignore

            pyautogui.scroll(int(amount.value))
            return RTResult().success(Number.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "pyautogui module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args([])
    def execute_mouse_position_fp(self, exec_ctx):
        try:
            import pyautogui  # type: ignore

            x, y = pyautogui.position()
            return RTResult().success(List([Number(x), Number(y)]))
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "pyautogui module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args(["path"])
    def execute_screen_capture_fp(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        if not isinstance(path, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'capture' must be a string",
                    exec_ctx,
                )
            )
        try:
            import pyautogui  # type: ignore

            pyautogui.screenshot(path.value)
            return RTResult().success(Number.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "pyautogui module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args(["x", "y", "w", "h", "p"])
    def execute_screen_capture_area_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        y = exec_ctx.symbol_table.get("y")
        w = exec_ctx.symbol_table.get("w")
        h = exec_ctx.symbol_table.get("h")
        p = exec_ctx.symbol_table.get("p")
        if not isinstance(x, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'capture_area' must be a number",
                    exec_ctx,
                )
            )
        if not isinstance(y, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'capture_area' must be a number",
                    exec_ctx,
                )
            )
        if not isinstance(w, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'capture_area' must be a number",
                    exec_ctx,
                )
            )
        if not isinstance(h, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Fourth argument of 'capture_area' must be a number",
                    exec_ctx,
                )
            )
        try:
            from PIL import ImageGrab  # type: ignore

            img = ImageGrab.grab(
                bbox=(
                    int(x.value),
                    int(y.value),
                    int(x.value) + int(w.value),
                    int(y.value) + int(h.value),
                )
            )
            img.save(p.value)
            return RTResult().success(Number.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Pillow module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args(["x", "y"])
    def execute_screen_get_color_fp(self, exec_ctx):
        x = exec_ctx.symbol_table.get("x")
        y = exec_ctx.symbol_table.get("y")
        if not isinstance(x, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'get_color' must be a number",
                    exec_ctx,
                )
            )
        if not isinstance(y, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'get_color' must be a number",
                    exec_ctx,
                )
            )
        try:
            import pyautogui  # type: ignore

            color = pyautogui.screenshot().getpixel((int(x.value), int(y.value)))
            hex_color = "#%02x%02x%02x" % color
            return RTResult().success(String(hex_color))
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "pyautogui module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args(
        ["value", "from_hex", "supress_error"], [None, Number.false, Number.false]
    )
    def execute_to_bytes(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        from_hex = exec_ctx.symbol_table.get("from_hex")
        suppress_error = exec_ctx.symbol_table.get("supress_error")

        if not isinstance(from_hex, Bool):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'to_bytes' must be a boolean (from_hex)",
                    exec_ctx,
                )
            )

        if not isinstance(suppress_error, Bool):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'to_bytes' must be a boolean (supress_error)",
                    exec_ctx,
                )
            )

        from_hex_ = bool(from_hex.value)
        suppress_error_ = bool(suppress_error.value)

        try:
            if isinstance(value, Number):
                hex_str = hex(int(value.value))[2:]
                return RTResult().success(Bytes(bytes.fromhex(hex_str)))

            elif isinstance(value, String):
                if from_hex_:
                    return RTResult().success(Bytes(bytes.fromhex(value.value)))
                else:
                    return RTResult().success(Bytes(value.value.encode()))

            elif isinstance(value, Bytes):
                return RTResult().success(Bytes(value.value))

            else:
                raise TypeError(f"Cannot convert type '{value.type()}' to bytes")

        except Exception as e:
            if suppress_error_:
                return RTResult().success(Number.none)
            else:
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        f"Failed to convert value of type '{value.type()}' to bytes: {e}",
                        exec_ctx,
                    )
                )

    @set_args(["value"])
    def execute_is_bytes(self, exec_ctx):
        is_bytes = isinstance(exec_ctx.symbol_table.get("value"), Bytes)
        return RTResult().success(Number.true if is_bytes else Number.false)

    @set_args(["s", "encoding", "errors"], [None, String("utf-8"), String("strict")])
    def execute_decode_fp(self, exec_ctx):
        s = exec_ctx.symbol_table.get("s")
        encoding = exec_ctx.symbol_table.get("encoding")
        errors = exec_ctx.symbol_table.get("errors")
        if not isinstance(s, Bytes):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'decode' must be bytes",
                    exec_ctx,
                )
            )
        if not isinstance(encoding, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'decode' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(errors, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'decode' must be a string",
                    exec_ctx,
                )
            )
        try:
            decoded = s.value.decode(encoding.value, errors.value)
            return RTResult().success(String(decoded))
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to decode bytes: {e}",
                    exec_ctx,
                )
            )

    @set_args(["s", "encoding", "errors"], [None, String("utf-8"), String("strict")])
    def execute_encode_fp(self, exec_ctx):
        s = exec_ctx.symbol_table.get("s")
        encoding = exec_ctx.symbol_table.get("encoding")
        errors = exec_ctx.symbol_table.get("errors")
        if not isinstance(s, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'encode' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(encoding, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'encode' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(errors, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'encode' must be a string",
                    exec_ctx,
                )
            )
        try:
            encoded = s.value.encode(encoding.value, errors.value)
            return RTResult().success(Bytes(encoded))
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to encode string: {e}",
                    exec_ctx,
                )
            )

    @set_args(["value"])
    def execute_is_py_obj(self, exec_ctx):
        is_py_obj = isinstance(exec_ctx.symbol_table.get("value"), PyObject)
        return RTResult().success(Number.true if is_py_obj else Number.false)

    @set_args(["value"])
    def execute_is_nan(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        if not isinstance(value, Number):
            return RTResult().success(Number.false)
        if math.isnan(value.value):
            return RTResult().success(Number.true)
        else:
            return RTResult().success(Number.false)

    @set_args(["value"])
    def execute_parse_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        if not isinstance(value, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'parse' must be a string",
                    exec_ctx,
                )
            )
        try:
            parsed = json.loads(value.value)
            return RTResult().success(self.validate_pyexec_result(parsed))
        except json.JSONDecodeError as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to parse JSON: {e}",
                    exec_ctx,
                )
            )

    @set_args(["value"])
    def execute_stringify_fp(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        try:
            stringified = json.dumps(self.convert_zer_to_py(value))
            return RTResult().success(String(stringified))
        except (TypeError, OverflowError) as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to stringify to JSON: {e}",
                    exec_ctx,
                )
            )

    @set_args(["channel", "value"])
    def execute_channel_send_fp(self, exec_ctx):
        channel = exec_ctx.symbol_table.get("channel")
        value = exec_ctx.symbol_table.get("value")
        if not isinstance(channel, Channel):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'send' must be a channel",
                    exec_ctx,
                )
            )

        channel.queue.put(value)
        return RTResult().success(Number.none)

    @set_args(["channel"])
    def execute_channel_receive_fp(self, exec_ctx):
        channel = exec_ctx.symbol_table.get("channel")
        if not isinstance(channel, Channel):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'recv' must be a channel",
                    exec_ctx,
                )
            )

        try:
            value = channel.queue.get()
            return RTResult().success(value)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error receiving from channel: {e}",
                    exec_ctx,
                )
            )

    @set_args(["channel"])
    def execute_channel_is_empty_fp(self, exec_ctx):
        channel = exec_ctx.symbol_table.get("channel")
        if not isinstance(channel, Channel):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'is_empty' must be a channel",
                    exec_ctx,
                )
            )
        return RTResult().success(Bool(channel.queue.empty()))

    @set_args([])
    def execute_channel_new_fp(self, _):
        channel = Channel(PyQueue())
        return RTResult().success(channel)

    @set_args(
        ["value1", "value2", "rel_tol", "abs_tol"],
        [None, None, Number(1e-9), Number(0.0)],
    )
    def execute_is_close_fp(self, exec_ctx):
        v1 = exec_ctx.symbol_table.get("value1").value
        v2 = exec_ctx.symbol_table.get("value2").value
        rel_tol = exec_ctx.symbol_table.get("rel_tol").value
        abs_tol = exec_ctx.symbol_table.get("abs_tol").value

        return RTResult().success(
            Bool(math.isclose(v1, v2, rel_tol=rel_tol, abs_tol=abs_tol))
        )

    @set_args(["value"])
    def execute_is_channel(self, exec_ctx):
        is_channel = isinstance(exec_ctx.symbol_table.get("value"), Channel)
        return RTResult().success(Number.true if is_channel else Number.false)

    @set_args(["value"])
    def execute_is_cfloat(self, exec_ctx):
        is_cfloat = isinstance(exec_ctx.symbol_table.get("value"), CFloat)
        return RTResult().success(Number.true if is_cfloat else Number.false)

    @set_args(["value", "supress_error"], [None, Bool.false])
    def execute_to_cfloat(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        supress_error = exec_ctx.symbol_table.get("supress_error")

        if not isinstance(supress_error, Bool):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'to_cfloat' must be a boolean",
                    exec_ctx,
                )
            )

        supress_error_ = bool(supress_error.value)

        try:
            if isinstance(value, CFloat):
                result = CFloat(value.value)
                return RTResult().success(result)

            elif isinstance(value, Number):
                decimal_value = Fraction(str(value.value))
                result = CFloat(decimal_value)
                return RTResult().success(result)

            elif isinstance(value, String):
                decimal_value = Fraction(value.value)
                result = CFloat(decimal_value)
                return RTResult().success(result)

            else:
                if supress_error_:
                    result = CFloat(Fraction("0"))
                    return RTResult().success(result)
                else:
                    return RTResult().failure(
                        RTError(
                            self.pos_start,
                            self.pos_end,
                            f"Cannot convert '{value.type()}' to decimal",
                            exec_ctx,
                        )
                    )

        except (ValueError, TypeError) as e:
            if supress_error_:
                result = CFloat(Fraction("0"))
                return RTResult().success(result)
            else:
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        f"Failed to convert to decimal: {str(e)}",
                        exec_ctx,
                    )
                )

    @set_args(["value"])
    def execute_is_coroutine(self, exec_ctx):
        is_coroutine = isinstance(exec_ctx.symbol_table.get("value"), Coroutine)
        return RTResult().success(Number.true if is_coroutine else Number.false)

    async def _run_interpreter_coro(self, coro_obj, context):
        res = RTResult()
        interpreter = Interpreter()

        func = coro_obj.func
        exec_ctx = func.generate_new_context()

        if isinstance(func, Function):
            res.register(
                await func.handle_arguments(
                    func.arg_names,
                    func.defaults,
                    func.vargs_name,
                    func.kargs_name,
                    coro_obj.positional_args,
                    coro_obj.keyword_args,
                    exec_ctx,
                )
            )
            if res.should_return():
                return res

            value = res.register(await interpreter.visit(func.body_node, exec_ctx))
            if res.should_return() and res.func_return_value is None:
                return res

            ret_value = (
                (value if func.should_auto_return else None)
                or res.func_return_value
                or Number.none
            )
            return res.success(ret_value)

        elif isinstance(func, BuiltInFunction):
            method_name = f"execute_{func.name}"
            method = getattr(func, method_name, func.no_execute_method)

            res.register(
                await func.handle_arguments(
                    param_names=method.arg_names,
                    defaults=method.defaults,
                    vargs_name=None,
                    kargs_name=None,
                    positional_args=coro_obj.positional_args,
                    keyword_args=coro_obj.keyword_args,
                    exec_ctx=exec_ctx,
                )
            )
            if res.should_return():
                return res

            return_value = res.register(await method(exec_ctx))
            if res.should_return():
                return res

            return res.success(return_value)

        return RTResult().failure(
            TError(
                coro_obj.pos_start,
                coro_obj.pos_end,
                "Object is not a valid coroutine function",
                context,
            )
        )

    @set_args(["coroutines"])
    async def execute_gather_fp(self, exec_ctx):
        coroutines_list = exec_ctx.symbol_table.get("coroutines")

        if not isinstance(coroutines_list, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'gather' must be a list",
                    exec_ctx,
                )
            )

        tasks = []
        for i, coro_obj in enumerate(coroutines_list.value):
            if not isinstance(coro_obj, Coroutine):
                return RTResult().failure(
                    TError(
                        self.pos_start,
                        self.pos_end,
                        f"All items in the list passed to 'gather' must be coroutines. Item at index {i} is a {coro_obj.type()}.",
                        exec_ctx,
                    )
                )
            tasks.append(self._run_interpreter_coro(coro_obj, exec_ctx))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results = []
        for res in results:
            if isinstance(res, BaseException):
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        f"A concurrent task failed with a Python exception: {res}",
                        exec_ctx,
                    )
                )

            if res.error:
                return res

            final_results.append(res.value)

        return RTResult().success(List(final_results))

    @set_args(["coroutine", "ms"])
    async def execute_timeout_fp(self, exec_ctx):
        coro_obj = exec_ctx.symbol_table.get("coroutine")
        ms = exec_ctx.symbol_table.get("ms")

        if not isinstance(coro_obj, Coroutine):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'timeout' must be a coroutine",
                    exec_ctx,
                )
            )

        if not isinstance(ms, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'timeout' must be a number",
                    exec_ctx,
                )
            )

        try:
            result = await asyncio.wait_for(
                self._run_interpreter_coro(coro_obj, exec_ctx),
                timeout=ms.value / 1000.0,
            )
            return result
        except asyncio.TimeoutError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Coroutine timed out after {ms.value}ms",
                    exec_ctx,
                )
            )

    @set_args(["coroutines", "ms"])
    async def execute_timeouts_fp(self, exec_ctx):
        coroutines_list = exec_ctx.symbol_table.get("coroutines")
        ms = exec_ctx.symbol_table.get("ms")

        if not isinstance(coroutines_list, List):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'timeouts' must be a list",
                    exec_ctx,
                )
            )

        if not isinstance(ms, Number):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'timeouts' must be a number",
                    exec_ctx,
                )
            )

        tasks = []
        for i, coro_obj in enumerate(coroutines_list.value):
            if not isinstance(coro_obj, Coroutine):
                return RTResult().failure(
                    TError(
                        self.pos_start,
                        self.pos_end,
                        f"All items in the list passed to 'timeouts' must be coroutines",
                        exec_ctx,
                    )
                )
            tasks.append(
                asyncio.wait_for(
                    self._run_interpreter_coro(coro_obj, exec_ctx),
                    timeout=ms.value / 1000.0,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results = []
        for res in results:
            if isinstance(res, asyncio.TimeoutError):
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        f"A coroutine timed out after {ms.value}ms",
                        exec_ctx,
                    )
                )
            if isinstance(res, BaseException):
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        f"A concurrent task failed with exception: {res}",
                        exec_ctx,
                    )
                )
            if res.error:
                return res
            final_results.append(res.value)

        return RTResult().success(List(final_results))

    @set_args(["file", "mode", "text"])
    async def execute_async_write_fp(self, exec_ctx):
        file, mode, text = (
            exec_ctx.symbol_table.get(arg) for arg in ["file", "mode", "text"]
        )
        try:
            import aiofiles  # type: ignore

            async with aiofiles.open(
                file.value,
                mode=mode.value,
                encoding="utf-8" if "b" not in mode.value else None,
            ) as f:
                await f.write(text.value)
            return RTResult().success(NoneObject.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "aiofiles module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to write to file: {e}",
                    exec_ctx,
                )
            )

    @set_args(["file", "mode"])
    async def execute_async_read_fp(self, exec_ctx):
        file, mode = (exec_ctx.symbol_table.get(arg) for arg in ["file", "mode"])
        try:
            import aiofiles  # type: ignore

            async with aiofiles.open(
                file.value,
                mode=mode.value,
                encoding="utf-8" if "b" not in mode.value else None,
            ) as f:
                content = await f.read()
            return RTResult().success(
                Bytes(content) if "b" in mode.value else String(content)
            )
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "aiofiles module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                IError(
                    self.pos_start, self.pos_end, f"Failed to read file: {e}", exec_ctx
                )
            )

    @set_args(["src", "dst"])
    async def execute_async_copy_fp(self, exec_ctx):
        src, dst = (exec_ctx.symbol_table.get(arg) for arg in ["src", "dst"])
        try:
            await asyncio.to_thread(copy, src.value, dst.value)
            return RTResult().success(NoneObject.none)
        except Exception as e:
            return RTResult().failure(
                IError(
                    self.pos_start, self.pos_end, f"Failed to copy file: {e}", exec_ctx
                )
            )

    @set_args(["top"])
    async def execute_async_walk_fp(self, exec_ctx):
        top_path = exec_ctx.symbol_table.get("top")
        try:
            walk_generator = await asyncio.to_thread(os.walk, top_path.value)
            walk_results = []
            for root, dirs, files in walk_generator:
                walk_results.append(
                    List(
                        [
                            String(root),
                            List([String(d) for d in dirs]),
                            List([String(f) for f in files]),
                        ]
                    )
                )
            return RTResult().success(List(walk_results))
        except Exception as e:
            return RTResult().failure(
                IError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed during directory walk: {e}",
                    exec_ctx,
                )
            )

    @set_args(
        ["url", "method", "headers", "data", "timeout"],
        [None, String("GET"), HashMap({}), HashMap({}), Number(15)],
    )
    async def execute_async_request_fp(self, exec_ctx):
        url, method, headers, data, timeout = (
            exec_ctx.symbol_table.get(arg)
            for arg in ["url", "method", "headers", "data", "timeout"]
        )
        try:
            import aiohttp  # type: ignore

            py_headers = self.convert_zer_to_py(headers)
            py_data = self.convert_zer_to_py(data)
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method.value,
                    url.value,
                    headers=py_headers,
                    data=py_data,
                    timeout=timeout.value,
                ) as resp:
                    resp.raise_for_status()
                    json_response = await resp.json()
                    return RTResult().success(
                        self.validate_pyexec_result(json_response)
                    )
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "aiohttp module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args(["url", "timeout"], [None, Number(15)])
    async def execute_async_downl_fp(self, exec_ctx):
        url, timeout = (exec_ctx.symbol_table.get(arg) for arg in ["url", "timeout"])
        try:
            import aiohttp  # type: ignore
            import aiofiles  # type: ignore

            async with aiohttp.ClientSession(
                headers={"User-Agent": "Mozilla/5.0"}
            ) as session:
                async with session.get(url.value, timeout=timeout.value) as response:
                    response.raise_for_status()
                    filename = (
                        os.path.basename(unquote(response.url.path)) or "download"
                    )
                    async with aiofiles.open(filename, mode="wb") as f:
                        await f.write(await response.read())
                    return RTResult().success(String(os.path.abspath(filename)))
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "aiofiles or aiohttp module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start, self.pos_end, f"Failed to download: {e}", exec_ctx
                )
            )

    @set_args(["command"])
    async def execute_async_system_fp(self, exec_ctx):
        cmd = exec_ctx.symbol_table.get("command")
        proc = await asyncio.create_subprocess_shell(cmd.value)
        await proc.wait()
        return RTResult().success(Number(proc.returncode))

    @set_args(["command"])
    async def execute_async_osystem_fp(self, exec_ctx):
        cmd = exec_ctx.symbol_table.get("command")
        proc = await asyncio.create_subprocess_shell(
            cmd.value, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return RTResult().success(
            List(
                [
                    String(stdout.decode(errors="ignore")),
                    String(stderr.decode(errors="ignore")),
                    Number(proc.returncode),
                ]
            )
        )

    @set_args(["key"])
    async def execute_async_keyboard_wait_fp(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")
        try:
            import keyboard  # type: ignore

            await asyncio.to_thread(keyboard.wait, key.value)
            return RTResult().success(NoneObject.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "keyboard module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args(["path"])
    async def execute_async_screen_capture_fp(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        try:
            import pyautogui  # type: ignore

            await asyncio.to_thread(pyautogui.screenshot, path.value)
            return RTResult().success(NoneObject.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "pyautogui module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args(["x", "y", "w", "h", "path"])
    async def execute_async_screen_capture_area_fp(self, exec_ctx):
        x, y, w, h, p = (
            exec_ctx.symbol_table.get(arg) for arg in ["x", "y", "w", "h", "p"]
        )
        try:
            import pyautogui  # type: ignore

            bbox = (int(x.value), int(y.value), int(w.value), int(h.value))
            await asyncio.to_thread(pyautogui.screenshot, p.value, region=bbox)
            return RTResult().success(NoneObject.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "pyautogui module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args([])
    def execute_channel_new_fp(self, _):
        return RTResult().success(Channel(asyncio.Queue()))

    @set_args(["channel", "value"])
    async def execute_async_channel_send_fp(self, exec_ctx):
        channel, value = (
            exec_ctx.symbol_table.get(arg) for arg in ["channel", "value"]
        )
        if not isinstance(channel, Channel):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'channel_send' must be a channel",
                    exec_ctx,
                )
            )
        await channel.value.put(value)
        return RTResult().success(NoneObject.none)

    @set_args(["channel"])
    async def execute_async_channel_receive_fp(self, exec_ctx):
        channel = exec_ctx.symbol_table.get("channel")
        if not isinstance(channel, Channel):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'channel_receive' must be a channel",
                    exec_ctx,
                )
            )
        value = await channel.value.get()
        return RTResult().success(value)

    @set_args([])
    async def execute_async_get_ip_fp(self, exec_ctx):
        try:
            import aiohttp  # type: ignore

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api64.ipify.org?format=json", timeout=5
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return RTResult().success(String(data["ip"]))
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "aiohttp module not available",
                    exec_ctx,
                )
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to retrieve public IP address: {e}",
                    exec_ctx,
                )
            )

    @set_args(["host"])
    async def execute_async_ping_fp(self, exec_ctx):
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

        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", host.value]

        try:
            proc = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()

            if proc.returncode == 0:
                return RTResult().success(Bool(True))
            else:
                return RTResult().success(Bool(False))
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error while pinging host: {e}",
                    exec_ctx,
                )
            )

    @set_args(["dir_path"], [String(".")])
    async def execute_async_list_dir_fp(self, exec_ctx):
        dir_path = exec_ctx.symbol_table.get("dir_path")
        try:
            is_dir = await asyncio.to_thread(os.path.isdir, dir_path.value)
            if not is_dir:
                raise FileNotFoundError(f"Directory not found: '{dir_path.value}'")

            items = await asyncio.to_thread(os.listdir, dir_path.value)
            return RTResult().success(List([String(item) for item in items]))
        except Exception as e:
            return RTResult().failure(
                IError(self.pos_start, self.pos_end, str(e), exec_ctx)
            )

    @set_args(["value"], [String("")])
    async def execute_async_println_fp(self, exec_ctx):
        try:
            import aioconsole  # type: ignore

            if isinstance(exec_ctx.symbol_table.get("value"), String):
                await aioconsole.aprint(
                    exec_ctx.symbol_table.get("value").value, flush=True
                )
            else:
                await aioconsole.aprint(
                    repr(exec_ctx.symbol_table.get("value")), flush=True
                )
            return RTResult().success(NoneObject.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "aioconsole module not available",
                    exec_ctx,
                )
            )

    @set_args(["value"], [String("")])
    async def execute_async_print_fp(self, exec_ctx):
        try:
            import aioconsole  # type: ignore

            if isinstance(exec_ctx.symbol_table.get("value"), String):
                await aioconsole.aprint(
                    exec_ctx.symbol_table.get("value").value, flush=True, end=""
                )
            else:
                await aioconsole.aprint(
                    repr(exec_ctx.symbol_table.get("value")), flush=True, end=""
                )
            return RTResult().success(NoneObject.none)
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "aioconsole module not available",
                    exec_ctx,
                )
            )

    @set_args(["prompt"], [String("")])
    async def execute_async_input_fp(self, exec_ctx):
        try:
            import aioconsole  # type: ignore

            text = await aioconsole.aprint(
                exec_ctx.symbol_table.get("value").value, flush=True
            )
            return RTResult().success(String(text))
        except ImportError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "aioconsole module not available",
                    exec_ctx,
                )
            )

    @set_args(["prompt"], [String("")])
    async def execute_async_get_password_fp(self, exec_ctx):
        from getpass import getpass

        prompt = exec_ctx.symbol_table.get("prompt").value
        password = await asyncio.to_thread(getpass, prompt)
        return RTResult().success(String(password))

    @set_args([])
    async def execute_async_clear_fp(self, _):
        command = "cls" if os.name == "nt" else "clear"
        proc = await asyncio.create_subprocess_shell(command)
        await proc.wait()
        return RTResult().success(NoneObject.none)

    @set_args(["code", "args"], [None, HashMap({})])
    async def execute_async_pyexec_fp(self, exec_ctx):
        code = exec_ctx.symbol_table.get("code")
        args = exec_ctx.symbol_table.get("args")

        if not isinstance(code, String):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'pyexec' must be a string",
                    exec_ctx,
                )
            )
        if not isinstance(args, HashMap):
            return RTResult().failure(
                TError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'pyexec' must be a hashmap",
                    exec_ctx,
                )
            )

        try:
            local_env = self.convert_zer_to_py(args)

            def run_exec():
                exec(code.value, {}, local_env)
                return local_env

            final_env = await asyncio.to_thread(run_exec)
            result = self.validate_pyexec_result(final_env)
            return RTResult().success(result)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Error executing Python code: {e}",
                    exec_ctx,
                )
            )


for method_name in [m for m in dir(BuiltInFunction) if m.startswith("execute_")]:
    func_name = method_name[8:]
    method = getattr(BuiltInFunction, method_name)
    if hasattr(method, "arg_names"):
        setattr(BuiltInFunction, func_name, BuiltInFunction(func_name))
        BUILTIN_FUNCTIONS.append(func_name)


class Interpreter:
    def __init__(self):
        self.visit_table = {}
        for attr_name in dir(self):
            if attr_name.startswith("visit_") and attr_name != "visit":
                method = getattr(self, attr_name)
                if callable(method):
                    node_type = attr_name[len("visit_") :]
                    self.visit_table[node_type] = method

    async def visit(self, node, context):
        node_type = type(node).__name__
        method = self.visit_table.get(node_type)
        if method is None:
            raise Exception(f"No visit method defined for {node_type}")
        return await method(node, context)

    async def visit_AwaitNode(self, node, context):
        res = RTResult()
        value_to_await = res.register(await self.visit(node.node_to_await, context))
        if res.should_return():
            return res

        if not isinstance(value_to_await, Coroutine):
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    "Object is not awaitable",
                    context,
                )
            )

        coro = value_to_await
        func = coro.func
        exec_ctx = func.generate_new_context()

        if isinstance(func, Function):
            interpreter = Interpreter()
            res.register(
                await func.handle_arguments(
                    func.arg_names,
                    func.defaults,
                    func.vargs_name,
                    func.kargs_name,
                    coro.positional_args,
                    coro.keyword_args,
                    exec_ctx,
                )
            )
            if res.should_return():
                return res

            value = res.register(await interpreter.visit(func.body_node, exec_ctx))
            if res.should_return() and res.func_return_value is None:
                return res

            ret_value = (
                (value if func.should_auto_return else None)
                or res.func_return_value
                or Number.none
            )
            return res.success(ret_value)

        elif isinstance(func, BuiltInFunction):
            method_name = f"execute_{func.name}"
            method = getattr(func, method_name, func.no_execute_method)

            res.register(
                await func.handle_arguments(
                    param_names=method.arg_names,
                    defaults=method.defaults,
                    vargs_name=None,
                    kargs_name=None,
                    positional_args=coro.positional_args,
                    keyword_args=coro.keyword_args,
                    exec_ctx=exec_ctx,
                )
            )
            if res.should_return():
                return res

            return_value = None
            if asyncio.iscoroutinefunction(method):
                return_value = res.register(await method(exec_ctx))
            else:
                return_value = res.register(method(exec_ctx))

            if res.should_return():
                return res

            return res.success(return_value)

    async def visit_NumberNode(self, node, context: Context):
        return RTResult().success(
            Number(node.tok.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    async def visit_StringNode(self, node, context: Context):
        return RTResult().success(
            String(node.tok.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    async def visit_ListNode(self, node, context: Context):
        res = RTResult()
        value = []
        for element_node in node.element_nodes:
            value.append(res.register(await self.visit(element_node, context)))
            if res.should_return():
                return res
        return res.success(
            List(value).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    async def visit_VarAccessNode(self, node, context: Context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = None

        if var_name in context.nonlocal_vars:
            value = context.parent.symbol_table.get(var_name)
        elif var_name in context.using_vars:
            global_st = context.symbol_table
            while global_st.parent:
                global_st = global_st.parent
            value = global_st.get(var_name)
        else:
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

        if not isinstance(value, (NameSpace, List, HashMap)):
            copied_value = value.copy()
        else:
            copied_value = value

        copied_value = copied_value.set_pos(node.pos_start, node.pos_end).set_context(
            context
        )
        return res.success(copied_value)

    async def visit_VarAssignNode(self, node, context: Context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = res.register(await self.visit(node.value_node, context))
        if res.should_return():
            return res

        if var_name in context.using_vars:
            global_symbol_table = context.symbol_table
            while global_symbol_table.parent:
                global_symbol_table = global_symbol_table.parent
            global_symbol_table.set(var_name, value)

        elif var_name in context.nonlocal_vars:
            context.parent.symbol_table.set(var_name, value)

        else:
            context.symbol_table.set(var_name, value)

        context.private_symbol_table.set(var_name, value)

        return res.success(value)

    async def visit_VarAssignAsNode(self, node, context: Context):
        res = RTResult()
        orig_name = node.var_name_tok.value
        alias_name = node.var_name_tok2.value

        value = context.symbol_table.get(orig_name)
        if value is None:
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Variable '{orig_name}' is not defined",
                    context,
                )
            )

        context.symbol_table.set(alias_name, value)
        context.private_symbol_table.set(alias_name, value)

        try:
            context.symbol_table.remove(orig_name)
            context.private_symbol_table.remove(orig_name)
        except KeyError:
            pass

        return res.success(value)

    async def initialize_namespace(self, namespace_obj):
        if namespace_obj.get("initialized_", checked=True).value:
            return
        stmts = namespace_obj.get("statements_", checked=True)
        ns_context = namespace_obj.get("context_", checked=True)
        for stmt in stmts:
            _ = await self.visit(stmt, ns_context)
        for k, v in ns_context.symbol_table.symbols.items():
            namespace_obj.set(k, v)
        for k, v in ns_context.private_symbol_table.symbols.items():
            namespace_obj.set(k, v)
        namespace_obj.set("initialized_", Number.true, checked=True)

    async def visit_NameSpaceNode(self, node, context):
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
        namespace.set("statements_", stmts, checked=True)
        namespace.set("context_", ns_context, checked=True)
        context.symbol_table.set(node.namespace_name, namespace)
        context.private_symbol_table.set(node.namespace_name, namespace)
        return res.success(namespace)

    async def visit_MemberAccessNode(self, node, context):
        res = RTResult()
        obj = res.register(await self.visit(node.object_node, context))
        if res.should_return():
            return res
        if not isinstance(obj, NameSpace):
            return res.failure(
                TError(
                    node.pos_start,
                    node.pos_end,
                    "Illegal operation -> unknown",
                    context,
                )
            )
        if (
            isinstance(obj, NameSpace)
            and not obj.get("initialized_", checked=True).value
        ):
            await self.initialize_namespace(obj)
        member = obj.get(node.member_name)
        if member is None:
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    f"'{obj}' has no member '{node.member_name}'",
                    context,
                )
            )
        if isinstance(member, Error):
            return res.failure(member)
        return res.success(member)

    async def visit_BinOpNode(self, node, context):
        res = RTResult()
        left = res.register(await self.visit(node.left_node, context))
        if res.should_return():
            return res
        right = res.register(await self.visit(node.right_node, context))
        if res.should_return():
            return res

        op_type = node.op_tok.type

        if op_type == TT_COMMA:
            if isinstance(left, List):
                if isinstance(right, List):
                    left.value.extend(right.value)
                else:
                    left.value.append(right)
                result = left
            elif isinstance(right, List):
                right.value.insert(0, left)
                result = right
            else:
                result = List([left, right])
            return res.success(result.set_pos(node.pos_start, node.pos_end))

        if isinstance(left, Number) and isinstance(right, Number):
            if op_type == TT_PLUS:
                result = Number(left.value + right.value)
            elif op_type == TT_MINUS:
                result = Number(left.value - right.value)
            elif op_type == TT_MUL:
                result = Number(left.value * right.value)
            elif op_type == TT_DIV:
                if right.value == 0:
                    return res.failure(
                        MError(
                            right.pos_start, right.pos_end, "Division by zero", context
                        )
                    )
                result = Number(left.value / right.value)
            elif op_type == TT_MOD:
                if right.value == 0:
                    return res.failure(
                        MError(
                            right.pos_start, right.pos_end, "Division by zero", context
                        )
                    )
                result = Number(left.value % right.value)
            elif op_type == TT_FLOORDIV:
                if right.value == 0:
                    return res.failure(
                        MError(
                            right.pos_start, right.pos_end, "Division by zero", context
                        )
                    )
                result = Number(left.value // right.value)
            elif op_type == TT_POW:
                result = Number(left.value**right.value)
            else:
                result, error = getattr(
                    left,
                    {
                        TT_EE: "get_comparison_eq",
                        TT_NE: "get_comparison_ne",
                        TT_LT: "get_comparison_lt",
                        TT_GT: "get_comparison_gt",
                        TT_LTE: "get_comparison_lte",
                        TT_GTE: "get_comparison_gte",
                    }.get(op_type),
                )(right)
                if error:
                    return res.failure(error)
            return res.success(result.set_pos(node.pos_start, node.pos_end))

        if isinstance(left, CFloat) and isinstance(right, CFloat):
            if op_type == TT_PLUS:
                result = CFloat(left.value + right.value)
            elif op_type == TT_MINUS:
                result = CFloat(left.value - right.value)
            elif op_type == TT_MUL:
                result = CFloat(left.value * right.value)
            elif op_type == TT_DIV:
                if right.value == 0:
                    return res.failure(
                        MError(
                            right.pos_start, right.pos_end, "Division by zero", context
                        )
                    )
                result = CFloat(left.value / right.value)
            elif op_type == TT_MOD:
                if right.value == 0:
                    return res.failure(
                        MError(
                            right.pos_start, right.pos_end, "Division by zero", context
                        )
                    )
                result = CFloat(left.value % right.value)
            elif op_type == TT_FLOORDIV:
                if right.value == 0:
                    return res.failure(
                        MError(
                            right.pos_start, right.pos_end, "Division by zero", context
                        )
                    )
                result = CFloat(left.value // right.value)
            elif op_type == TT_POW:
                result = CFloat(left.value**right.value)
            else:
                result, error = getattr(
                    left,
                    {
                        TT_EE: "get_comparison_eq",
                        TT_NE: "get_comparison_ne",
                        TT_LT: "get_comparison_lt",
                        TT_GT: "get_comparison_gt",
                        TT_LTE: "get_comparison_lte",
                        TT_GTE: "get_comparison_gte",
                    }.get(op_type),
                )(right)
                if error:
                    return res.failure(error)
            return res.success(result.set_pos(node.pos_start, node.pos_end))

        ops = {
            TT_PLUS: "added_to",
            TT_MINUS: "subbed_by",
            TT_MUL: "multed_by",
            TT_DIV: "dived_by",
            TT_POW: "powed_by",
            TT_MOD: "moduled_by",
            TT_EE: "get_comparison_eq",
            TT_NE: "get_comparison_ne",
            TT_LT: "get_comparison_lt",
            TT_GT: "get_comparison_gt",
            TT_LTE: "get_comparison_lte",
            TT_GTE: "get_comparison_gte",
            TT_FLOORDIV: "floordived_by",
            TT_DOLLAR: "dollared_by",
        }

        if op_type in ops:
            method = getattr(left, ops[op_type])
            result, error = method(right)
        elif node.op_tok.matches(TT_KEYWORD, "and"):
            result, error = left.anded_by(right)
        elif node.op_tok.matches(TT_KEYWORD, "or"):
            result, error = left.ored_by(right)
        else:
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Unknown binary operator '{node.op_tok}'",
                    context,
                )
            )

        if error:
            return res.failure(error)
        return res.success(result.set_pos(node.pos_start, node.pos_end))

    async def visit_UnaryOpNode(self, node, context):
        res = RTResult()
        value = res.register(await self.visit(node.node, context))
        if res.should_return():
            return res
        if isinstance(value, Number) and value.value is None:
            return res.failure(
                TError(
                    node.pos_start,
                    node.pos_end,
                    "Cannot perform arithmetic or logical operation on 'none'",
                    context,
                )
            )
        op_type = node.op_tok.type
        ops = {
            TT_MINUS: lambda x: x.multed_by(Number(-1)),
        }
        kw_ops = {
            "not": lambda x: x.notted(),
        }
        if op_type in ops:
            result, error = ops[op_type](value)
        elif node.op_tok.matches(TT_KEYWORD, "not"):
            result, error = kw_ops["not"](value)
        else:
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Unknown unary operator '{node.op_tok}'",
                    context,
                )
            )
        if error:
            return res.failure(error)
        return res.success(result.set_pos(node.pos_start, node.pos_end))

    async def visit_IfNode(self, node, context):
        res = RTResult()
        for condition, expr, should_return_none in node.cases:
            condition_value = res.register(await self.visit(condition, context))
            if res.should_return():
                return res
            if condition_value.is_true():
                expr_value = res.register(await self.visit(expr, context))
                if res.should_return():
                    return res
                return res.success(Number.none if should_return_none else expr_value)
        if node.else_case:
            expr, should_return_none = node.else_case
            expr_value = res.register(await self.visit(expr, context))
            if res.should_return():
                return res
            return res.success(Number.none if should_return_none else expr_value)
        return res.success(Number.none)

    async def visit_ForNode(self, node, context):
        res = RTResult()
        start_value = res.register(await self.visit(node.start_value_node, context))
        if res.should_return():
            return res
        end_value = res.register(await self.visit(node.end_value_node, context))
        if res.should_return():
            return res
        if node.step_value_node:
            step_value = res.register(await self.visit(node.step_value_node, context))
            if res.should_return():
                return res
        else:
            step_value = Number(1)
        start_int = start_value.value
        end_int = end_value.value
        step_int = step_value.value
        var_name = node.var_name_tok.value
        body_node = node.body_node
        elements = [] if not node.should_return_none else None
        loop_var = Number(0)
        context.symbol_table.set(var_name, loop_var)
        for i in range(start_int, end_int, step_int):
            loop_var.value = i
            value = res.register(await self.visit(body_node, context))
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
            if elements is not None:
                elements.append(value)
        return res.success(
            List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
            if elements is not None
            else Number.none
        )

    async def visit_WhileNode(self, node, context):
        res = RTResult()

        condition_node = node.condition_node
        body_node = node.body_node

        if node.should_return_none:
            elements = None
        else:
            elements = []

        while True:
            condition = res.register(await self.visit(condition_node, context))
            if res.should_return():
                return res

            if not condition.is_true():
                break

            value = res.register(await self.visit(body_node, context))

            if res.should_return():
                if res.loop_should_continue:
                    continue

                if res.loop_should_break:
                    break

                return res

            if elements is not None:
                elements.append(value)

        if elements is None:
            return res.success(Number.none)
        else:
            return res.success(
                List(elements)
                .set_context(context)
                .set_pos(node.pos_start, node.pos_end)
            )

    async def visit_FuncDefNode(self, node, context):
        res = RTResult()
        func_name = node.var_name_tok.value if node.var_name_tok else None
        body_node = node.body_node
        arg_names = [arg_name.value for arg_name in node.arg_name_toks]

        func_value = (
            Function(
                func_name,
                body_node,
                arg_names,
                node.defaults,
                node.vargs_name_tok,
                node.kargs_name_tok,
                node.should_auto_return,
                node.is_async,
            )
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

        if node.decorator_nodes:
            for deco_node in reversed(node.decorator_nodes):
                decorator = res.register(await self.visit(deco_node, context))
                if res.should_return():
                    return res
                wrapped_func = res.register(await decorator.execute([func_value], {}))
                if res.should_return():
                    return res
                func_value = wrapped_func

        if node.var_name_tok:
            context.symbol_table.set(func_name, func_value)

        return res.success(func_value)

    async def visit_CallNode(self, node, context):
        try:
            res = RTResult()
            value_to_call = res.register(await self.visit(node.node_to_call, context))
            if res.should_return():
                return res
            value_to_call = value_to_call.copy().set_pos(node.pos_start, node.pos_end)
            value_to_call.set_context(context)
            positional_args = []
            keyword_args = {}
            for arg_node in node.arg_nodes:
                if isinstance(arg_node, VargsUnpackNode):
                    list_to_unpack = res.register(
                        await self.visit(arg_node.node_to_unpack, context)
                    )
                    if res.should_return():
                        return res
                    if not isinstance(list_to_unpack, List):
                        return res.failure(
                            RTError(
                                arg_node.pos_start,
                                arg_node.pos_end,
                                "Value to unpack with * must be a list",
                                context,
                            )
                        )
                    positional_args.extend(list_to_unpack.value)
                elif isinstance(arg_node, KargsUnpackNode):
                    map_to_unpack = res.register(
                        await self.visit(arg_node.node_to_unpack, context)
                    )
                    if res.should_return():
                        return res
                    if not isinstance(map_to_unpack, HashMap):
                        return res.failure(
                            RTError(
                                arg_node.pos_start,
                                arg_node.pos_end,
                                "Value to unpack with ** must be a hashmap",
                                context,
                            )
                        )
                    for k, v in map_to_unpack.value.items():
                        if not isinstance(k, str):
                            return res.failure(
                                RTError(
                                    arg_node.pos_start,
                                    arg_node.pos_end,
                                    "Keyword argument keys must be strings",
                                    context,
                                )
                            )
                        keyword_args[k] = v

                elif isinstance(arg_node, VarAssignNode):
                    arg_name = arg_node.var_name_tok.value
                    arg_value = res.register(
                        await self.visit(arg_node.value_node, context)
                    )
                    if res.should_return():
                        return res
                    keyword_args[arg_name] = arg_value

                else:
                    positional_args.append(
                        res.register(await self.visit(arg_node, context))
                    )
                    if res.should_return():
                        return res

            return_value = res.register(
                await value_to_call.execute(positional_args, keyword_args)
            )
            if res.should_return():
                return res

            if return_value:
                return_value = (
                    return_value.copy()
                    .set_pos(node.pos_start, node.pos_end)
                    .set_context(context)
                )

            return res.success(return_value)

        except RecursionError:
            return RTResult().failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Maximum recursion depth exceeded ({sys.getrecursionlimit()})",
                    context,
                )
            )

    async def visit_ReturnNode(self, node, context):
        res = RTResult()
        if node.node_to_return:
            value = res.register(await self.visit(node.node_to_return, context))
            if res.should_return():
                return res
        else:
            value = Number.none
        return res.success_return(value)

    async def visit_ContinueNode(self, _, __):
        return RTResult().success_continue()

    async def visit_BreakNode(self, _, __):
        return RTResult().success_break()

    async def visit_LoadNode(self, node: LoadNode, context: Context):
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
        result, err = await load_module(path, self, context)
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

    async def visit_HashMapNode(self, node, context):
        res = RTResult()
        result = {}
        for key_node, value_node in node.pairs:
            key = res.register(await self.visit(key_node, context))
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
            val = res.register(await self.visit(value_node, context))
            if res.should_return():
                return res
            result[key.value] = val
        return res.success(HashMap(result))

    async def visit_ForInNode(self, node: ForInNode, context: Context) -> RTResult:
        res = RTResult()
        var_name = node.var_name_tok.value
        body = node.body_node
        should_return_none = node.should_return_none
        iterable = res.register(await self.visit(node.iterable_node, context))
        if res.should_return():
            return res
        iterator, error = iterable.iter()
        if error:
            return res.failure(error)
        e = []
        try:
            while True:
                current = next(iterator)
                context.symbol_table.set(var_name, current)
                value = res.register(await self.visit(body, context))
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
                    e.append(value)
        except StopIteration:
            pass
        if should_return_none:
            return res.success(Number.none)
        else:
            return res.success(
                List(value).set_context(context).set_pos(node.pos_start, node.pos_end)
            )

    async def visit_UsingNode(self, node, context: Context):
        res = RTResult()

        if not context.parent:
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    "'using' cannot be used at the global level",
                    context,
                )
            )

        global_symbol_table = context.symbol_table
        while global_symbol_table.parent:
            global_symbol_table = global_symbol_table.parent

        for var_tok in node.var_name_toks:
            var_name = var_tok.value
            if global_symbol_table.get(var_name) is None:
                return res.failure(
                    RTError(
                        var_tok.pos_start,
                        var_tok.pos_end,
                        f"Name '{var_name}' is not defined in the global scope",
                        context,
                    )
                )
            context.using_vars.add(var_name)

        return res.success(Number.none)

    async def visit_UsingParentNode(self, node, context: Context):
        res = RTResult()

        if not context.parent:
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    "'using parent' can only be used in a nested scope",
                    context,
                )
            )

        for var_tok in node.var_name_toks:
            var_name = var_tok.value
            if context.parent.symbol_table.get(var_name) is None:
                return res.failure(
                    RTError(
                        var_tok.pos_start,
                        var_tok.pos_end,
                        f"No binding for nonlocal variable '{var_name}' found",
                        context,
                    )
                )
            context.nonlocal_vars.add(var_name)

        return res.success(Number.none)

    async def visit_IndexAssignNode(self, node, context):
        res = RTResult()

        collection_obj = res.register(await self.visit(node.obj_node, context))
        if res.should_return():
            return res

        index_obj = res.register(await self.visit(node.index_node, context))
        if res.should_return():
            return res

        value_to_set = res.register(await self.visit(node.value_node, context))
        if res.should_return():
            return res

        if isinstance(collection_obj, List):
            if not isinstance(index_obj, Number):
                return res.failure(
                    RTError(
                        node.index_node.pos_start,
                        node.index_node.pos_end,
                        "List index must be a number",
                        context,
                    )
                )

            idx = int(index_obj.value)
            try:
                collection_obj.value[idx] = value_to_set
            except IndexError:
                return res.failure(
                    RTError(
                        node.index_node.pos_start,
                        node.index_node.pos_end,
                        f"Index {idx} is out of bounds for list of size {len(collection_obj.value)}",
                        context,
                    )
                )

        elif isinstance(collection_obj, HashMap):
            if not isinstance(index_obj, String):
                return res.failure(
                    RTError(
                        node.index_node.pos_start,
                        node.index_node.pos_end,
                        "Hashmap key must be a string",
                        context,
                    )
                )

            key = index_obj.value
            collection_obj.value[key] = value_to_set

        else:
            return res.failure(
                RTError(
                    node.obj_node.pos_start,
                    node.obj_node.pos_end,
                    "Indexed assignment can only be performed on a list or hashmap",
                    context,
                )
            )

        return res.success(value_to_set)

    async def visit_VargsUnpackNode(self, node, context):
        return RTResult().failure(
            RTError(
                node.pos_start,
                node.pos_end,
                "Vargs unpacking (*) can only be used in function calls",
                context,
            )
        )

    async def visit_KargsUnpackNode(self, node, context):
        return RTResult().failure(
            RTError(
                node.pos_start,
                node.pos_end,
                "Kargs unpacking (**) can only be used in function calls",
                context,
            )
        )

    async def visit_MultiAssignNode(self, node, context: Context):
        res = RTResult()
        var_names = [tok.value for tok in node.var_name_toks]

        value = res.register(await self.visit(node.value_node, context))
        if res.should_return():
            return res

        if not isinstance(value, List):
            return res.failure(
                TError(
                    node.value_node.pos_start,
                    node.value_node.pos_end,
                    "Value to unpack must be a list",
                    context,
                )
            )
        values_to_unpack = value.value
        if len(values_to_unpack) == 1 and isinstance(values_to_unpack[0], List):
            values_to_unpack = values_to_unpack[0].value

        if len(var_names) != len(values_to_unpack):
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    f"ValueError: not enough values to unpack (expected {len(var_names)}, got {len(values_to_unpack)})",
                    context,
                )
            )

        for i, var_name in enumerate(var_names):
            val_to_assign = values_to_unpack[i]
            context.symbol_table.set(var_name, val_to_assign)

        return res.success(Number.none)


global_symbol_table.set("argv_fp", List([String(e) for e in sys.argv[1:]]))
global_symbol_table.set("os_sep_fp", String(os.sep))
global_symbol_table.set("none", Number.none)
global_symbol_table.set("false", Number.false)
global_symbol_table.set("true", Number.true)
global_symbol_table.set("list", String("<list>"))
global_symbol_table.set("str", String("<str>"))
global_symbol_table.set("int", String("<int>"))
global_symbol_table.set("coroutine", String("<coroutine>"))
global_symbol_table.set("float", String("<float>"))
global_symbol_table.set("func", String("<func>"))
global_symbol_table.set("bool", String("<bool>"))
global_symbol_table.set("hashmap", String("<hashmap>"))
global_symbol_table.set("thread", String("<thread>"))
global_symbol_table.set("bytes", String("<bytes>"))
global_symbol_table.set("py_obj", String("<py-obj>"))
global_symbol_table.set("os_name_fp", String(os.name))
global_symbol_table.set("PI_fp", Number(math.pi))
global_symbol_table.set("E_fp", Number(math.e))
global_symbol_table.set("none_type", String("<none>"))
global_symbol_table.set("cfloat", String("<cfloat>"))
global_symbol_table.set("nan", Number(float("nan")))
global_symbol_table.set("inf", Number(float("inf")))
global_symbol_table.set("neg_inf", Number(float("-inf")))
global_symbol_table.set("channel_type", String("<channel>"))

for func in BUILTIN_FUNCTIONS:
    global_symbol_table.set(func, getattr(BuiltInFunction, func))

private_symbol_table = SymbolTable()
private_symbol_table.set("is_main", Number.false)


def clean_value(value):
    from .datatypes import List, String, NoneObject

    if isinstance(value, NoneObject):
        return String("")
    if isinstance(value, String) and value.value.strip().lower() == "none":
        return String("")
    if isinstance(value, List):
        if not hasattr(value, "value") or not isinstance(value.value, list):
            return String("")
        cleaned_value = [
            clean_value(elem)
            for elem in value.value
            if not (
                isinstance(elem, NoneObject)
                or (isinstance(elem, String) and elem.value.strip().lower() == "none")
            )
        ]
        if len(cleaned_value) == 0:
            return String("")
        if len(cleaned_value) == 1:
            single_elem = cleaned_value[0]
            if isinstance(single_elem, List):
                return single_elem
            if isinstance(single_elem, String):
                return String(single_elem.value)
        return List(cleaned_value)
    return value


def run(fn, text):
    async def async_run():
        lexer = Lexer(fn, text)
        tokens, error = lexer.make_tokens()
        if error:
            return None, error
        
        for i in tokens:
            print(i)

        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return None, ast.error

        interpreter = Interpreter()
        context = Context("<program>")
        context.symbol_table = global_symbol_table
        context.private_symbol_table = private_symbol_table
        context.private_symbol_table.set("is_main", Number.true)

        result = await interpreter.visit(ast.node, context)

        if fn == "<stdin>":
            value = result.value
            result.value = clean_value(value)
        else:
            result.value = ""

        return result.value, result.error

    try:
        loop = asyncio.get_event_loop()
        value, error = loop.run_until_complete(async_run())
        return value, error
    except (KeyboardInterrupt, EOFError):
        print(
            "\n---------------------------------------------------------------------------"
        )
        print(
            "InterruptError                            Traceback (most recent call last)\n"
        )
        print(
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}InterruptError{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}User Terminated{Fore.RESET}{Style.RESET_ALL}"
        )
        sys.exit(2)
    except OverflowError:
        print(
            "\n---------------------------------------------------------------------------"
        )
        print(
            "MemoryOverflowError                         Traceback (most recent call last)\n"
        )
        print(
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}MemoryOverflowError{Fore.RESET}{Style.RESET_ALL}: {Fore.MAGENTA}Memory Overflow{Fore.RESET}{Style.RESET_ALL}"
        )
        sys.exit(2)
