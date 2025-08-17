### **Changelog: Version 3.0.2 - Ergonomics & Expressiveness Update**

**Date:** August 17, 2025

We are excited to launch version 3.0.2, an update centered on improving the core developer experience. The centerpiece of this release is a major syntactic enhancement that makes writing code more intuitive and readable.

---

### Function Renaming: `is_panic`

The diagnostic helper function has been renamed from `is_err` to `is_panic` for greater clarity and consistency.

New Signature:
```
is_panic(func, args=[])
```

Returns `[result, none, none]` if execution succeeds.

Returns `[none, err_msg, err_name]` if execution fails.

err_name is one of `"RT"`, `"M"`, `"IO"`, or `"T"`.

This makes error checking more intuitive and emphasizes the panic semantics of runtime exceptions.

### 🚀 New Feature: Intuitive Indexed Assignment with `$`

To improve code readability and developer ergonomics, we are introducing a major syntactic sugar enhancement. This change replaces the more verbose `set(...)` function call with a direct and intuitive assignment operator. Our goal is to make the language feel more familiar and to let you write cleaner, more expressive code.

#### **How It Works**

The new syntax leverages the existing `$` access operator, combining it with the standard assignment operator `=`. This allows you to modify elements within a `List` and `HashMap` directly.

*   **For Lists:** You can assign a new value to an element using its numeric index.
    *   **Syntax:** `IDENTIFIER $ NUMBER = EXPR`

*   **For HashMaps:** You can assign a new value to an entry using its string key.
    *   **Syntax:** `IDENTIFIER $ STRING = EXPR`

#### **Examples: Before vs. After**

The improvement is best illustrated by comparing the old and new code.

**Before: Using the `set()` function**
```
let my_list = [10, 20, 30]
let my_map = {"status": "pending", "id": 123}

# Required a function call to modify
set(my_list, 0, 99)
set(my_map, "status", "complete")

println(my_list)   #> [99, 20, 30]
println(my_map)    #> {"status": "complete", "id": 123}
```

**Now: Using Direct Indexed Assignment**
```
let my_list = [10, 20, 30]
let my_map = {"status": "pending", "id": 123}

# The new syntax is much cleaner and more intuitive!
my_list$0 = 99
my_map$"status" = "complete"

println(my_list)   #> [99, 20, 30]
println(my_map)    #> {"status": "complete", "id": 123}
```
