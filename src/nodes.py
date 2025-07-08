from colorama import Fore, Style


class NumberNode:
    __slots__ = ["tok", "pos_start", "pos_end"]

    def __init__(self, tok):
        self.tok = tok

        self.pos_start = self.tok.pos_start
        self.pos_end = self.tok.pos_end

    def __repr__(self):
        return f"{self.tok}"

    def __str__(self):
        return f"NumberNode({self.tok.value})"


class StringNode:
    __slots__ = ["tok", "pos_start", "pos_end"]

    def __init__(self, tok):
        self.tok = tok

        self.pos_start = self.tok.pos_start
        self.pos_end = self.tok.pos_end

    def __repr__(self):
        return f"{self.tok}"

    def __str__(self):
        return f'StringNode("{self.tok.value}")'


class ListNode:

    __slots__ = ["element_nodes", "pos_start", "pos_end"]

    def __init__(self, element_nodes, pos_start, pos_end):
        self.element_nodes = element_nodes

        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return f"ListNode({', '.join(str(x) for x in self.element_nodes)})"


class VarAccessNode:
    __slots__ = ["var_name_tok", "pos_start", "pos_end"]

    def __init__(self, var_name_tok):
        self.var_name_tok = var_name_tok

        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.var_name_tok.pos_end

    def __str__(self):
        return f"VarAccessNode({self.var_name_tok.value})"


class VarAssignNode:
    __slots__ = ["var_name_tok", "value_node", "pos_start", "pos_end"]

    def __init__(self, var_name_tok, value_node):
        self.var_name_tok = var_name_tok
        self.value_node = value_node

        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.value_node.pos_end

    def __str__(self):
        return f"VarAssignNode({self.var_name_tok.value} = {self.value_node})"


class BinOpNode:
    __slots__ = ["left_node", "op_tok", "right_node", "pos_start", "pos_end"]

    def __init__(self, left_node, op_tok, right_node):
        self.left_node = left_node
        self.op_tok = op_tok
        self.right_node = right_node

        self.pos_start = self.left_node.pos_start
        self.pos_end = self.right_node.pos_end

    def __repr__(self):
        return f"({self.left_node}, {self.op_tok}, {self.right_node})"

    def __str__(self):
        return f"BinOpNode({self.left_node} {self.op_tok.type} {self.right_node})"


class UnaryOpNode:
    __slots__ = ["op_tok", "node", "pos_start", "pos_end"]

    def __init__(self, op_tok, node):
        self.op_tok = op_tok
        self.node = node

        self.pos_start = self.op_tok.pos_start
        self.pos_end = node.pos_end

    def __repr__(self):
        return f"({self.op_tok}, {self.node})"

    def __str__(self):
        return f"UnaryOpNode({self.op_tok.type}{self.node})"


class IfNode:
    __slots__ = ["cases", "else_case", "pos_start", "pos_end"]

    def __init__(self, cases, else_case):
        self.cases = cases
        self.else_case = else_case

        self.pos_start = self.cases[0][0].pos_start
        self.pos_end = (self.else_case or self.cases[len(self.cases) - 1])[0].pos_end

    def __str__(self):
        result = "IfNode("
        for condition, expr, _ in self.cases:
            result += f"\nif {condition} do {expr}"
        if self.else_case:
            expr, _ = self.else_case
            result += f"\nelse {expr}"
        return result + ")"


class ForNode:
    __slots__ = [
        "var_name_tok",
        "start_value_node",
        "end_value_node",
        "step_value_node",
        "body_node",
        "should_return_none",
        "pos_start",
        "pos_end",
    ]

    def __init__(
        self,
        var_name_tok,
        start_value_node,
        end_value_node,
        step_value_node,
        body_node,
        should_return_none,
    ):
        self.var_name_tok = var_name_tok
        self.start_value_node = start_value_node
        self.end_value_node = end_value_node
        self.step_value_node = step_value_node
        self.body_node = body_node
        self.should_return_none = should_return_none

        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.body_node.pos_end

    def __str__(self):
        return f"ForNode({self.var_name_tok.value} from {self.start_value_node} to {self.end_value_node} step {self.step_value_node} do {self.body_node})"


class WhileNode:
    __slots__ = [
        "condition_node",
        "body_node",
        "should_return_none",
        "pos_start",
        "pos_end",
    ]

    def __init__(self, condition_node, body_node, should_return_none):
        self.condition_node = condition_node
        self.body_node = body_node
        self.should_return_none = should_return_none

        self.pos_start = self.condition_node.pos_start
        self.pos_end = self.body_node.pos_end

    def __str__(self):
        return f"WhileNode(while {self.condition_node} do {self.body_node})"


class FuncDefNode:
    __slots__ = [
        "var_name_tok",
        "arg_name_toks",
        "body_node",
        "should_auto_return",
        "pos_start",
        "pos_end",
    ]

    def __init__(self, var_name_tok, arg_name_toks, body_node, should_auto_return):
        self.var_name_tok = var_name_tok
        self.arg_name_toks = arg_name_toks
        self.body_node = body_node
        self.should_auto_return = should_auto_return

        if self.var_name_tok:
            self.pos_start = self.var_name_tok.pos_start
        elif len(self.arg_name_toks) > 0:
            self.pos_start = self.arg_name_toks[0].pos_start
        else:
            self.pos_start = self.body_node.pos_start

        self.pos_end = self.body_node.pos_end

    def __str__(self):
        return f"FuncDefNode({self.var_name_tok.value if self.var_name_tok else 'anonymous'}({', '.join(t.value for t in self.arg_name_toks)}) {self.body_node})"


class CallNode:
    __slots__ = ["node_to_call", "arg_nodes", "pos_start", "pos_end"]

    def __init__(self, node_to_call, arg_nodes):
        self.node_to_call = node_to_call
        self.arg_nodes = arg_nodes

        self.pos_start = self.node_to_call.pos_start

        if len(self.arg_nodes) > 0:
            self.pos_end = self.arg_nodes[len(self.arg_nodes) - 1].pos_end
        else:
            self.pos_end = self.node_to_call.pos_end

    def __str__(self):
        return f"CallNode({self.node_to_call}({', '.join(str(arg) for arg in self.arg_nodes)}))"


class ReturnNode:
    __slots__ = ["node_to_return", "pos_start", "pos_end"]

    def __init__(self, node_to_return, pos_start, pos_end):
        self.node_to_return = node_to_return

        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return f"ReturnNode({self.node_to_return})"


class ContinueNode:
    __slots__ = ["pos_start", "pos_end"]

    def __init__(self, pos_start, pos_end):
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return "ContinueNode()"


class BreakNode:
    __slots__ = ["pos_start", "pos_end"]

    def __init__(self, pos_start, pos_end):
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return "BreakNode()"


class AccessNode:

    def __init__(self, obj, index):
        self.obj = obj
        self.index = index

    def __str__(self):
        return f"AccessNode({self.obj}[{self.index}])"


class LoadNode:
    __slots__ = ["module_name_tok", "file_path", "pos_start", "pos_end"]

    def __init__(self, module_name_tok):
        self.module_name_tok = module_name_tok
        self.file_path = module_name_tok.value

        self.pos_start = self.module_name_tok.pos_start
        self.pos_end = self.module_name_tok.pos_end

    def __str__(self):
        return f'LoadNode("{self.file_path}")'


class HashMapNode:
    __slots__ = ["pairs", "pos_start", "pos_end"]

    def __init__(self, pairs, pos_start, pos_end):
        self.pairs = pairs
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return f"HashMapNode({', '.join(f'{k}: {v}' for k, v in self.pairs)})"


class ForInNode:
    __slots__ = [
        "var_name_tok",
        "iterable_node",
        "body_node",
        "pos_start",
        "pos_end",
        "should_return_none",
    ]

    def __init__(
        self,
        var_name_tok,
        iterable_node,
        body_node,
        should_return_none,
        pos_start=None,
        pos_end=None,
    ):
        self.var_name_tok = var_name_tok
        self.iterable_node = iterable_node
        self.body_node = body_node
        self.should_return_none = should_return_none
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return f"ForInNode({self.var_name_tok.value} in {self.iterable_node} do {self.body_node})"


class VarAssignAsNode:
    __slots__ = ["var_name_tok", "var_name_tok2", "pos_start", "pos_end"]

    def __init__(self, var_name_tok, var_name_tok2):
        self.var_name_tok = var_name_tok
        self.var_name_tok2 = var_name_tok2

        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.var_name_tok2.pos_end

    def __str__(self):
        return (
            f"VarAssignAsNode({self.var_name_tok.value} = {self.var_name_tok2.value})"
        )


class NameSpaceNode:
    __slots__ = ["namespace_name", "statements", "pos_start", "pos_end"]

    def __init__(self, namespace_name, statements, pos_start, pos_end):
        self.namespace_name = (
            namespace_name if isinstance(namespace_name, str) else namespace_name.value
        )
        self.statements = statements
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"NameSpaceNode({self.namespace_name}, {self.statements})"


def astpretty(node, indent=0):
    pad = "  " * indent
    if node is None:
        return pad + f"{Fore.LIGHTBLACK_EX}None{Style.RESET_ALL}"

    def colorize_type(node_type):
        return f"{Fore.BLUE}{node_type}{Style.RESET_ALL}"

    def colorize_value(value):
        return f"{Fore.YELLOW}{value}{Style.RESET_ALL}"

    def colorize_string(value):
        return f'{Fore.GREEN}"{value}"{Style.RESET_ALL}'

    def colorize_keyword(keyword):
        return f"{Fore.CYAN}{keyword}{Style.RESET_ALL}"

    if isinstance(node, ListNode):
        node_type = colorize_type("ListNode")
        res = pad + f"{node_type}(\n"
        for elem in node.element_nodes:
            res += astpretty(elem, indent + 1) + ",\n"
        res += pad + ")"
        return res

    if isinstance(node, LoadNode):
        node_type = colorize_type("LoadNode")
        return pad + f"{node_type}({colorize_string(node.file_path)})"

    if isinstance(node, StringNode):
        node_type = colorize_type("StringNode")
        return pad + f"{node_type}({colorize_string(node.tok.value)})"
    if isinstance(node, NumberNode):
        node_type = colorize_type("NumberNode")
        return pad + f"{node_type}({colorize_value(node.tok.value)})"

    if isinstance(node, VarAccessNode):
        node_type = colorize_type("VarAccessNode")
        return pad + f"{node_type}({colorize_value(node.var_name_tok.value)})"
    if isinstance(node, VarAssignNode):
        node_type = colorize_type("VarAssignNode")
        return (
            pad
            + f"{node_type}({colorize_value(node.var_name_tok.value)} {colorize_keyword('=')} {astpretty(node.value_node, 0)})"
        )

    if isinstance(node, BinOpNode):
        node_type = colorize_type("BinOpNode")
        return (
            pad
            + f"{node_type}(\n{astpretty(node.left_node, indent + 1)},\n{pad + '  ' + colorize_value(node.op_tok.type)},\n{astpretty(node.right_node, indent + 1)}\n{pad})"
        )
    if isinstance(node, UnaryOpNode):
        node_type = colorize_type("UnaryOpNode")
        return (
            pad
            + f"{node_type}({colorize_value(node.op_tok.type)}, {astpretty(node.node, indent + 1)})"
        )

    if isinstance(node, CallNode):
        node_type = colorize_type("CallNode")
        res = pad + f"{node_type}(\n{astpretty(node.node_to_call, indent + 1)}"
        if node.arg_nodes:
            res += ",\n" + pad + f"  {colorize_keyword('args')}=[\n"
            for arg in node.arg_nodes:
                res += astpretty(arg, indent + 2) + ",\n"
            res += pad + "  ]"
        res += f"\n{pad})"
        return res

    if isinstance(node, IfNode):
        node_type = colorize_type("IfNode")
        res = pad + f"{node_type}(\n"
        for condition, expr, _ in node.cases:
            res += (
                pad
                + f"  {colorize_keyword('if')}\n"
                + astpretty(condition, indent + 2)
                + ",\n"
            )
            res += (
                pad
                + f"  {colorize_keyword('do')}\n"
                + astpretty(expr, indent + 2)
                + ",\n"
            )
        if node.else_case:
            expr, _ = node.else_case
            res += (
                pad
                + f"  {colorize_keyword('else')}\n"
                + astpretty(expr, indent + 2)
                + ",\n"
            )
        res += pad + ")"
        return res

    if isinstance(node, ForNode):
        node_type = colorize_type("ForNode")
        return pad + (
            f"{node_type}({colorize_value(node.var_name_tok.value)} "
            f"{colorize_keyword('from')} {astpretty(node.start_value_node, 0)} "
            f"{colorize_keyword('to')} {astpretty(node.end_value_node, 0)} "
            f"{colorize_keyword('step')} {astpretty(node.step_value_node, 0)} "
            f"{colorize_keyword('do')} {astpretty(node.body_node, indent + 1)})"
        )

    if isinstance(node, ForInNode):
        node_type = colorize_type("ForInNode")
        return pad + (
            f"{node_type}({colorize_value(node.var_name_tok.value)} "
            f"{colorize_keyword('in')} {astpretty(node.iterable_node, 0)} "
            f"{colorize_keyword('do')} {astpretty(node.body_node, indent + 1)})"
        )

    if isinstance(node, VarAssignAsNode):
        node_type = colorize_type("VarAssignAsNode")
        return pad + (
            f"{node_type}({colorize_value(node.var_name_tok.value)} "
            f"{colorize_keyword('as')} {astpretty(node.var_name_tok2, 0)})"
        )

    if isinstance(node, WhileNode):
        node_type = colorize_type("WhileNode")
        return pad + (
            f"{node_type}({colorize_keyword('while')} {astpretty(node.condition_node, 0)} "
            f"{colorize_keyword('do')} {astpretty(node.body_node, indent + 1)})"
        )

    if isinstance(node, FuncDefNode):
        node_type = colorize_type("FuncDefNode")
        args = ", ".join(colorize_value(tok.value) for tok in node.arg_name_toks)
        name = (
            colorize_value(node.var_name_tok.value)
            if node.var_name_tok
            else colorize_keyword("anonymous")
        )
        return (
            pad + f"{node_type}({name}({args}) {astpretty(node.body_node, indent + 1)})"
        )

    if isinstance(node, ReturnNode):
        node_type = colorize_type("ReturnNode")
        return pad + f"{node_type}({astpretty(node.node_to_return, indent + 1)})"
    if isinstance(node, ContinueNode):
        node_type = colorize_type("ContinueNode")
        return pad + f"{node_type}()"
    if isinstance(node, BreakNode):
        node_type = colorize_type("BreakNode")
        return pad + f"{node_type}()"

    if isinstance(node, AccessNode):
        node_type = colorize_type("AccessNode")
        return (
            pad + f"{node_type}({astpretty(node.obj, 0)}[{astpretty(node.index, 0)}])"
        )

    if isinstance(node, HashMapNode):
        node_type = colorize_type("HashMapNode")
        res = pad + f"{node_type}(\n"
        for k, v in node.pairs:
            res += pad + f"  {astpretty(k, 0)}: {astpretty(v, 0)},\n"
        res += pad + ")"
        return res

    if isinstance(node, MemberAccessNode):
        return (
            pad + colorize_type("MemberAccessNode") + "("
            + astpretty(node.object_node,0) + "."
            + colorize_value(node.member_name)
            + ")"
        )
    
    if isinstance(node, NameSpaceNode):
        node_type = colorize_type("NameSpaceNode")
        res = pad + f"{node_type}({colorize_value(node.namespace_name)}) (\n"
        for stmt in node.statements:
            res += astpretty(stmt, indent + 1) + "\n"
        res += pad + ")"
        return res

    return pad + repr(node)




class MemberAccessNode:
    __slots__ = ["object_node", "member_name", "pos_start", "pos_end"]

    def __init__(self, object_node, member_name, pos_start, pos_end):
        self.object_node = object_node
        self.member_name = member_name
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"(MemberAccessNode {self.object_node}.{self.member_name})"
