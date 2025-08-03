from .lexer import RTResult
import operator
from .errors import (
    TError,
    RTError,
    MError,
)


class Context:
    __slots__ = (
        "display_name",
        "parent",
        "parent_entry_pos",
        "symbol_table",
        "private_symbol_table",
    )

    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_pos = parent_entry_pos
        self.symbol_table = None
        self.private_symbol_table = None


class SymbolTable:
    __slots__ = ("symbols", "parent")

    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def get(self, name):
        value = self.symbols.get(name, None)
        if value == None and self.parent:
            return self.parent.get(name)
        return value

    def set(self, name, value):
        self.symbols[name] = value

    def change(self, other):
        self.symbols = other.symbols
        self.parent = other.parent

    def remove(self, name):
        del self.symbols[name]

    def exists(self, value):
        return True if value in self.symbols.value() else False

    def copy(self):
        return SymbolTable().change(self)


class Object:
    def __init__(self):
        self.set_pos()
        self.set_context()
        self.fields = []

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def type(self):
        return "Object"

    def added_to(self, other):
        return None, self.illegal_operation(other)

    def subbed_by(self, other):
        return None, self.illegal_operation(other)

    def multed_by(self, other):
        return None, self.illegal_operation(other)

    def dived_by(self, other):
        return None, self.illegal_operation(other)

    def moduled_by(self, other):
        return None, self.illegal_operation(other)

    def powed_by(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_eq(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_ne(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_lt(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_gt(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_lte(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_gte(self, other):
        return None, self.illegal_operation(other)

    def anded_by(self, other):
        return None, self.illegal_operation(other)

    def ored_by(self, other):
        return None, self.illegal_operation(other)

    def notted(self, other):
        return None, self.illegal_operation(other)

    def execute(self, _):
        return RTResult().failure(
            self.illegal_operation(error_str="Cannot call non-function")
        )

    def copy(self):
        raise Exception("No copy method defined")

    def is_true(self):
        return False

    def prequaled_by(self, other: "Object"):
        return None, self.illegal_operation(other)

    def get(self, other):
        return None, self.illegal_operation(other)

    def iter(self):
        return None, self.illegal_operation(
            error_str="Iteration is not supported for this type"
        )

    def illegal_operation(self, other=None, error_str=None):
        if not other:
            other = self
        return TError(
            self.pos_start,
            other.pos_end,
            f'Illegal operation -> {error_str or "unknown"}',
            self.context,
        )


class ThreadWrapper(Object):
    __slots__ = "thread"

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

    def type(self):
        return "<thread>"


class NoneObject(Object):
    __slots__ = "value"

    def __init__(self, value):
        super().__init__()
        self.value = value

    def added_to(self, other):
        return other, None

    def copy(self):
        copy = NoneObject(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def is_true(self):
        return False

    def __str__(self):
        return "none"

    def __repr__(self):
        return str(self.value)

    def type(self):
        return "<none>"

    def get_comparison_eq(self, other):
        if isinstance(other, NoneObject):
            return Bool(True).set_context(self.context), None
        return Bool(False).set_context(self.context), None

    def get_comparison_ne(self, other):
        if isinstance(other, NoneObject):
            return Bool(False).set_context(self.context), None
        return Bool(True).set_context(self.context), None

    def get_comparison_lt(self, _):
        return Bool(False).set_context(self.context), None

    def get_comparison_gt(self, _):
        return Bool(False).set_context(self.context), None

    def get_comparison_lte(self, other):
        if isinstance(other, NoneObject):
            return Bool(False).set_context(self.context), None
        return Bool(True).set_context(self.context), None

    def get_comparison_gte(self, other):
        if isinstance(other, NoneObject):
            return Bool(True).set_context(self.context), None
        return Bool(False).set_context(self.context), None


NoneObject.none = NoneObject("none")


class Bool(Object):
    __slots__ = ("value",)

    def __init__(self, value):
        super().__init__()
        self.value = bool(value)

    def copy(self):
        copy = Bool(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def is_true(self):
        return self.value

    def type(self):
        return "<bool>"

    def notted(self):
        return Bool(not self.value).set_context(self.context), None

    def anded_by(self, other):
        if not isinstance(other, Bool):
            return None, None
        return Bool(self.value and other.value).set_context(self.context), None

    def ored_by(self, other):
        if not isinstance(other, Bool):
            return None, None
        return Bool(self.value or other.value).set_context(self.context), None

    def _get_comparison_result(self, other, op):
        if (
            isinstance(other, Bool)
            and self.value is not None
            and other.value is not None
        ):
            result = bool(op(self.value, other.value))
            return Bool(result).set_context(self.context), None

        if self.value is None:
            if isinstance(other, NoneObject):
                result = op in (operator.eq, operator.le, operator.ge)
            else:
                result = op is operator.ne
            return Bool(result).set_context(self.context), None

        return Bool(op is operator.ne).set_context(self.context), None

    def get_comparison_eq(self, other):
        return self._get_comparison_result(other, operator.eq)

    def get_comparison_ne(self, other):
        return self._get_comparison_result(other, operator.ne)

    def __str__(self):
        return "true" if self.value else "false"

    def __repr__(self):
        return str(self).lower()


Bool.true = Bool(True)
Bool.false = Bool(False)


class Number(Object):
    __slots__ = ("value", "context", "pos_start", "pos_end", "fields")

    def __init__(self, value, context=None, pos_start=None, pos_end=None):
        self.value = value
        self.context = context
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.fields = []

    def copy(self):
        return Number(self.value, self.context, self.pos_start, self.pos_end)

    def added_to(self, other):
        if isinstance(other, Number):
            return Number(self.value + other.value).set_context(self.context), None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't add a number to a type of '{other.type()}'"
            )

    def subbed_by(self, other):
        if isinstance(other, Number):
            return Number(self.value - other.value).set_context(self.context), None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't subtract a number from a type of '{other.type()}'"
            )

    def multed_by(self, other):
        if isinstance(other, Number):
            return Number(self.value * other.value).set_context(self.context), None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't multiply a number by a type of '{other.type()}'"
            )

    def dived_by(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, RTError(
                    other.pos_start, other.pos_end, "Division by zero", self.context
                )

            return Number(self.value / other.value).set_context(self.context), None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't divide a number by a type of '{other.type()}'"
            )

    def moduled_by(self, other):
        if isinstance(other, Number):
            return Number(self.value % other.value).set_context(self.context), None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't mod a number by a type of '{other.type()}'"
            )

    def powed_by(self, other):
        if isinstance(other, Number):
            return Number(self.value**other.value).set_context(self.context), None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't power a number by a type of '{other.type()}'"
            )

    def floordived_by(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, MError(
                    other.pos_start, other.pos_end, "Division by zero", self.context
                )
            if other.value == 1:
                return self, None
            return Number(self.value // other.value).set_context(self.context), None
        else:
            return None, Object.illegal_operation(
                self,
                other,
                f"Can't floor divide a number by a type of '{other.type()}'",
            )

    def _get_comparison_result(self, other, op):
        if (
            isinstance(other, Number)
            and self.value is not None
            and other.value is not None
        ):
            result = bool(op(self.value, other.value))
            return Bool(result).set_context(self.context), None

        if self.value is None:
            if isinstance(other, NoneObject):
                result = op in (operator.eq, operator.le, operator.ge)
            else:
                result = op is operator.ne
            return Bool(result).set_context(self.context), None

        return Bool(op is operator.ne).set_context(self.context), None

    def get_comparison_eq(self, other):
        return self._get_comparison_result(other, operator.eq)

    def get_comparison_ne(self, other):
        return self._get_comparison_result(other, operator.ne)

    def get_comparison_lt(self, other):
        return self._get_comparison_result(other, operator.lt)

    def get_comparison_gt(self, other):
        return self._get_comparison_result(other, operator.gt)

    def get_comparison_lte(self, other):
        return self._get_comparison_result(other, operator.le)

    def get_comparison_gte(self, other):
        return self._get_comparison_result(other, operator.ge)

    def anded_by(self, other):
        if not isinstance(other, Number):
            return None, Object.illegal_operation(
                self, other, f"Can't compare a number to a type of '{other.type()}'"
            )
        if self.value is None or other.value is None:
            return None, TError(
                self.pos_start,
                self.pos_end,
                "Cannot perform logical operation with 'none'",
                self.context,
            )
        return (
            Bool((self.value != 0) & (other.value != 0)).set_context(self.context),
            None,
        )

    def ored_by(self, other):
        if not isinstance(other, Number):
            return None, Object.illegal_operation(
                self, other, f"Can't compare a number to a type of '{other.type()}'"
            )
        if self.value is None or other.value is None:
            return None, TError(
                self.pos_start,
                self.pos_end,
                "Cannot perform logical operation with 'none'",
                self.context,
            )
        return (
            Number((self.value != 0) | (other.value != 0)).set_context(self.context),
            None,
        )

    def notted(self):
        if self.value is None:
            return None, TError(
                self.pos_start,
                self.pos_end,
                "Cannot perform logical operation with 'none'",
                self.context,
            )
        return Number(self.value * -1).set_context(self.context), None

    def copy(self):
        copy = Number(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def is_true(self):
        return bool(self.value) if self.value is not None else False

    def type(self):
        if self.value % 1 == 0:
            return "<int>"
        else:
            return "<float>"

    def __str__(self):
        if self.value is None:
            return "none"
        if isinstance(self, Bool):
            return "false" if not self.value else "true"
        if str(self.value).find("e") != -1 or str(self.value).find("E") != -1:
            return str(self.value).replace("e", "*10^(").replace("E", "*10^(") + ")"
        return str(self.value)

    def __repr__(self):
        if self.value is None:
            return "none"
        if isinstance(self.value, Bool):
            return "false" if not self.value else "true"
        if str(self.value).find("e") != -1 or str(self.value).find("E") != -1:
            return str(self.value).replace("e", "*10^(").replace("E", "*10^(") + ")"
        return str(self.value)


Number.false = Bool.false
Number.true = Bool.true
Number.none = NoneObject.none


class String(Object):
    __slots__ = "value"

    def __init__(self, value):
        super().__init__()
        self.value = value
        self.fields = ["size"]

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def added_to(self, other):
        if isinstance(other, String):
            return String(self.value + other.value).set_context(self.context), None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't add a string to a type of '{other.type()}'"
            )

    def multed_by(self, other):
        if isinstance(other, Number):
            return String(self.value * other.value).set_context(self.context), None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't multiply a string by a type of '{other.type()}'"
            )

    def _make_comparison(self, other, op, type_to_check):
        if isinstance(other, type_to_check):
            result = bool(op(self.value, other.value))
            return Bool(result).set_context(self.context), None
        default_result = True if op is operator.ne else False
        return Bool(default_result).set_context(self.context), None

    def get_comparison_eq(self, other):
        return self._make_comparison(other, operator.eq, String)

    def get_comparison_ne(self, other):
        return self._make_comparison(other, operator.ne, String)

    def is_true(self):
        return len(self.value) > 0

    def copy(self):
        copy = String(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def type(self):
        return "<str>"

    def __str__(self):
        return self.value.replace("\n", "\\n")

    def get_comparison_gt(self, index):
        if not isinstance(index, Number):
            return None, self.illegal_operation(index, "Index must be a number")
        if index.value < 0 or index.value >= len(self.value):
            return None, RTError(
                index.pos_start,
                index.pos_end,
                "Element at this index could not be removed from String because index is out of bounds",
                self.context,
            )
        return String(self.value[index.value]), None

    def iter(self):
        return iter([String(ch) for ch in self.value]), None

    def __repr__(self):
        return repr(self.value)


class PyObject(Object):
    __slots__ = ("value",)

    def __init__(self, obj):
        super().__init__()
        self.value = obj

    def get_obj(self):
        return self.value

    def copy(self):
        c = PyObject(self.value)
        c.set_pos(self.pos_start, self.pos_end)
        c.set_context(self.context)
        return c


class List(Object):
    __slots__ = "value"

    def __init__(self, value):
        super().__init__()
        self.value = value

    def added_to(self, other):
        new_list = self.copy()
        new_list.value.append(other)
        return new_list, None

    def subbed_by(self, other):
        if isinstance(other, Number):
            new_list = self.copy()
            try:
                new_list.value.pop(other.value)
                return new_list, None
            except:
                return None, RTError(
                    other.pos_start,
                    other.pos_end,
                    "Element at this index could not be removed from list because index is out of bounds",
                    self.context,
                )
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't subtract a list by a type of '{other.type()}'"
            )

    def multed_by(self, other):
        if isinstance(other, List):
            new_list = self.copy()
            new_list.value.extend(other.value)
            return new_list, None
        elif isinstance(other, Number):
            new_list = self.copy()
            new_list.value = self.value * other.value
            return new_list, None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't multiply a list by a type of '{other.type()}'"
            )

    def get_comparison_gt(self, other):
        if isinstance(other, Number):
            try:
                return self.value[other.value], None
            except IndexError:
                return None, RTError(
                    other.pos_start,
                    other.pos_end,
                    "Element at this index could not be retrieved from list because index is out of bounds",
                    self.context,
                )
        else:
            return None, Object.illegal_operation(self, other, "Index must be a number")

    def copy(self):
        copy = List(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def is_true(self):
        return len(self.value) > 0

    def type(self):
        return "<list>"

    def iter(self):
        return iter(self.value), None

    def __str__(self):
        return ", ".join([str(x) for x in self.value])

    def __repr__(self):
        return f'[{", ".join([repr(x) for x in self.value])}]'


class HashMap(Object):
    __slots__ = "value"    
    def __init__(self, value):
        super().__init__()
        self.value: dict[str, Object] = {}
        if isinstance(value, HashMap):
            raw = value.value
        elif isinstance(value, dict):
            raw = value
        else:
            raw = {}

        for k, v in raw.items():
            key_str = str(k)
            self.value[key_str] = v

    def is_true(self):
        return len(self.value) > 0

    def added_to(self, other):
        if not isinstance(other, HashMap):
            return None, self.illegal_operation(other)

        new_map_value = self.value.copy()
        for key, value in other.value.items():
            new_map_value[key] = value

        return HashMap(new_map_value), None

    def type(self):
        return "<hashmap>"

    def get_comparison_gt(self, index):
        if not isinstance(index, String):
            return None, self.illegal_operation(index)

        try:
            return self.value[index.value], None
        except KeyError:
            return None, RTError(
                index.pos_start,
                index.pos_end,
                "Value at this key could not be retrieved from hashmap because key is not found",
                self.context,
            )

    def get_index(self, index):
        if not isinstance(index, String):
            return None, self.illegal_operation(index)
        try:
            return self.value[index.value], None
        except KeyError:
            return None, RTError(
                index.pos_start,
                index.pos_end,
                "Value at this key could not be retrieved from hashmap because key is not found",
                self.context,
            )

    def set_index(self, index, value):
        if not isinstance(index, String):
            return None, self.illegal_operation(index)
        new_value = self.value.copy()
        new_value[index.value] = value
        return HashMap(new_value)

    def iter(self):
        pairs = [List([String(str(k)), v]) for k, v in self.value.items()]
        return iter(pairs), None

    def get_comparison_eq(self, other):
        if not isinstance(other, HashMap):
            return Bool(False).set_context(self.context), None
        if len(self.value) != len(other.value):
            return Number.false.set_context(self.context), None

        for key, value in self.value.items():
            if key not in other.value:
                return Number.false.set_context(self.context), None
            cmp, err = value.get_comparison_eq(other.value[key])
            if err:
                return None, err
            if not cmp.is_true():
                return Number.false.set_context(self.context), None
        return Number.true.set_context(self.context), None

    def get_comparison_ne(self, other):
        eq_result, _ = self.get_comparison_eq(other)
        if eq_result == Number.true:
            return Number.false.set_context(self.context), None
        return Number.true.set_context(self.context), None

    def __len__(self) -> int:
        return len(self.value)

    def copy(self):
        copied_map = HashMap(self.value.copy())
        copied_map.set_pos(self.pos_start, self.pos_end)
        copied_map.set_context(self.context)
        return copied_map

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        __val = ", ".join([f"{repr(k)}: {repr(v)}" for k, v in self.value.items()])
        return f"{{{__val}}}"


class File(Object):
    __slots__ = ("name", "path")

    def __init__(self, name, path):
        super().__init__()
        self.name = name
        self.path = path

    def _make_comparison(self, other, op, type_to_check):
        if isinstance(other, type_to_check):
            result = bool(op(self.path, other.path))
            return Bool(result).set_context(self.context), None
        default_result = True if op is operator.ne else False
        return Bool(default_result).set_context(self.context), None

    def get_comparison_eq(self, other):
        return self._make_comparison(other, operator.eq, File)

    def get_comparison_ne(self, other):
        return self._make_comparison(other, operator.ne, File)

    def copy(self):
        copy = File(self.name, self.path)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def type(self):
        return "<File>"

    def __repr__(self):
        return f"<File {self.name}>"


class NameSpace(Object):
    __slots__ = ("name", "value", "_internal")

    def __init__(self, name):
        super().__init__()
        self.name = name

        self.value = HashMap({})

        self._internal = {
            "context_": Number.none,
            "statements_": Number.none,
            "initialized_": Number.false,
        }

    def get(self, name):
        if name in self._internal:
            return self._internal[name]

        r, err = self.value.get_comparison_gt(String(name))
        if err:
            return None
        return r

    def set(self, name, value):
        if name in self._internal:
            self._internal[name] = value
        else:
            self.value = self.value.set_index(String(name), value)
        return self

    def copy(self):
        copied_ns = NameSpace(self.name)
        copied_ns.value = self.value.copy()
        copied_ns._internal = self._internal.copy()
        copied_ns.set_pos(self.pos_start, self.pos_end)
        copied_ns.set_context(self.context)
        return copied_ns

    def added_to(self, other):

        if not isinstance(other, NameSpace):
            return None, self.illegal_operation(other)
        return self.value.added_to(other.value)

    def type(self):
        return "<namespace>"

    def __repr__(self):
        return f"<namespace {self.name}>"


class Bytes(Object):
    __slots__ = ("value",)

    def __init__(self, value):
        super().__init__()
        self.value = value

    def added_to(self, other):
        if isinstance(other, Bytes):
            return Bytes(self.value + other.value).set_context(self.context), None
        return None, self.illegal_operation(other)

    def get_comparison_eq(self, other):
        if isinstance(other, Bytes):
            return Bool(self.value == other.value).set_context(self.context), None
        return Bool(False).set_context(self.context), None

    def get_comparison_ne(self, other):
        if isinstance(other, Bytes):
            return Bool(self.value != other.value).set_context(self.context), None
        return Bool(True).set_context(self.context), None

    def get_comparison_gt(self, index):
        if not isinstance(index, Number):
            return None, self.illegal_operation(index)
        try:
            return Bytes(bytes(self.value[index.value])).set_context(self.context), None
        except IndexError:
            return None, RTError(
                index.pos_start,
                index.pos_end,
                "Element at this index could not be retrieved from bytes because index is out of bounds",
                self.context,
            )

    def copy(self):
        copy = Bytes(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def iter(self):
        pairs = [Bytes(bytes([i])) for i in self.value]
        return iter(pairs), None

    def is_true(self):
        return len(self.value) > 0

    def type(self):
        return "<bytes>"

    def __str__(self):
        return self.value.hex()

    def __repr__(self):
        return self.value.hex()
