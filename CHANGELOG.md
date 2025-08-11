### **Changelog: Version 3.0.1 - Scope Control & Stability Update**

**Date:** August 11, 2025

We are pleased to release version 3.0.1, a major update that introduces advanced scope management features and significant improvements to built-in functions. This release focuses on enhancing the expressiveness of the language and improving stability for complex program structures.

---

### New Features

#### **1. Global Scope Access with `using`**

A new keyword, `using`, has been introduced to control variable access in the global scope from within functions. This keyword, similar to Python's `global`, allows a function to declare its intention to modify a variable in the top-level global scope.

*   **Syntax:** `using IDENTIFIER ("," IDENTIFIER)*`
*   **Behavior:** When a variable is declared with `using`, subsequent assignments to it modify the global variable, not a local copy. Accessing the variable correctly retrieves the global value.
*   **Constraint:** `using` can only be used inside a function.

#### **2. Nonlocal Scope Access with `using parent`**

For managing variables in nested functions, the `using parent` keyword has been added. This functions similarly to Python's `nonlocal` statement, allowing a nested function to modify a variable in its immediate enclosing (parent) scope.

*   **Syntax:** `using parent IDENTIFIER ("," IDENTIFIER)*`
*   **Behavior:** When a variable is declared with `using parent`, assignments to it modify the variable in the parent function's scope.
*   **Constraint:** `using parent` can only be used inside a nested function where a valid parent scope exists.

---

### Bug Fixes & Stability 🐛

#### **1. Corrected Variable Access for `using` and `using parent`**

**Fix:** A critical bug was identified in how the interpreter handled variable access after a `using` or `using parent` declaration. Previously, only the assignment operation was redirected; variable access still read a stale local copy. This has been corrected. Accessing a variable declared with `using` or `using parent` now correctly reads the current value from the target scope (global or parent), ensuring proper state synchronization.

#### **2. Namespace Context Resolution**

**Fix:** Addressed an issue where lazily-initialized namespaces might fail to resolve variables from their enclosing context during member access. The context resolution logic for namespaces has been stabilized, ensuring that namespace members correctly inherit and access variables from the scope in which the namespace was defined.

---

### Changes & Improvements

#### **1. `to_bytes` Function Overhaul**

The built-in `to_bytes` function has been significantly upgraded from a specific hex-to-bytes converter to a more general data utility.

*   **Expanded Input Types:** Now accepts `number`, `string`, and `bytes` as input.
*   **New Parameter (`from_hex`)**: A new boolean parameter `from_hex` (defaulting to `false`) allows control over conversion.
    *   If `from_hex=false`, strings are converted using standard character encoding (e.g., UTF-8).
    *   If `from_hex=true`, strings are parsed as hexadecimal values (legacy behavior).

---

### Deprecations & Removals

#### **1. Removed `to_hex` Built-in Function**

The built-in function `to_hex` has been removed. Its functionality is considered specialized and can be achieved through other core language primitives, streamlining the standard library.
