# Changelog: Version 5.0.4 — Multiple Assignment

**Date:** September 3, 2025

Zerionyx 5.0.4 is the first stable release after the 5.0.x LTS line.
This update introduces **multiple assignment syntax**, removes the legacy **`let` keyword**, and expands async console utilities for more fluid interactive scripting.

---

## ✨ New Features

* **Multiple Assignment**

  You can now assign multiple variables from **lists or values** in a single line:

  ```zyx
  a, b, c = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
  x, y, z = 1, 2, 3
  ```

* **Unified Variable Declaration**

  The **`let` keyword has been removed**.
  Variables are now declared and assigned directly with `=` for a **cleaner, more Pythonic experience**:

  ```zyx
  # Before
  let x = 10  

  # Now
  x = 10  
  ```

---

Zerionyx 5.0.4 enhances **developer ergonomics** with **multiple assignment** and a **simplified variable model**.

