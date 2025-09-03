# Changelog: Version 5.0.4 — Multiple Assignment & New Concurrency Model

**Date:** September 3, 2025

Zerionyx 5.0.4 is the first stable release after the 5.0.x LTS line. This update introduces a **simplified variable model**, powerful **multiple assignment syntax**, and revamps concurrency by replacing `async` with a robust **thread pool system**.

---

## ✨ New Features

*   **Multiple Assignment**

    You can now assign multiple variables from **lists or values** in a single line:

    ```zyx
    a, b, c = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    x, y, z = 1, 2, 3
    ```

*   **Introduction of Thread Pools**

    Concurrency in Zerionyx has been supercharged with the introduction of a built-in thread pool, accessible via the `threading` library. This provides an efficient way to manage and execute multiple tasks in parallel without the overhead of creating new threads for each task.

    ```zyx
    threading = load("libs.threading")

    pool = threading.pool.new(4) # Create a pool of 4 worker threads
    future = threading.pool.submit(pool, my_long_running_task, [arg1, arg2])

    # Continue other work...

    # Get the result later (this will wait if the task isn't done)
    value, err_msg, err_type = threading.pool.result(future)
    ```

---

## 💥 Breaking Changes & Removals

*   **Unified Variable Declaration**

    The **`let` keyword has been removed**. Variables are now declared and assigned directly with `=` for a **cleaner, more Pythonic experience**:

    ```zyx
    # Before
    let x = 10  

    # Now
    x = 10  
    ```

*   **Removal of `async` Keyword**

    The `async` keyword and its related functionality have been removed. This change simplifies Zerionyx's concurrency model, consolidating all asynchronous and parallel operations under the new, more powerful `threading` library. All asynchronous tasks should now be implemented using the thread pool for better performance and control.

---

Zerionyx 5.0.4 enhances **developer ergonomics** with **multiple assignment**, a **simplified variable model**, and a unified, powerful **new concurrency model** built around threads.