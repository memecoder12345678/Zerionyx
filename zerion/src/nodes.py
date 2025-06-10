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
        return f"StringNode(\"{self.tok.value}\")"


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
        for condition, expr, should_return in self.cases:
            result += f"\nIF {condition} THEN {expr}"
        if self.else_case:
            expr, should_return = self.else_case
            result += f"\nELSE {expr}"
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
        return f"WhileNode(WHILE {self.condition_node} DO {self.body_node})"


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
        return f"LoadNode(\"{self.file_path}\")"


def ast_to_dict(node):
    if node is None:
        return None
    if isinstance(node, NumberNode):
        return {"type": "NumberNode", "value": node.tok.value}
    if isinstance(node, StringNode):
        return {"type": "StringNode", "value": node.tok.value}
    if isinstance(node, VarAccessNode):
        return {"type": "VarAccessNode", "name": node.var_name_tok.value}
    if isinstance(node, VarAssignNode):
        return {
            "type": "VarAssignNode",
            "name": node.var_name_tok.value,
            "value": ast_to_dict(node.value_node),
        }
    if isinstance(node, BinOpNode):
        return {
            "type": "BinOpNode",
            "left": ast_to_dict(node.left_node),
            "op": node.op_tok.type,
            "right": ast_to_dict(node.right_node),
        }
    if isinstance(node, UnaryOpNode):
        return {
            "type": "UnaryOpNode",
            "op": node.op_tok.type,
            "node": ast_to_dict(node.node),
        }
    if isinstance(node, ListNode):
        elements = [ast_to_dict(e) for e in node.element_nodes]
        return {
            "type": "ListNode",
            "elements": elements
        }
    if isinstance(node, IfNode):
        return {
            "type": "IfNode",
            "cases": [[ast_to_dict(cond), ast_to_dict(expr)] for cond, expr, _ in node.cases],
            "else": ast_to_dict(node.else_case[0]) if node.else_case else None,
        }
    if isinstance(node, ForNode):
        return {
            "type": "ForNode",
            "var": node.var_name_tok.value,
            "start": ast_to_dict(node.start_value_node),
            "end": ast_to_dict(node.end_value_node),
            "step": ast_to_dict(node.step_value_node),
            "body": ast_to_dict(node.body_node),
        }
    if isinstance(node, WhileNode):
        return {
            "type": "WhileNode",
            "condition": ast_to_dict(node.condition_node),
            "body": ast_to_dict(node.body_node),
        }
    if isinstance(node, FuncDefNode):
        return {
            "type": "FuncDefNode",
            "name": node.var_name_tok.value if node.var_name_tok else "anonymous",
            "args": [tok.value for tok in node.arg_name_toks],
            "body": ast_to_dict(node.body_node),
        }
    if isinstance(node, CallNode):
        return {
            "type": "CallNode",
            "function": ast_to_dict(node.node_to_call),
            "args": [ast_to_dict(arg) for arg in node.arg_nodes],
        }
    if isinstance(node, ReturnNode):
        return {"type": "ReturnNode", "value": ast_to_dict(node.node_to_return)}
    if isinstance(node, ContinueNode):
        return {"type": "ContinueNode"}
    if isinstance(node, BreakNode):
        return {"type": "BreakNode"}
    if isinstance(node, AccessNode):
        return {
            "type": "AccessNode",
            "object": ast_to_dict(node.obj),
            "index": ast_to_dict(node.index),
        }
    if isinstance(node, LoadNode):
        return {"type": "LoadNode", "path": node.file_path}
    return {"type": "UnknownNode", "repr": repr(node)}
