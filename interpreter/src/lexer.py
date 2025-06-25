from .consts import *
from .utils import Token, Position, RTResult
from .errors import IllegalCharError, ExpectedCharError, InvalidSyntaxError


class Lexer:
    __slots__ = ["fn", "text", "pos", "current_char", "tokens", "open_bracket_stack"]

    def __init__(self, fn, text):
        self.fn = fn
        self.text = text
        self.pos = Position(-1, 0, -1, fn, text)
        self.current_char = None
        self.advance()
        self.tokens = []
        self.open_bracket_stack = []

    def advance(self):
        self.pos.advance(self.current_char)
        self.current_char = (
            self.text[self.pos.idx] if self.pos.idx < len(self.text) else None
        )

    def make_tokens(self):
        while self.current_char is not None:
            # print(self.open_bracket_stack)
            if self.current_char in " \t":
                self.advance()
            elif self.current_char == "#":
                self.skip_comment()
            elif self.current_char in ";\n":
                if (
                    self.open_bracket_stack
                    and self.open_bracket_stack[-1][0] == ")augmented"
                ):
                    rparen_pos = self.pos.copy()
                    self.tokens.append(
                        Token(TT_RPAREN, pos_start=rparen_pos, pos_end=rparen_pos)
                    )
                    self.open_bracket_stack.pop()

                if self.open_bracket_stack:
                    self.advance()
                else:
                    if self.tokens and self.tokens[-1].type == TT_NEWLINE:
                        self.advance()
                        continue
                    newline_pos_start = self.pos.copy()
                    self.tokens.append(Token(TT_NEWLINE, pos_start=newline_pos_start))
                    self.advance()
            elif self.current_char in DIGITS:
                self.tokens.append(self.make_number())
            elif self.current_char in LETTERS + "_":
                self.tokens.append(self.make_identifier())
            elif self.current_char == '"':
                token, error = self.make_string()
                if error:
                    return [], error
                self.tokens.append(token)
            elif self.current_char == "'":
                token, error = self.make_string_single()
                if error:
                    return [], error
                self.tokens.append(token)
            elif self.current_char == "+":
                self.handle_plus_or_augmented()
            elif self.current_char == "-":
                self.handle_minus_or_augmented()
            elif self.current_char == "*":
                self.handle_mul_or_augmented()
            elif self.current_char == "/":
                self.div_or_floordiv_or_augmented()
            elif self.current_char == "\\":
                if self.peek_foward_steps(1) == "\n":
                    self.advance()
                    self.advance()
                else:
                    pos_start = self.pos.copy()
                    self.advance()
                    return [], IllegalCharError(
                        pos_start, self.pos, "Stray '\\' character in program"
                    )
            elif self.current_char == "^":
                self.handle_pow_or_augmented()
            elif self.current_char == "%":
                self.handle_mod_or_augmented()
            elif self.current_char == "=":
                self.tokens.append(self.make_equals())
            elif self.current_char == "(":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_LPAREN, pos_start=pos_start))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                self.open_bracket_stack.append((")", pos_start))
            elif self.current_char == ")":
                pos_start_closer = self.pos.copy()
                self.tokens.append(Token(TT_RPAREN, pos_start=pos_start_closer))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()

                if not self.open_bracket_stack:
                    return [], ExpectedCharError(
                        pos_start_closer, self.pos, "')' without matching opener"
                    )

                expected_closer, _ = self.open_bracket_stack[-1]
                if expected_closer == ")":
                    self.open_bracket_stack.pop()
                elif expected_closer == ")augmented":
                    return [], InvalidSyntaxError(
                        pos_start_closer,
                        self.pos,
                        "Expected end of expression or newline",
                    )
                else:
                    return [], ExpectedCharError(
                        pos_start_closer, self.pos, f"'{expected_closer}'"
                    )
            elif self.current_char == "[":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_LSQUARE, pos_start=pos_start))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                self.open_bracket_stack.append(("]", pos_start))
            elif self.current_char == "]":
                pos_start_closer = self.pos.copy()
                self.tokens.append(Token(TT_RSQUARE, pos_start=pos_start_closer))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()

                if not self.open_bracket_stack:
                    return [], ExpectedCharError(
                        pos_start_closer, self.pos, "']' without matching opener"
                    )

                expected_closer, _ = self.open_bracket_stack[-1]
                if expected_closer == "]":
                    self.open_bracket_stack.pop()
                else:
                    return [], ExpectedCharError(
                        pos_start_closer, self.pos, f"'{expected_closer}'"
                    )
            elif self.current_char == "!":
                token, error = self.make_not_equals()
                if error:
                    return [], error
                self.tokens.append(token)
            elif self.current_char == "<":
                self.tokens.append(self.make_less_than())
            elif self.current_char == ">":
                self.tokens.append(self.make_greater_than())
            elif self.current_char == ".":
                self.tokens.append(Token(TT_DOT, pos_start=self.pos.copy()))
                self.advance()
            elif self.current_char == ",":
                self.tokens.append(Token(TT_COMMA, pos_start=self.pos.copy()))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
            elif self.current_char == "{":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_LBRACE, pos_start=pos_start))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                self.open_bracket_stack.append(("}", pos_start))
            elif self.current_char == "}":
                pos_start_closer = self.pos.copy()
                self.tokens.append(Token(TT_RBRACE, pos_start=pos_start_closer))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()

                if not self.open_bracket_stack:
                    return [], ExpectedCharError(
                        pos_start_closer, self.pos, "'}' without matching opener"
                    )

                expected_closer, _ = self.open_bracket_stack[-1]
                if expected_closer == "}":
                    self.open_bracket_stack.pop()
                else:
                    return [], ExpectedCharError(
                        pos_start_closer, self.pos, f"'{expected_closer}'"
                    )
            elif self.current_char == ":":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_COLON, pos_start=pos_start))
                self.advance()
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                return [], IllegalCharError(pos_start, self.pos, "'" + char + "'")

        if self.open_bracket_stack and self.open_bracket_stack[-1][0] == ")augmented":
            rparen_pos = self.pos.copy()
            self.tokens.append(
                Token(TT_RPAREN, pos_start=rparen_pos, pos_end=rparen_pos)
            )
            self.open_bracket_stack.pop()

        if self.open_bracket_stack:
            expected_closer, opener_pos_start = self.open_bracket_stack[-1]
            if expected_closer == ")augmented":
                return [], InvalidSyntaxError(
                    opener_pos_start,
                    self.pos,
                    "Incomplete augmented assignment expression, expected an expression after operator",
                )
            return [], ExpectedCharError(
                opener_pos_start, self.pos, f"Expected '{expected_closer}'"
            )

        self.tokens.append(Token(TT_EOF, pos_start=self.pos))
        return self.tokens, None

    def make_number(self):
        num_str = ""
        dot_count = 0
        pos_start = self.pos.copy()

        while self.current_char != None and self.current_char in DIGITS + ".":
            if self.current_char == ".":
                if dot_count == 1:
                    break
                dot_count += 1
            num_str += self.current_char
            self.advance()

        if dot_count == 0:
            return Token(TT_INT, int(num_str), pos_start, self.pos)
        else:
            return Token(TT_FLOAT, float(num_str), pos_start, self.pos)



    def make_string_single(self):
        string = ""
        pos_start = self.pos.copy()
        escape_character = False
        self.advance()
        escape_characters = {"n": "\n", "t": "\t", "r": "\r", "'": "\'", '"': '\"'}
        if self.current_char == "'" and self.peek_foward_steps(1) == "'":
            self.advance()
            self.advance()
            while self.current_char is not None:
                if (
                    self.current_char == "'"
                    and self.peek_foward_steps(1) == "'"
                    and self.peek_foward_steps(2) == "'"
                ):
                    self.advance()
                    self.advance()
                    self.advance()
                    break
                if escape_character:
                    string += escape_characters.get(
                        self.current_char,
                        "\\" if self.current_char == "\\" else self.current_char,
                    )
                    escape_character = False
                else:
                    if self.current_char == "\\":
                        escape_character = True
                    else:
                        string += self.current_char
                self.advance()
            else:
                return [], ExpectedCharError(
                    pos_start, self.pos, "''' (closing quotes for multiline string)"
                )
            return Token(TT_STRING, string, pos_start, self.pos), None
        while self.current_char is not None and (
            self.current_char != "'" or escape_character
        ):
            if escape_character:
                string += escape_characters.get(
                    self.current_char,
                    "\\" if self.current_char == "\\" else self.current_char,
                )
                escape_character = False
            else:
                if self.current_char == "\\":
                    escape_character = True
                else:
                    string += self.current_char
            self.advance()
        if self.current_char != "'":
            return [], ExpectedCharError(
                pos_start, self.pos, '"\'" (closing quote for string)'
            )
        self.advance()
        return Token(TT_STRING, string, pos_start, self.pos), None

    def make_string(self):
        string = ""
        pos_start = self.pos.copy()
        escape_character = False
        self.advance()
        escape_characters = {"n": "\n", "t": "\t", "r": "\r", "'": "\'", '"': '\"'}
        if self.current_char == '"' and self.peek_foward_steps(1) == '"':
            self.advance()
            self.advance()
            while self.current_char is not None:
                if (
                    self.current_char == '"'
                    and self.peek_foward_steps(1) == '"'
                    and self.peek_foward_steps(2) == '"'
                ):
                    self.advance()
                    self.advance()
                    self.advance()
                    break
                if escape_character:
                    string += escape_characters.get(
                        self.current_char,
                        "\\" if self.current_char == "\\" else self.current_char,
                    )
                    escape_character = False
                else:
                    if self.current_char == "\\":
                        escape_character = True
                    else:
                        string += self.current_char
                self.advance()
            else:
                return [], ExpectedCharError(
                    pos_start, self.pos, '""" (closing quotes for multiline string)'
                )
            return Token(TT_STRING, string, pos_start, self.pos), None
        while self.current_char is not None and (
            self.current_char != '"' or escape_character
        ):
            if escape_character:
                string += escape_characters.get(
                    self.current_char,
                    "\\" if self.current_char == "\\" else self.current_char,
                )
                escape_character = False
            else:
                if self.current_char == "\\":
                    escape_character = True
                else:
                    string += self.current_char
            self.advance()
        if self.current_char != '"':
            return [], ExpectedCharError(
                pos_start, self.pos, "'\"' (closing quote for string)"
            )
        self.advance()
        return Token(TT_STRING, string, pos_start, self.pos), None

    def peek_foward_steps(self, steps) -> str | None:
        peek_pos_idx = self.pos.idx + steps
        if peek_pos_idx < len(self.text) and peek_pos_idx >= 0:
            return self.text[peek_pos_idx : peek_pos_idx + 1]
        return None

    def previous_token(self) -> Token | None:
        try:
            return self.tokens[-1]
        except IndexError:
            return None

    def _emit_augmented_assignment_tokens(
        self,
        base_op_type: str,
        identifier_token_original: Token,
        eq_token_pos_start: Position,
        eq_token_pos_end: Position,
        op_token_pos_start: Position,
        op_token_pos_end: Position,
    ):

        self.tokens.append(
            Token(
                TT_EQ,
                pos_start=eq_token_pos_start.copy(),
                pos_end=eq_token_pos_end.copy(),
            )
        )

        self.tokens.append(
            Token(
                TT_IDENTIFIER,
                value=identifier_token_original.value,
                pos_start=identifier_token_original.pos_start.copy(),
                pos_end=identifier_token_original.pos_end.copy(),
            )
        )

        self.tokens.append(
            Token(
                base_op_type,
                pos_start=op_token_pos_start.copy(),
                pos_end=op_token_pos_end.copy(),
            )
        )

        lparen_aug_pos = op_token_pos_end.copy()
        self.tokens.append(
            Token(
                TT_LPAREN,
                pos_start=lparen_aug_pos.copy(),
                pos_end=lparen_aug_pos.copy(),
            )
        )
        self.open_bracket_stack.append((")augmented", lparen_aug_pos.copy()))

    def _handle_augmented_assignment_common(
        self, base_op_type: str, pos_start_op_char: Position
    ):
        pos_end_op_char = self.pos.copy()

        if self.current_char == "=":
            if not self.tokens or self.tokens[-1].type != TT_IDENTIFIER:
                self.tokens.append(
                    Token(
                        base_op_type,
                        pos_start=pos_start_op_char,
                        pos_end=pos_end_op_char,
                    )
                )
                pos_start_eq = self.pos.copy()
                self.advance()
                pos_end_eq = self.pos.copy()
                self.tokens.append(
                    Token(TT_EQ, pos_start=pos_start_eq, pos_end=pos_end_eq)
                )
                return

            identifier_token = self.tokens.pop()

            pos_start_eq_char = self.pos.copy()
            self.advance()
            pos_end_eq_char = self.pos.copy()

            self.tokens.append(identifier_token)
            self._emit_augmented_assignment_tokens(
                base_op_type,
                identifier_token_original=identifier_token,
                eq_token_pos_start=pos_start_eq_char,
                eq_token_pos_end=pos_end_eq_char,
                op_token_pos_start=pos_start_op_char,
                op_token_pos_end=pos_end_op_char,
            )
        else:
            self.tokens.append(
                Token(
                    base_op_type, pos_start=pos_start_op_char, pos_end=pos_end_op_char
                )
            )

    def handle_plus_or_augmented(self):
        pos_start_op = self.pos.copy()
        self.advance()
        self._handle_augmented_assignment_common(TT_PLUS, pos_start_op)

    def handle_minus_or_augmented(self):
        pos_start_op = self.pos.copy()
        self.advance()

        if self.current_char == ">":
            self.advance()
            self.tokens.append(
                Token(TT_ARROW, pos_start=pos_start_op, pos_end=self.pos.copy())
            )
        else:
            self._handle_augmented_assignment_common(TT_MINUS, pos_start_op)

    def handle_mul_or_augmented(self):
        pos_start_op = self.pos.copy()
        self.advance()
        self._handle_augmented_assignment_common(TT_MUL, pos_start_op)

    def handle_pow_or_augmented(self):
        pos_start_op = self.pos.copy()
        self.advance()
        self._handle_augmented_assignment_common(TT_POW, pos_start_op)

    def handle_mod_or_augmented(self):
        pos_start_op = self.pos.copy()
        self.advance()
        self._handle_augmented_assignment_common(TT_MOD, pos_start_op)

    def div_or_floordiv_or_augmented(self):
        pos_start_first_slash = self.pos.copy()
        self.advance()

        if self.current_char == "/":
            pos_start_operator = pos_start_first_slash
            self.advance()
            self._handle_augmented_assignment_common(TT_FLOORDIV, pos_start_operator)
        else:
            self._handle_augmented_assignment_common(TT_DIV, pos_start_first_slash)

    def make_identifier(self) -> Token:
        id_str = ""
        pos_start_identifier = self.pos.copy()

        while (
            self.current_char is not None and self.current_char in LETTERS_DIGITS + "_"
        ):
            id_str += self.current_char
            self.advance()

        pos_end_identifier = self.pos.copy()

        is_assignment_op_follows = False
        peek_idx = self.pos.idx
        while peek_idx < len(self.text) and self.text[peek_idx] in " \t":
            peek_idx += 1

        if peek_idx < len(self.text):
            op_char1 = self.text[peek_idx]
            op_char2 = (
                self.text[peek_idx + 1] if peek_idx + 1 < len(self.text) else None
            )
            op_char3 = (
                self.text[peek_idx + 2] if peek_idx + 2 < len(self.text) else None
            )

            if op_char1 == "=" and op_char2 != "=":
                is_assignment_op_follows = True
            elif op_char1 in ["+", "-", "*", "^", "%"] and op_char2 == "=":
                is_assignment_op_follows = True
            elif op_char1 == "/" and (
                op_char2 == "=" or (op_char2 == "/" and op_char3 == "=")
            ):
                is_assignment_op_follows = True

        if is_assignment_op_follows:
            pt: Token | None = self.previous_token()
            allowed_preceding_keywords_for_let = {"do", "else"}
            insert_let = False
            if id_str not in KEYWORDS:
                if (
                    pt is None
                    or pt.type == TT_NEWLINE
                    or (
                        pt.type == TT_KEYWORD
                        and pt.value in allowed_preceding_keywords_for_let
                    )
                    or pt.type == TT_ARROW
                ):
                    insert_let = True

            if insert_let:
                self.tokens.append(
                    Token(
                        TT_KEYWORD,
                        value="let",
                        pos_start=pos_start_identifier.copy(),
                        pos_end=pos_end_identifier.copy(),
                    )
                )

        tok_type = TT_KEYWORD if id_str in KEYWORDS else TT_IDENTIFIER
        return Token(tok_type, id_str, pos_start_identifier, pos_end_identifier)

    def make_not_equals(self):
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            self.advance()
            return Token(TT_NE, pos_start=pos_start, pos_end=self.pos.copy()), None
        return None, ExpectedCharError(pos_start, self.pos.copy(), "'=' (after '!')")

    def make_equals(self) -> Token:
        tok_type = TT_EQ
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            self.advance()
            tok_type = TT_EE

        return Token(tok_type, pos_start=pos_start, pos_end=self.pos.copy())

    def make_less_than(self) -> Token:
        tok_type = TT_LT
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            self.advance()
            tok_type = TT_LTE

        return Token(tok_type, pos_start=pos_start, pos_end=self.pos.copy())

    def make_greater_than(self) -> Token:
        tok_type = TT_GT
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            self.advance()
            tok_type = TT_GTE

        return Token(tok_type, pos_start=pos_start, pos_end=self.pos.copy())

    def skip_comment(self) -> None:
        self.advance()
        while self.current_char is not None and self.current_char != "\n":
            self.advance()
