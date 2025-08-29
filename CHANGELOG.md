# Changelog: Version 4.0.4 &mdash; The Expressiveness & Metaprogramming Update

**Date:** August 29, 2025

This is a landmark release for Zerionyx, fundamentally enhancing the language's expressiveness and introducing powerful metaprogramming capabilities. Version 4.0.4 brings two of the most requested features from modern dynamic languages: arbitrary argument lists (`*vargs`/`**kargs`) and function decorators, making function definitions more flexible and code more reusable.

---

## ✨ New Features

### 1. Arbitrary Argument Lists (`*vargs` & `**kargs`)

Function definitions now support Python-like syntax for capturing a variable number of positional and keyword arguments. This makes it possible to create highly flexible functions that can accept any number of inputs.

*   `*vargs`: Captures all additional positional arguments into a `list`.
*   `**kargs`: Captures all additional keyword arguments into a `hashmap`.

```zyx
# Usage Example
defun logger(prefix, *vargs, **kargs)
    print(prefix)
    for arg in vargs do
        println("  - Positional: " + to_str(arg))
    done
    for item in items(kargs) do
        println("  - Keyword: " + item$0 + " = " + to_str(item$1))
    done
done

logger("Processing Data:", 101, "active", user="memecoder", status="online")
```

### 2. Function Decorators

Zerionyx now supports decorator syntax (`@`) for metaprogramming. Decorators are functions that take another function as input, add functionality to it, and return the modified function. This is a powerful pattern for separating concerns and reusing code (e.g., for logging, timing, or authentication).

```zyx
# Usage Example
defun log_call(fn)
    defun wrapper(*vargs, **kargs)
        println("Calling function: " + slice(to_str(fn), 10, -1))
        result = fn(*vargs, **kargs)
        println("Function " + slice(to_str(fn), 10, -1) + " finished.")
        return result
    done
    return wrapper
done

@log_call
defun add(a, b) -> a + b

add(5, 3)
```
**Output:**
```
Calling function: add
Function add finished.
```
---

## 🐞 Bug Fixes & Improvements

1.  **Lexer Robustness:** The lexer has been improved to correctly handle multi-character operators (`**`, `=>`) without ambiguity.

2.  **Parser Enhancements:** The function definition parser has been completely rewritten to support the new flexible argument syntax.

---

Zerionyx 4.0.4 is a major leap forward, providing developers with sophisticated tools to write cleaner, more powerful, and more reusable code. These new metaprogramming features unlock advanced design patterns and solidify Zerionyx's position as a highly capable modern scripting language.