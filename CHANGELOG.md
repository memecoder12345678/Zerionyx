# Changelog: Version 4.0.1 &mdash; The Stabilization & Syntax Alignment Update

**Date:** August 24, 2025

After the experimental leap in 4.0.0, this release restores Zerionyx to a **stable, consistent, and ergonomic scripting language**. Version 4.0.1 removes disruptive features, fixes critical bugs, and introduces **syntax alignment** to unify and simplify how code is written across the language.

---

## Removed Experimental Features

* **PSOP (Prototype Space-Oriented Programming):** The `namespace` prototypes, `clone()` instantiation, and `space` keyword have been removed.
* **Dot-Notation Assignment:** Direct member assignment using `.` has been reverted to the prior model.
* **Experimental Keywords:** All constructs introduced in 4.0.0 that broke syntax consistency have been eliminated.

---

## Bug Fixes & Improvements

1. **Parser Crash &mdash; `load` Statement**

   * Fixed a crash when `load` did not use the required `libs.` or `local.` prefix.
   * The parser now displays a clear, actionable error message.

2. **Error Message Consistency**

   * Unified error message style for all interpreter errors.
   * Messages are concise, consistent, and include suggested fixes.

3. **Runtime Stability**

   * Fixed crashes in recursive function calls under deep call chains.
   * Optimized memory handling for large strings to prevent freezes.

---

## Syntax Alignment

To ensure long-term maintainability, this release standardizes several aspects of Zerionyx syntax:

* **Conditionals:** All `if / else` must use explicit block form.

  ```zyx
    # Before
    if x > 0 do
        println("positive")
    else
        println("negative")
    done

    # Now
    if x > 0 do
        println("positive")
    else do
        println("negative")
    done
  ```

---

Zerionyx 4.0.1 is a **reset and refinement release**: stable, predictable, and consistent. By removing experimental paradigms and unifying the syntax, it ensures developers can write, read, and maintain code with confidence.