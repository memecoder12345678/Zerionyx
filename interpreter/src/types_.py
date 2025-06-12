from .lexer import RTResult
import operator
from functools import wraps
from .errors import (
    TError,
    RTError,
    MError,
)


def handle_number_op(func):

    @wraps(func)
    def wrapper(self, other):
        if not isinstance(other, Number):
            return None, self.illegal_operation(
                other, f"The operation only supports number, not '{other.type()}'"
            )

        if self.value is None or other.value is None:
            return None, TError(
                self.pos_start,
                self.pos_end,
                "Cannot perform arithmetic with 'none'",
                self.context,
            )

        return func(self, other)

    return wrapper


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

        return True if value in self.symbols.values() else False

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

    def execute(self, args):

        return RTResult().failure(self.illegal_operation())

    def copy(self):

        raise Exception("No copy method defined")

    def is_true(self):

        return False

    def prequaled_by(self, other: "Object"):

        return None, self.illegal_operation(other)

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


class BaseFunction(Object):

    def __init__(self, name):

        super().__init__()

        self.name = name or "<anonymous>"

    def generate_new_context(self):

        new_context = Context(self.name, self.context, self.pos_start)

        new_context.symbol_table = SymbolTable(new_context.parent.symbol_table)

        new_context.private_symbol_table = SymbolTable(
            new_context.parent.private_symbol_table
        )

        return new_context

    def check_args(self, arg_names, args):

        res = RTResult()

        if len(args) > len(arg_names):

            return res.failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"{len(args) - len(arg_names)} too many args passed into {self}",
                    self.context,
                )
            )

        if len(args) < len(arg_names):

            return res.failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"{len(arg_names) - len(args)} too few args passed into {self}",
                    self.context,
                )
            )

        return res.success(None)

    def populate_args(self, arg_names, args, exec_ctx):

        for i in range(len(args)):

            arg_name = arg_names[i]

            arg_value = args[i]

            arg_value.set_context(exec_ctx)

            exec_ctx.symbol_table.set(arg_name, arg_value)

    def check_and_populate_args(self, arg_names, args, exec_ctx):

        res = RTResult()

        res.register(self.check_args(arg_names, args))

        if res.should_return():

            return res

        self.populate_args(arg_names, args, exec_ctx)

        return res.success(None)


class None_(Object):

    __slots__ = "value"

    def __init__(self, value):

        super().__init__()

        self.value = value

    def added_to(self, other):

        return other, None

    def copy(self):

        copy = None_(self.value)

        copy.set_pos(self.pos_start, self.pos_end)

        copy.set_context(self.context)

        return copy

    def is_true(self):

        return False

    def __str__(self):

        return "none"

    def __repr__(self):

        return str(self.value)

    def notted(self):

        return Number(1 if self.value == 0 else 0).set_context(self.context), None

    def get_comparison_eq(self, other):

        if isinstance(other, None_):

            return Number(1).set_context(self.context), None

        return Number(0).set_context(self.context), None

    def get_comparison_ne(self, other):

        if isinstance(other, None_):

            return Number(0).set_context(self.context), None

        return Number(1).set_context(self.context), None

    def get_comparison_lt(self, other):

        return Number(0).set_context(self.context), None

    def get_comparison_gt(self, other):

        return Number(0).set_context(self.context), None

    def get_comparison_lte(self, other):

        if isinstance(other, None_):

            return Number(1).set_context(self.context), None

        return Number(0).set_context(self.context), None

    def get_comparison_gte(self, other):

        if isinstance(other, None_):

            return Number(1).set_context(self.context), None

        return Number(0).set_context(self.context), None


None_.none = None_("none")


class Number(Object):
    __slots__ = ("value", "context", "pos_start", "pos_end", "fields")

    def __init__(
        self, value, context=None, pos_start=None, pos_end=None, reusable=False
    ):
        self.reusable = reusable
        self.value = value
        self.context = context
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.fields = []

    def copy(self):
        return Number(self.value, self.context, self.pos_start, self.pos_end)

    @handle_number_op
    def i_add(self, other):
        self.value += other.value
        return self, None

    @handle_number_op
    def added_to(self, other):
        if other.value == 0:
            return self, None
        if self.value == 0:
            return other, None
        if other.value == 1:
            if hasattr(self, "reusable"):
                self.value += 1
                return self, None
            return Number(self.value + 1, self.context), None
        if self.value == 1:
            if hasattr(other, "reusable"):
                other.value += 1
                return other, None
        if hasattr(self, "reusable"):
            self.value += other.value
            return self, None
        return Number(self.value + other.value, self.context), None

    @handle_number_op
    def subbed_by(self, other):
        if other.value == 0:
            return self, None
        if other.value == 1:
            if hasattr(self, "reusable"):
                self.value -= 1
                return self, None
        if hasattr(self, "reusable"):
            self.value -= other.value
            return self, None
        return Number(self.value - other.value, self.context), None

    @handle_number_op
    def multed_by(self, other):
        if self.value == 0 or other.value == 0:
            return Number(0).set_context(self.context), None
        if self.value == 1:
            return other, None
        if other.value == 1:
            return self, None
        if other.value == 2:
            return Number(self.value << 1, self.context), None
        return Number(self.value * other.value, self.context), None

    @handle_number_op
    def dived_by(self, other):
        if other.value == 0:
            return None, MError(
                other.pos_start, other.pos_end, "Division by zero", self.context
            )
        if other.value == 1:
            return self, None
        return Number(self.value / other.value).set_context(self.context), None

    @handle_number_op
    def moduled_by(self, other):
        if other.value == 0:
            return None, MError(
                other.pos_start, other.pos_end, "Division by zero", self.context
            )
        if other.value == 1:
            return Number.false, None
        return Number(self.value % other.value).set_context(self.context), None

    @handle_number_op
    def powed_by(self, other):
        if other.value == 0:
            return Number(1).set_context(self.context), None
        if other.value == 1:
            return self, None
        if other.value == 2:
            return Number(self.value * self.value).set_context(self.context), None
        if self.value == 0:
            return Number.false, None
        return Number(self.value**other.value).set_context(self.context), None

    @handle_number_op
    def floordived_by(self, other):
        if other.value == 0:
            return None, MError(
                other.pos_start, other.pos_end, "Division by zero", self.context
            )
        if other.value == 1:
            return self, None
        return Number(self.value // other.value).set_context(self.context), None

    def _get_comparison_result(self, other, op):
        default = 1 if op is operator.ne else 0

        if (
            isinstance(other, Number)
            and self.value is not None
            and other.value is not None
        ):
            result = int(op(self.value, other.value))
            return Number(result, self.context), None

        if self.value is None:
            if isinstance(other, None_):
                result = 1 if op in (operator.eq, operator.le, operator.ge) else 0
            else:
                result = default
            return Number(result, self.context), None

        return Number(default, self.context), None

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
            Number((self.value != 0) & (other.value != 0)).set_context(self.context),
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
        return Number(int(not self.value)).set_context(self.context), None

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

        if self.value == 0:

            return "0"

        if self.value == 1:

            return "1"

        return str(self.value).replace("e", "*10^")

    def __repr__(self):

        if self.value is None:

            return "none"

        if self.value == 0:

            return "0"

        if self.value == 1:

            return "1"

        return str(self.value).replace("e", "*10^")


Number.false = Number(0, reusable=True)
Number.true = Number(1, reusable=True)
Number.none = None_.none


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
            result = int(op(self.value, other.value))
            return Number(result).set_context(self.context), None

        default_result = 1 if op is operator.ne else 0
        return Number(default_result).set_context(self.context), None

    def get_comparison_eq(self, other):
        return self._make_comparison(other, operator.eq, String)

    def get_comparison_ne(self, other):
        return self._make_comparison(other, operator.ne, String)

    def get_comparison_lt(self, other):
        return self._make_comparison(other, operator.lt, String)

    def get_comparison_gt(self, other):
        return self._make_comparison(other, operator.gt, String)

    def get_comparison_lte(self, other):
        return self._make_comparison(other, operator.le, String)

    def get_comparison_gte(self, other):
        return self._make_comparison(other, operator.ge, String)

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

    def __repr__(self):

        return_value = f'"{self.value}"'

        if return_value.endswith('""'):

            return_value = return_value[:-1]

        elif return_value.endswith("'\""):

            return_value = return_value[:-2]

        return return_value


class List(Object):

    __slots__ = ("elements", "reusable")

    def __init__(self, elements, reusable=False):
        super().__init__()
        self.elements = elements
        self.reusable = reusable

    def added_to(self, other):
        if hasattr(self, "reusable") and self.reusable:
            self.elements.append(other)
            return self, None
        new_list = self.copy()
        new_list.elements.append(other)
        return new_list, None

    def subbed_by(self, other):
        if isinstance(other, Number):
            if hasattr(self, "reusable") and self.reusable:
                try:
                    self.elements.pop(other.value)
                    return self, None
                except:
                    return None, RTError(
                        other.pos_start,
                        other.pos_end,
                        "Element at this index could not be removed from list because index is out of bounds",
                        self.context,
                    )
            new_list = self.copy()
            try:
                new_list.elements.pop(other.value)
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
            if hasattr(self, "reusable") and self.reusable:
                self.elements.extend(other.elements)
                return self, None
            new_list = self.copy()
            new_list.elements.extend(other.elements)
            return new_list, None
        else:
            return None, Object.illegal_operation(
                self, other, f"Can't multiply a list by a type of '{other.type()}'"
            )

    def get_comparison_gt(self, other):

        if isinstance(other, Number):

            try:

                return self.elements[other.value], None

            except IndexError:

                return None, RTError(
                    other.pos_start,
                    other.pos_end,
                    "Element at this index could not be retrieved from list because index is out of bounds",
                    self.context,
                )

        else:

            return None, Object.illegal_operation(
                self, other, "Index must be a number type"
            )

    def copy(self):

        copy = List(self.elements)

        copy.set_pos(self.pos_start, self.pos_end)

        copy.set_context(self.context)

        return copy

    def is_true(self):

        return len(self.elements) > 0

    def type(self):

        return "<list>"

    def __str__(self):

        return ", ".join([str(x) for x in self.elements])

    def __repr__(self):

        return f'[{", ".join([repr(x) for x in self.elements])}]'


class File(Object):

    __slots__ = ("name", "path")

    def __init__(self, name, path):

        super().__init__()

        self.name = name

        self.path = path

    def _make_comparison(self, other, op, type_to_check):
        if isinstance(other, type_to_check):
            result = int(op(self.path, other.path))
            return Number(result).set_context(self.context), None

        default_result = 1 if op is operator.ne else 0
        return Number(default_result).set_context(self.context), None

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


List.empty = List([], reusable=True)
