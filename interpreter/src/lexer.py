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
            if self.current_char in " \t":
                self.advance()
            elif self.current_char == "#":
                self.skip_comment()
            elif self.current_char in ";\n":
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
            elif self.current_char == '\\': 
                if self.peek_foward_steps(1) == '\n':
                    self.advance()
                    self.advance()
                else:
                    pos_start = self.pos.copy()
                    self.advance() 
                    return [], IllegalCharError(pos_start, self.pos, "Stray '\\' character in program")
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
                self.open_bracket_stack.append((')', pos_start))
            elif self.current_char == ")":
                pos_start_closer = self.pos.copy()
                self.tokens.append(Token(TT_RPAREN, pos_start=pos_start_closer))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()

                if not self.open_bracket_stack:
                    return [], InvalidSyntaxError(pos_start_closer, self.pos, "Unmatched ')'")
                
                expected_closer, opener_pos = self.open_bracket_stack[-1]
                if expected_closer == ')':
                    self.open_bracket_stack.pop()
                else:
                    actual_opener_char = '['
                    return [], InvalidSyntaxError(
                        pos_start_closer, self.pos,
                        f"Mismatched closing parenthesis ')'. Expected '{expected_closer}' to close '{actual_opener_char}' opened at line {opener_pos.ln + 1}, column {opener_pos.col + 1}"
                    )
            elif self.current_char == "[":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_LSQUARE, pos_start=pos_start))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                self.open_bracket_stack.append((']', pos_start))
            elif self.current_char == "]":
                pos_start_closer = self.pos.copy()
                self.tokens.append(Token(TT_RSQUARE, pos_start=pos_start_closer))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()

                if not self.open_bracket_stack:
                    return [], InvalidSyntaxError(pos_start_closer, self.pos, "Unmatched ']'")

                expected_closer, opener_pos = self.open_bracket_stack[-1]
                if expected_closer == ']':
                    self.open_bracket_stack.pop()
                else:
                    actual_opener_char = '('
                    return [], InvalidSyntaxError(
                        pos_start_closer, self.pos,
                        f"Mismatched closing bracket ']'"
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
            elif self.current_char == ",":
                self.tokens.append(Token(TT_COMMA, pos_start=self.pos.copy()))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                return [], IllegalCharError(pos_start, self.pos, "'" + char + "'")

        if self.open_bracket_stack:
            expected_closer, opener_pos_start = self.open_bracket_stack[-1]
            actual_opener_char = '(' if expected_closer == ')' else '['
            return [], InvalidSyntaxError(
                opener_pos_start,
                self.pos,
                f"Expected '{expected_closer}'"
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

        escape_characters = {"n": "\n", "t": "\t", "r": "\r"}

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
                return [], InvalidSyntaxError(pos_start, self.pos, "Unterminated string literal")

            return Token(TT_STRING, string, pos_start, self.pos), []

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
            return [], InvalidSyntaxError(pos_start, self.pos, "Unterminated string literal")

        self.advance()
        return Token(TT_STRING, string, pos_start, self.pos), []

    def make_string(self):
        string = ""
        pos_start = self.pos.copy()
        escape_character = False
        self.advance()

        escape_characters = {"n": "\n", "t": "\t", "r": "\r"}

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
                return [], InvalidSyntaxError(pos_start, self.pos, "Unterminated string literal")

            return Token(TT_STRING, string, pos_start, self.pos), []

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
            return [], InvalidSyntaxError(pos_start, self.pos, "Unterminated string literal")

        self.advance()
        return Token(TT_STRING, string, pos_start, self.pos), []

    def peek_foward(self) -> str | None:
        peek_pos = self.pos.copy()
        while self.text[peek_pos.idx : peek_pos.idx + 1] == " ":
            peek_pos.idx += 1
        if peek_pos.idx > len(self.text):
            return None
        if peek_pos.idx < len(self.text):
            forward = self.text[peek_pos.idx : peek_pos.idx + 1]
            return forward
        return None


    def peek_foward_steps(self, steps) -> str | None:
        peek_pos_idx = self.pos.idx + steps
        if peek_pos_idx < len(self.text) and peek_pos_idx >=0 :
            return self.text[peek_pos_idx : peek_pos_idx + 1]
        return None


    def peek_backward_steps(self, steps) -> str | None:
        peek_pos_idx = self.pos.idx - steps
        if peek_pos_idx >= 0 and peek_pos_idx < len(self.text):
            return self.text[peek_pos_idx : peek_pos_idx + 1]
        return None

    def previous_token(self) -> Token | None:
        try:
            return self.tokens[-1]
        except IndexError:
            return None

    def _emit_augmented_assignment_tokens(
        self, base_op_type: str, op_pos_start: Position, op_pos_end: Position
    ):
        if self.tokens and self.tokens[-1].type == TT_IDENTIFIER:
            identifier_token = self.tokens[-1]
            id_name = identifier_token.value
            self.tokens.append(
                Token(TT_EQ, pos_start=op_pos_start.copy(), pos_end=op_pos_end.copy())
            )

            rhs_element_pos = op_pos_end.copy()
            self.tokens.append(
                Token(
                    TT_IDENTIFIER,
                    value=id_name,
                    pos_start=identifier_token.pos_start.copy(),
                    pos_end=identifier_token.pos_end.copy()
                )
            )

            self.tokens.append(
                Token(base_op_type, pos_start=rhs_element_pos, pos_end=rhs_element_pos)
            )
        else:
            base_op_char_pos_start = op_pos_start.copy()
            base_op_char_pos_end = op_pos_start.copy()

            first_char_of_op = self.text[op_pos_start.idx]
            base_op_char_pos_end.advance(first_char_of_op)

            if base_op_type == TT_FLOORDIV:
                if op_pos_start.idx + 1 < len(self.text):
                    second_char_of_op = self.text[op_pos_start.idx + 1]
                    base_op_char_pos_end.advance(second_char_of_op)

            self.tokens.append(
                Token(
                    base_op_type,
                    pos_start=base_op_char_pos_start,
                    pos_end=base_op_char_pos_end.copy(),
                )
            )
            self.tokens.append(
                Token(
                    TT_EQ,
                    pos_start=base_op_char_pos_end.copy(),
                    pos_end=op_pos_end.copy(),
                )
            )

    def handle_plus_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            pos_op_start = pos_start
            self.advance()
            pos_op_end = self.pos.copy()
            self._emit_augmented_assignment_tokens(TT_PLUS, pos_op_start, pos_op_end)
        else:
            self.tokens.append(
                Token(TT_PLUS, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def handle_minus_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            pos_op_start = pos_start
            self.advance()
            pos_op_end = self.pos.copy()
            self._emit_augmented_assignment_tokens(TT_MINUS, pos_op_start, pos_op_end)
        elif self.current_char == ">":
            pos_arrow_start = pos_start
            self.advance()
            pos_arrow_end = self.pos.copy()
            self.tokens.append(
                Token(TT_ARROW, pos_start=pos_arrow_start, pos_end=pos_arrow_end)
            )
        else:
            self.tokens.append(
                Token(TT_MINUS, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def handle_mul_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            pos_op_start = pos_start
            self.advance()
            pos_op_end = self.pos.copy()
            self._emit_augmented_assignment_tokens(TT_MUL, pos_op_start, pos_op_end)
        else:
            self.tokens.append(
                Token(TT_MUL, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def handle_pow_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            pos_op_start = pos_start
            self.advance()
            pos_op_end = self.pos.copy()
            self._emit_augmented_assignment_tokens(TT_POW, pos_op_start, pos_op_end)
        else:
            self.tokens.append(
                Token(TT_POW, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def handle_mod_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            pos_op_start = pos_start
            self.advance()
            pos_op_end = self.pos.copy()
            self._emit_augmented_assignment_tokens(TT_MOD, pos_op_start, pos_op_end)
        else:
            self.tokens.append(
                Token(TT_MOD, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def div_or_floordiv_or_augmented(self):
        pos_start_first_slash = self.pos.copy()
        self.advance()

        if self.current_char == "/":
            pos_start_operator = pos_start_first_slash
            self.advance()
            pos_after_base_op = self.pos.copy()

            if self.current_char == "=":
                self.advance()
                pos_op_end = self.pos.copy()
                self._emit_augmented_assignment_tokens(
                    TT_FLOORDIV, pos_start_operator, pos_op_end
                )
            else:
                self.tokens.append(
                    Token(
                        TT_FLOORDIV,
                        pos_start=pos_start_operator,
                        pos_end=pos_after_base_op,
                    )
                )
        elif self.current_char == "=":
            pos_start_operator = pos_start_first_slash
            self.advance()
            pos_op_end = self.pos.copy()
            self._emit_augmented_assignment_tokens(
                TT_DIV, pos_start_operator, pos_op_end
            )
        else:
            self.tokens.append(
                Token(TT_DIV, pos_start=pos_start_first_slash, pos_end=self.pos.copy())
            )

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

            if op_char1 == "=":
                if op_char2 != "=":
                    is_assignment_op_follows = True
            elif op_char1 in ["+", "-", "*", "^", "%"]:
                if op_char2 == "=":
                    is_assignment_op_follows = True
            elif op_char1 == "/":
                if op_char2 == "=":
                    is_assignment_op_follows = True
                elif op_char2 == "/" and op_char3 == "=":
                    is_assignment_op_follows = True

        if is_assignment_op_follows:
            pt: Token | None = self.previous_token()
            allowed_preceding_keywords_for_let = {"do", "else"}
            insert_let = False
            if id_str not in KEYWORDS:
                if pt is None:
                    insert_let = True
                elif pt.type == TT_NEWLINE:
                    insert_let = True
                elif (
                    pt.type == TT_KEYWORD
                    and pt.value in allowed_preceding_keywords_for_let
                ):
                    insert_let = True
                elif pt.type == TT_ARROW:
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
            return Token(TT_NE, pos_start=pos_start, pos_end=self.pos), None

        self.advance()
        return None, ExpectedCharError(pos_start, self.pos.copy(), "'=' (after '!')")


    def make_equals(self) -> Token:
        tok_type = TT_EQ
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            self.advance()
            tok_type = TT_EE

        return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

    def make_less_than(self) -> Token:
        tok_type = TT_LT
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            self.advance()
            tok_type = TT_LTE

        return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

    def make_greater_than(self) -> Token:
        tok_type = TT_GT
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            self.advance()
            tok_type = TT_GTE

        return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

    def skip_comment(self) -> None:
        self.advance()

        while self.current_char != None and self.current_char != "\n":
            self.advance()
