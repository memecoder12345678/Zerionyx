# Changelog: Version 5.0.5 — Language Features, Comprehensions & Fixes

**Date:** September 14, 2025

Zerionyx 5.0.5 is a major update that introduces powerful new **language features**, **collection comprehensions**, critical **bug fixes**, and new **type-check utilities**. This release significantly enhances the language's expressiveness and developer ergonomics.

---

## 🐞 Bug Fixes

*   Fixed an issue in **`threading.pool.result()`** where completed futures sometimes returned `None`. Now consistently returns the task's final `value`.

---

## ✨ New Features

*   **New `del` Statement for Variable Deletion**
    You can now permanently remove one or more variables from the current scope using the `del` keyword.

    ```zyx
    a = 10
    b = 20
    del a, b
    # println(a) would now cause a RuntimeError
    ```

*   **Variable Aliasing with the `as` Keyword**
    The `as` keyword creates a new name (alias) that refers to the same underlying object as an existing variable. This is a reference, not a copy.

    ```zyx
    original = [1, 2]
    alias as original
    append(alias, 3)
    println(original) # Output: [1, 2, 3]
    ```

*   **Powerful List and Hashmap Comprehensions**
    A concise, expressive syntax for creating lists and hashmaps from iterables has been added.

    *   **List Comprehension:**
        ```zyx
        squares = [i^2 for i = 0 to 10]
        # squares is now [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
        ```
    *   **Hashmap Comprehension:**
        ```zyx
        number_map = {for i = 0 to 5 do to_str(i) : i}
        # number_map is now {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4}
        ```

*   **New Built-in Functions**
    Added new helpers for runtime validation and safe data access:
    *   `is_thread_pool(x) -> bool`   # Check if x is a thread pool
    *   `is_future(x) -> bool`      # Check if x is a future
    *   `is_namespace(x) -> bool`   # Check if x is a namespace
    *   `get_member(namespace, member, default)` &rarr; any &mdash; Gets a member from a `namespace`, returning `default` (defaults to `none`) if it does not exist.

---

## 💥 Breaking Changes

*   **Decorator Syntax Change**
    The decorator symbol has been changed from `@` to `&` for a cleaner and more consistent style.

*   **Hashmap `del()` Renamed to `del_key()`**
    The built-in function `del()` for removing a key from a hashmap has been renamed to **`del_key()`**. This change was necessary to avoid a name conflict with the new `del` keyword.

    *   **Old Code:** `del(my_map, "my_key")`
    *   **New Code:** `del_key(my_map, "my_key")`

---

## 📌 Summary

Zerionyx 5.0.5 brings:

*   **Core language enhancements** with the `del` statement and `as` aliasing.
*   Expressive **list and hashmap comprehensions**.
*   A **new decorator syntax** with `&`.
*   Handy **utility functions** like `get_member` and new type-checkers.
*   A name change for the hashmap key deletion function to `del_key`.

This release makes the language more powerful, consistent, and developer-friendly.