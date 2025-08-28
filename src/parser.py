import os
from .nodes import *
from .consts import *
from .errors import (
    InvalidSyntaxError,
)
from .utils import Token, Fore, Style


class ParseResult:
    def __init__(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.__init__")
        self.error = None
        self.node = None
        self.last_registered_advance_count = 0
        self.advance_count = 0
        self.to_reverse_count = 0

    def register_advancement(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.register_advancement: before advance_count={self.advance_count}")
        self.last_registered_advance_count = 1
        self.advance_count += 1
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.register_advancement: after advance_count={self.advance_count}")

    def register(self, res):
        err = '\n' + str(res.error) if res.error else 'None'
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.register: registering result with advance_count={res.advance_count}, error={err}")
        self.last_registered_advance_count = res.advance_count
        self.advance_count += res.advance_count
        if res.error:
            self.error = res.error
        err = '\n' + str(self.error) if self.error else 'None'
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.register: current total advance_count={self.advance_count}, error={err}")
        return res.node

    def try_register(self, res):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.try_register: trying to register result")
        if res.error:
            self.to_reverse_count = res.advance_count
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.try_register: registration failed, to_reverse_count={self.to_reverse_count}")
            return None
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.try_register: registration successful")
        return self.register(res)

    def success(self, node):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.success: node={node}")
        self.node = node
        return self

    def failure(self, error):
        err = '\n' + str(error) if error else 'None'
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: ParseResult.failure: error='{err}'")
        if not self.error or self.last_registered_advance_count == 0:
            self.error = error
        return self


class Parser:
    __slots__ = ("tokens", "tok_idx", "current_tok")

    def __init__(self, tokens):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.__init__: tokens={tokens}")
        self.tokens = tokens
        self.tok_idx = -1
        self.current_tok = None
        self.advance()

    def advance(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.advance: from tok_idx={self.tok_idx}")
        self.tok_idx += 1
        self.update_current_tok()
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.advance: to tok_idx={self.tok_idx}, current_tok={self.current_tok}")
        return self.current_tok

    def reverse(self, amount=1):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.reverse: from tok_idx={self.tok_idx}, amount={amount}")
        self.tok_idx -= amount
        self.update_current_tok()
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.reverse: to tok_idx={self.tok_idx}, current_tok={self.current_tok}")
        return self.current_tok

    def update_current_tok(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.update_current_tok: tok_idx={self.tok_idx}")
        if self.tok_idx >= 0 and self.tok_idx < len(self.tokens):
            self.current_tok: Token = self.tokens[self.tok_idx]
        else:
            self.current_tok = None
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.update_current_tok: current_tok is now {self.current_tok}")

    def skip_newlines(self) -> ParseResult:
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.skip_newlines: starting with current_tok={self.current_tok}")
        res = ParseResult()
        while self.current_tok and self.current_tok.type == TT_NEWLINE:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.skip_newlines: skipping NEWLINE")
            res.register_advancement()
            self.advance()
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.skip_newlines: finished")
        return res

    def parse(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.parse: starting parse")
        self.skip_newlines()
        res = self.statements()
        if not res.error and self.current_tok.type != TT_EOF:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.parse: Syntax error - unexpected token {self.current_tok}")
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Token cannot appear after previous tokens",
                )
            )
        err = '\n' + str(res.error) if res.error else 'None'
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.parse: finished parse, result error={err}, node={res.node}")
        return res

    def statements(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statements: starting with current_tok={self.current_tok}")
        res = ParseResult()
        statements = []
        pos_start = self.current_tok.pos_start.copy()

        self.skip_newlines()

        res.register(self.skip_newlines())

        statement = res.register(self.statement())
        if res.error:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statements: error parsing first statement")
            return res
        statements.append(statement)

        more_statements = True
        while True:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statements: loop start, current_tok={self.current_tok}")
            newline_count = 0
            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()
                newline_count += 1

            if newline_count == 0:
                more_statements = False
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statements: no newlines, breaking loop")

            if not more_statements:
                break

            self.skip_newlines()
            statement = res.try_register(self.statement())

            if not statement:
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statements: try_register failed, reversing and breaking")
                self.reverse(res.to_reverse_count)
                more_statements = False
                continue

            statements.append(statement)

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statements: finished, returning ListNode with {len(statements)} statements")
        return res.success(
            ListNode(statements, pos_start, self.current_tok.pos_end.copy())
        )

    def statement(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statement: starting with current_tok={self.current_tok}")
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.matches(TT_KEYWORD, "using"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statement: found 'using' keyword")
            return self.using_expr()

        if self.current_tok.matches(TT_KEYWORD, "defun"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statement: found 'defun' keyword")
            return self.func_def()

        if self.current_tok.matches(TT_KEYWORD, "return"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statement: found 'return' keyword")
            res.register_advancement()
            self.advance()

            expr = None
            if self.current_tok.type not in (
                TT_NEWLINE,
                TT_EOF,
            ) and not self.current_tok.matches(TT_KEYWORD, "done"):
                expr = res.try_register(self.expr())
                if res.error:
                    return res

            return res.success(
                ReturnNode(expr, pos_start, self.current_tok.pos_start.copy())
            )

        if self.current_tok.matches(TT_KEYWORD, "continue"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statement: found 'continue' keyword")
            res.register_advancement()
            self.advance()
            return res.success(
                ContinueNode(pos_start, self.current_tok.pos_start.copy())
            )

        if self.current_tok.matches(TT_KEYWORD, "break"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statement: found 'break' keyword")
            res.register_advancement()
            self.advance()
            return res.success(BreakNode(pos_start, self.current_tok.pos_start.copy()))

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statement: parsing as expression")
        expr = res.register(self.expr())
        if res.error:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statement: failed to parse expression, returning error")
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'return', 'continue', 'break', 'let', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[', '{' or 'not'",
                )
            )
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.statement: successfully parsed expression, node={expr}")
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
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.expr: starting with current_tok={self.current_tok}")
        res = ParseResult()

        if self.current_tok.matches(TT_KEYWORD, "let"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.expr: found 'let' keyword")
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
            if self.current_tok.type == TT_EQ:
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.expr: found '=' for assignment")
                res.register_advancement()
                self.advance()
                expr = res.register(self.expr())
                if res.error:
                    return res
                return res.success(VarAssignNode(var_name, expr))
            elif self.current_tok.matches(TT_KEYWORD, "as"):
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.expr: found 'as' for aliasing")
                res.register_advancement()
                self.advance()
                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected identifier for alias",
                        )
                    )
                alias_name = self.current_tok
                res.register_advancement()
                self.advance()
                return res.success(VarAssignAsNode(var_name, alias_name))
            else:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected '=' or 'as'",
                    )
                )

        if self.current_tok.matches(TT_KEYWORD, "load"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.expr: found 'load' keyword")
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
            raw_path = module.value.replace(".", os.sep)
            if raw_path.endswith(("\\", "/")):
                raw_path = raw_path[:-1]
            raw_path += ".zyx"
            candidates = []
            if module.value.startswith("libs."):
                candidates.append(raw_path)
            elif module.value.startswith("local."):
                if self.current_tok.pos_start.fn == "<stdin>":
                    local_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), raw_path[6:]
                    )
                else:
                    local_path = os.path.join(
                        os.path.dirname(os.path.abspath(self.current_tok.pos_start.fn)),
                        raw_path[6:],
                    )
                candidates.append(local_path)
            else:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Invalid module path format. Paths must start with 'libs.' or 'local.'",
                    )
                )
            chosen_path = None
            for path in candidates:
                if os.path.exists(path):
                    chosen_path = path
                    break
            module.value = os.path.normpath(chosen_path or candidates[0])
            res.register_advancement()
            self.advance()
            return res.success(LoadNode(module))

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.expr: parsing binary operation for 'and'/'or'")
        node = res.register(
            self.bin_op(self.comp_expr, ((TT_KEYWORD, "and"), (TT_KEYWORD, "or")))
        )

        if res.error:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'let', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[', '{' or 'not'",
                )
            )

        if isinstance(node, BinOpNode) and node.op_tok.type == TT_DOLLAR:
            if self.current_tok.type == TT_EQ:
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.expr: found index assignment (e.g., list$idx = value)")
                res.register_advancement()
                self.advance()

                value_node = res.register(self.expr())
                if res.error:
                    return res

                return res.success(
                    IndexAssignNode(node.left_node, node.right_node, value_node)
                )

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.expr: finished, result node={node}")
        return res.success(node)

    def comp_expr(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.comp_expr: starting with current_tok={self.current_tok}")
        res = ParseResult()

        if self.current_tok.matches(TT_KEYWORD, "not"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.comp_expr: found 'not' keyword")
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()
            node = res.register(self.comp_expr())
            if res.error:
                return res
            return res.success(UnaryOpNode(op_tok, node))

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.comp_expr: parsing binary operation for comparison ops")
        node = res.register(
            self.bin_op(self.arith_expr, (TT_EE, TT_NE, TT_LT, TT_GT, TT_LTE, TT_GTE))
        )

        if res.error:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected int, float, identifier, '+', '-', '(', '[', '{', 'if', 'for', 'while', 'defun' or 'not'",
                )
            )

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.comp_expr: finished, result node={node}")
        return res.success(node)

    def arith_expr(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.arith_expr: starting with current_tok={self.current_tok}")
        return self.bin_op(self.term, (TT_PLUS, TT_MINUS))

    def term(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.term: starting with current_tok={self.current_tok}")
        return self.bin_op(self.factor, (TT_MUL, TT_DIV, TT_FLOORDIV, TT_MOD))

    def factor(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.factor: starting with current_tok={self.current_tok}")
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TT_PLUS, TT_MINUS):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.factor: found unary plus/minus")
            res.register_advancement()
            self.advance()
            factor = res.register(self.factor())
            if res.error:
                return res
            return res.success(UnaryOpNode(tok, factor))

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.factor: parsing dot operation")
        return self.dot_op()

    def dot_op(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.dot_op: starting with current_tok={self.current_tok}")
        return self.bin_op(self.dollar_op, (TT_DOT,))

    def dollar_op(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.dollar_op: starting with current_tok={self.current_tok}")
        return self.bin_op(self.power, (TT_DOLLAR,))

    def power(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.power: starting with current_tok={self.current_tok}")
        return self.bin_op(self.call, (TT_POW,))

    def call(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.call: starting with current_tok={self.current_tok}")
        res = ParseResult()
        node = res.register(self.atom())
        if res.error:
            return res

        while self.current_tok.type == TT_DOT:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.call: found member access '.'")
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

            member_name_tok = self.current_tok
            res.register_advancement()
            self.advance()
            node = MemberAccessNode(
                node,
                member_name_tok.value,
                node.pos_start,
                self.current_tok.pos_end.copy(),
            )

        if self.current_tok.type == TT_LPAREN:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.call: found function call '('")
            res.register_advancement()
            self.advance()
            arg_nodes = []
            if self.current_tok.type == TT_RPAREN:
                res.register_advancement()
                self.advance()
            else:
                while True:
                    # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.call: parsing argument")
                    self.skip_newlines()
                    if self.current_tok.matches(TT_KEYWORD, "let"):
                        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.call: parsing named argument")
                        res.register_advancement()
                        self.advance()
                        if self.current_tok.type != TT_IDENTIFIER:
                            return res.failure(
                                InvalidSyntaxError(
                                    self.current_tok.pos_start,
                                    self.current_tok.pos_end,
                                    "Expected identifier after 'let'",
                                )
                            )
                        var_name_tok = self.current_tok
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
                        value_node = res.register(self.expr())
                        if res.error:
                            return res
                        arg_nodes.append(VarAssignNode(var_name_tok, value_node))
                    else:
                        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.call: parsing positional argument")
                        arg_nodes.append(res.register(self.expr()))
                        if res.error:
                            return res.failure(
                                InvalidSyntaxError(
                                    self.current_tok.pos_start,
                                    self.current_tok.pos_end,
                                    "Expected ')', 'let', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[', '{' or 'not'",
                                )
                            )
                    self.skip_newlines()
                    if self.current_tok.type == TT_RPAREN:
                        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.call: found ')'")
                        res.register_advancement()
                        self.advance()
                        break
                    elif self.current_tok.type == TT_COMMA:
                        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.call: found ','")
                        res.register_advancement()
                        self.advance()
                    else:
                        return res.failure(
                            InvalidSyntaxError(
                                self.current_tok.pos_start,
                                self.current_tok.pos_end,
                                "Expected ',' or ')'",
                            )
                        )
            return res.success(CallNode(node, arg_nodes))

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.call: finished, result node={node}")
        return res.success(node)

    def using_expr(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.using_expr: starting with current_tok={self.current_tok}")
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        res.register_advancement()
        self.advance()

        if self.current_tok.matches(TT_IDENTIFIER, "parent"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.using_expr: found 'parent' keyword")
            res.register_advancement()
            self.advance()

            node_class = UsingParentNode
            err_msg = "Expected identifier after 'using parent'"
        else:
            node_class = UsingNode
            err_msg = "Expected identifier after 'using'"

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end, err_msg
                )
            )

        var_name_toks = [self.current_tok]
        res.register_advancement()
        self.advance()

        while self.current_tok.type == TT_COMMA:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.using_expr: found ',', parsing next identifier")
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
            var_name_toks.append(self.current_tok)
            res.register_advancement()
            self.advance()

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.using_expr: finished, creating {node_class.__name__} with {len(var_name_toks)} tokens")
        return res.success(
            node_class(var_name_toks, pos_start, self.current_tok.pos_end.copy())
        )

    def atom(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: starting with current_tok={self.current_tok}")
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TT_INT, TT_FLOAT):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found INT/FLOAT")
            res.register_advancement()
            self.advance()
            return res.success(NumberNode(tok))
        elif tok.type == TT_STRING:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found STRING")
            res.register_advancement()
            self.advance()
            return res.success(StringNode(tok))
        elif tok.type == TT_IDENTIFIER:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found IDENTIFIER")
            res.register_advancement()
            self.advance()
            return res.success(VarAccessNode(tok))
        elif tok.type == TT_LPAREN:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found LPAREN")
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
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found LSQUARE, parsing list")
            list_expr = res.register(self.list_expr())
            if res.error:
                return res
            return res.success(list_expr)
        elif tok.matches(TT_KEYWORD, "if"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found 'if' keyword, parsing if expression")
            if_expr = res.register(self.if_expr())
            if res.error:
                return res
            return res.success(if_expr)
        elif tok.matches(TT_KEYWORD, "for"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found 'for' keyword, parsing for expression")
            for_expr = res.register(self.for_expr())
            if res.error:
                return res
            return res.success(for_expr)
        elif tok.matches(TT_KEYWORD, "while"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found 'while' keyword, parsing while expression")
            while_expr = res.register(self.while_expr())
            if res.error:
                return res
            return res.success(while_expr)
        elif tok.matches(TT_KEYWORD, "defun"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found 'defun' keyword, parsing function definition")
            func_def = res.register(self.func_def())
            if res.error:
                return res
            return res.success(func_def)
        elif tok.matches(TT_KEYWORD, "namespace"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found 'namespace' keyword, parsing namespace")
            namespace = res.register(self.namespace())
            if res.error:
                return res
            return res.success(namespace)
        elif tok.type == TT_LBRACE:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: found LBRACE, parsing hashmap")
            hashmap_expr = res.register(self.hashmap_expr())
            if res.error:
                return res
            return res.success(hashmap_expr)

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.atom: failed to find a valid atom")
        return res.failure(
            InvalidSyntaxError(
                tok.pos_start,
                tok.pos_end,
                "Expected int, float, identifier, '+', '-', '(', '[', '{', 'if', 'for', 'while' or 'defun'",
            )
        )

    def namespace(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.namespace: starting with current_tok={self.current_tok}")
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "namespace"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'namespace'",
                )
            )
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
        namespace_name = self.current_tok.value
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_NEWLINE:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected NEWLINE",
                )
            )
        res.register_advancement()
        self.advance()

        statements = []
        while not self.current_tok.matches(TT_KEYWORD, "done"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.namespace: parsing statement in body")
            self.skip_newlines()
            stmt = res.register(self.statement())
            if res.error:
                return res
            statements.append(stmt)
            self.skip_newlines()

        statements_node = ListNode(
            statements, pos_start, self.current_tok.pos_start.copy()
        )

        if not self.current_tok.matches(TT_KEYWORD, "done"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'done'",
                )
            )
        res.register_advancement()
        self.advance()

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.namespace: successfully parsed namespace '{namespace_name}'")
        return res.success(
            NameSpaceNode(
                namespace_name,
                statements_node,
                pos_start,
                self.current_tok.pos_end.copy(),
            )
        )

    def hashmap_expr(self) -> ParseResult:
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.hashmap_expr: starting with current_tok={self.current_tok}")
        res = ParseResult()
        pairs = []
        pos_start = self.current_tok.pos_start.copy()
        res.register_advancement()
        self.advance()
        self.skip_newlines()

        if self.current_tok.type == TT_RBRACE:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.hashmap_expr: found empty hashmap")
            res.register_advancement()
            self.advance()
            return res.success(
                HashMapNode(pairs, pos_start, self.current_tok.pos_end.copy())
            )
        else:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.hashmap_expr: parsing first key-value pair")
            key = res.register(self.expr())
            if res.error:
                return res

            if self.current_tok.type != TT_COLON:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ':'",
                    )
                )
            res.register_advancement()
            self.advance()

            value = res.register(self.expr())
            if res.error:
                return res
            pairs.append((key, value))

            while self.current_tok.type == TT_COMMA:
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.hashmap_expr: found ',', parsing next pair")
                res.register_advancement()
                self.advance()
                self.skip_newlines()

                key = res.register(self.expr())
                if res.error:
                    return res
                self.skip_newlines()

                if self.current_tok.type != TT_COLON:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected ':'",
                        )
                    )
                res.register_advancement()
                self.advance()
                self.skip_newlines()

                value = res.register(self.expr())
                if res.error:
                    return res
                self.skip_newlines()

                pairs.append((key, value))

            self.skip_newlines()
            if self.current_tok.type != TT_RBRACE:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ',' or '}'",
                    )
                )
            res.register_advancement()
            self.advance()

            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.hashmap_expr: successfully parsed hashmap with {len(pairs)} pairs")
            return res.success(
                HashMapNode(pairs, pos_start, self.current_tok.pos_end.copy())
            )

    def list_expr(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.list_expr: starting with current_tok={self.current_tok}")
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
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.list_expr: found empty list")
            res.register_advancement()
            self.advance()
        else:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.list_expr: parsing first element")
            element_nodes.append(res.register(self.expr()))
            if res.error:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ']', 'let', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[', '{'"
                        " or 'not'",
                    )
                )

            while self.current_tok.type == TT_COMMA:
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.list_expr: found ',', parsing next element")
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

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.list_expr: successfully parsed list with {len(element_nodes)} elements")
        return res.success(
            ListNode(element_nodes, pos_start, self.current_tok.pos_end.copy())
        )

    def if_expr(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.if_expr (unified): starting")
        res = ParseResult()
        cases = []
        else_case = None
        is_multiline_structure = False

        if not self.current_tok.matches(TT_KEYWORD, "if"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'if'",
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
                    "Expected 'do'",
                )
            )
        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            is_multiline_structure = True
            res.register_advancement()
            self.advance()
            body = res.register(self.statements())
            if res.error:
                return res
            cases.append((condition, body, True))
        else:
            body = res.register(self.statement())
            if res.error:
                return res
            cases.append((condition, body, False))

        while self.current_tok.matches(TT_KEYWORD, "elif"):
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
                        "Expected 'do'",
                    )
                )
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                is_multiline_structure = True
                res.register_advancement()
                self.advance()
                body = res.register(self.statements())
                if res.error:
                    return res
                cases.append((condition, body, True))
            else:
                if is_multiline_structure:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Cannot mix single-line and multi-line blocks in an if-elif-else chain",
                        )
                    )
                body = res.register(self.statement())
                if res.error:
                    return res
                cases.append((condition, body, False))

        if self.current_tok.matches(TT_KEYWORD, "else"):
            res.register_advancement()
            self.advance()

            if not self.current_tok.matches(TT_KEYWORD, "do"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'do'",
                    )
                )
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                is_multiline_structure = True
                res.register_advancement()
                self.advance()
                body = res.register(self.statements())
                if res.error:
                    return res
                else_case = (body, True)
            else:
                if is_multiline_structure:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Cannot mix single-line and multi-line blocks in an if-elif-else chain",
                        )
                    )
                body = res.register(self.statement())
                if res.error:
                    return res
                else_case = (body, False)

        if is_multiline_structure:
            if not self.current_tok.matches(TT_KEYWORD, "done"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'done' to terminate multi-line if-elif-else block",
                    )
                )
            res.register_advancement()
            self.advance()

        return res.success(IfNode(cases, else_case))

    def for_expr(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.for_expr: starting with current_tok={self.current_tok}")
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "for"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'for'",
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
                    "Expected identifier",
                )
            )
        var_name = self.current_tok
        res.register_advancement()
        self.advance()

        if self.current_tok.matches(TT_KEYWORD, "in"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.for_expr: parsing 'for...in' loop")
            res.register_advancement()
            self.advance()

            iterable_node = res.register(self.expr())
            if res.error:
                return res

            if not self.current_tok.matches(TT_KEYWORD, "do"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'do'",
                    )
                )
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.for_expr: parsing multiline for-in body")
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
                            "Expected 'done'",
                        )
                    )
                res.register_advancement()
                self.advance()
                return res.success(
                    ForInNode(
                        var_name,
                        iterable_node,
                        body,
                        True,
                        var_name.pos_start,
                        body.pos_end,
                    )
                )

            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.for_expr: parsing single-line for-in body")
            body = res.register(self.statement())
            if res.error:
                return res
            return res.success(
                ForInNode(
                    var_name,
                    iterable_node,
                    body,
                    False,
                    var_name.pos_start,
                    body.pos_end,
                )
            )

        if self.current_tok.type != TT_EQ:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '=' or 'in'",
                )
            )

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.for_expr: parsing standard 'for' loop")
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
                    "Expected 'to'",
                )
            )
        res.register_advancement()
        self.advance()

        end_value = res.register(self.expr())
        if res.error:
            return res

        step_value = None
        if self.current_tok.matches(TT_KEYWORD, "step"):
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.for_expr: found 'step' value")
            res.register_advancement()
            self.advance()
            step_value = res.register(self.expr())
            if res.error:
                return res

        if not self.current_tok.matches(TT_KEYWORD, "do"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'do'",
                )
            )
        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.for_expr: parsing multiline for body")
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
                        "Expected 'done'",
                    )
                )
            res.register_advancement()
            self.advance()
            return res.success(
                ForNode(var_name, start_value, end_value, step_value, body, True)
            )

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.for_expr: parsing single-line for body")
        body = res.register(self.statement())
        if res.error:
            return res
        return res.success(
            ForNode(var_name, start_value, end_value, step_value, body, False)
        )

    def while_expr(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.while_expr: starting with current_tok={self.current_tok}")
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
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.while_expr: parsing multiline while body")
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

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.while_expr: parsing single-line while body")
        body = res.register(self.statement())
        if res.error:
            return res
        return res.success(WhileNode(condition, body, False))

    def func_def(self):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.func_def: starting with current_tok={self.current_tok}")
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "defun"):
            return res.failure(
                InvalidSyntaxError(
                    pos_start, self.current_tok.pos_end, "Expected 'defun'"
                )
            )
        res.register_advancement()
        self.advance()

        var_name_tok = None
        if self.current_tok.type == TT_IDENTIFIER:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.func_def: found function name '{self.current_tok.value}'")
            var_name_tok = self.current_tok
            res.register_advancement()
            self.advance()
        else:
            pass
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.func_def: parsing anonymous function")

        if self.current_tok.type != TT_LPAREN:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '(' after function name",
                )
            )
        res.register_advancement()
        self.advance()

        arg_name_toks = []
        defaults = []
        while self.current_tok.type != TT_RPAREN:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.func_def: parsing parameter")
            if self.current_tok.matches(TT_KEYWORD, "let"):
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.func_def: parsing parameter with default value")
                res.register_advancement()
                self.advance()
                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected parameter name after 'let'",
                        )
                    )
                arg_name = self.current_tok
                res.register_advancement()
                self.advance()
                if self.current_tok.type != TT_EQ:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected '=' for default value",
                        )
                    )
                res.register_advancement()
                self.advance()
                default_value = res.register(self.expr())
                if res.error:
                    return res
                arg_name_toks.append(arg_name)
                defaults.append(default_value)
            else:
                # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.func_def: parsing regular parameter")
                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected parameter name or 'let'",
                        )
                    )
                arg_name_toks.append(self.current_tok)
                defaults.append(None)
                res.register_advancement()
                self.advance()

            if self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()
            elif self.current_tok.type != TT_RPAREN:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ',' or ')' after parameter",
                    )
                )

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_ARROW:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.func_def: parsing arrow function body")
            res.register_advancement()
            self.advance()
            body = res.register(self.expr())
            if res.error:
                return res
            return res.success(
                FuncDefNode(var_name_tok, arg_name_toks, defaults, body, True)
            )
        elif self.current_tok.type == TT_NEWLINE:
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.func_def: parsing multiline function body")
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
                        "Expected 'done' after function body",
                    )
                )
            res.register_advancement()
            self.advance()
            return res.success(
                FuncDefNode(var_name_tok, arg_name_toks, defaults, body, False)
            )
        else:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '->' or NEWLINE after function parameters",
                )
            )

    def bin_op(self, func_a, ops, func_b=None):
        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.bin_op: starting for ops={ops}, current_tok={self.current_tok}")
        if func_b is None:
            func_b = func_a

        res = ParseResult()
        left = res.register(func_a())
        if res.error:
            return res

        while self.current_tok and (
            self.current_tok.type in ops
            or (self.current_tok.type, self.current_tok.value) in ops
        ):
            op_tok = self.current_tok
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.bin_op: found operator {op_tok}")
            res.register_advancement()
            self.advance()

            right = res.register(func_b())
            if res.error:
                return res

            left = BinOpNode(left, op_tok, right)
            # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.bin_op: created BinOpNode, new left is {left}")

        # print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}DEBUG{Fore.RESET}{Style.RESET_ALL}: Parser.bin_op: finished, returning node {left}")
        return res.success(left)
