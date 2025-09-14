# Changelog: Version 5.0.5 — Bug Fixes, Type Checks & Decorator Overhaul

**Date:** September 7, 2025

Zerionyx 5.0.5 introduces critical **bug fixes**, new **runtime type-check utilities**, and a **revamped decorator syntax**. This release focuses on **stability** and **developer ergonomics**.

---

## 🐞 Bug Fixes

* Fixed an issue in **`threading.pool.result()`** where completed futures sometimes returned `None`.
  Now consistently return `value`.

---

## ✨ New Features

* **New Type Check Functions**
  Added built-in helpers for runtime validation:

  ```zyx
  is_thread_pool(x)   -> bool   # Check if x is a thread pool
  is_future(x)        -> bool   # Check if x is a future
  is_namespace(x)     -> bool   # Check if x is a namespace
  ```

  **Example:**

  ```zyx
  pool = threading.pool.new(2)
  println(is_thread_pool(pool))  # true
  ```

---

## 💥 Breaking Changes

* **Decorator Syntax Change**
  The decorator symbol has been changed from `@` to `&` for a cleaner and more consistent style.

  ```zyx
  load "libs.decorators"

  &decorators.cache
  defun fib(n)
      if n < 2 do
          return n
      done
      a = 0
      b = 1
      for i = 1 to n do
          temp = b
          b = a + b
          a = temp
      done
      return b
  done

  println("Fib(40) with cache...")

  &decorators.measure_time
  defun cached_fib() -> fib(40)
  println(cached_fib())
  println(cached_fib())
  ```

---

## 📌 Summary

Zerionyx 5.0.5 brings:

* Stability improvements with **bug fixes**
* Handy **type-check helpers** (`is_thread_pool`, `is_future`, `is_namespace`)
* A **new decorator syntax** with `&`

This release smooths out rough edges and makes the language more **consistent** and **developer-friendly**.

