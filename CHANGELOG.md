### **Changelog: Version 4.0.0 - The PSOP Revolution**

**Date:** August 21, 2025

This is a landmark release. Version 4.0.0 fundamentally evolves Zerionyx from a simple scripting language into a powerful, organized, and expressive language centered around a new programming paradigm: **Prototype Space-Oriented Programming (PSOP)**. This update introduces revolutionary ways to structure, reuse, and write code, alongside critical bug fixes and ergonomic improvements.

---

### 🌟 New Paradigm: Prototype Space-Oriented Programming (PSOP)

Zerionyx now formally embraces PSOP, a model that combines the organizational power of namespaces with the flexibility of prototypal instantiation.

*   **Core Concepts:**
    1.  **Prototype (`namespace`):** The `namespace` block is now treated as a "live template" or a complete prototype object, encapsulating both state (variables) and behavior (functions).
    2.  **Instance (`clone()`):** A new built-in function, `clone()`, allows you to create deep copies of any namespace, producing new, independent instances with their own state.
    3.  **Context (`space`):** The `space` keyword provides a consistent, unambiguous reference to the current instance's context, eliminating the complexities of `this` found in other languages.

This paradigm offers the encapsulation benefits of OOP without the rigidity of classes and inheritance, making code both highly structured and incredibly flexible.

### 🚀 New Features & Syntactic Enhancements

#### 1. Prototypal Instantiation with `clone()`

The cornerstone of the PSOP model is the new `clone()` built-in function. It empowers developers to create multiple instances from a single namespace prototype.

*   **Syntax:** `clone(NAMESPACE_PROTOTYPE)`
*   **Behavior:** Performs a deep copy of the given namespace, creating a new instance with its own sandboxed state. The original prototype and other instances are not affected by changes to the clone.

**Example: Creating Multiple Instances**
```zyx
namespace UserPrototype
    name = "default"
    defun greet() -> "Hello, " + to_str(space.name)
done

# Create two independent user instances from the prototype
let user1 = clone(UserPrototype)
let user2 = clone(UserPrototype)

user1.name = "Alice"
user2.name = "Bob"

println(user1.greet()) #> Hello, Alice
println(user2.greet()) #> Hello, Bob
```

#### 2. Direct Member Assignment (`.`)

To align with the dynamic nature of PSOP, we've introduced a more intuitive way to modify the state of namespaces and their instances. You can now assign values to members directly using the familiar dot (`.`) and assignment (`=`) operators.

*   **Syntax:** `NAMESPACE_INSTANCE.MEMBER_NAME = EXPR`

**Example: Before vs. After**
```zyx
# Before: No standard way to modify members after creation
# Now: Simple and direct!

let my_app_config = clone(AppConfigPrototype)

# The new syntax is clean and universally understood
my_app_config.port = 8080
my_app_config.debug_mode = true
```

---

### 🐛 Bug Fixes & Stability Improvements

*   **Parser Stability:** Fixed a critical `IndexError` crash in the `load` statement handler. The parser will now produce a user-friendly error message if a module path does not start with the required `libs.` or `local.` prefix, instead of exiting unexpectedly.
*   **Error Message Clarity:** Improved the error message for invalid `load` paths to guide the user on the correct syntax, enhancing the overall developer experience.
*   **General Fixes:** Addressed various minor bugs to improve the overall stability and predictability of the interpreter.

This update represents a major leap forward for Zerionyx, establishing a clear and powerful identity. We believe the PSOP model will enable you to write more scalable, maintainable, and elegant code. We can't wait to see what you build with it