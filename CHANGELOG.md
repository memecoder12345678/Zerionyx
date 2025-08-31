# Changelog: Version 5.0.0 — The Asynchronous Update

**Date:** August 31, 2025

Zerionyx 5.0.0 marks a monumental leap forward by introducing a complete asynchronous programming model to the language. This release brings first-class `async/await` syntax, enabling developers to write highly efficient, non-blocking code for I/O-bound operations like network requests, file access, and concurrent task management.

This update is designed to feel intuitive and powerful, integrating seamlessly with the existing language features while unlocking new possibilities for performance and responsiveness.

---

## ✨ Major New Features

### 1. Asynchronous Functions (`async defun`)

You can now declare non-blocking functions, known as coroutines, using the new `async defun` syntax. Calling an `async` function does not execute it immediately; instead, it returns a special `coroutine` object, ready to be run by the event loop.

```zyx
load "libs.asyncio"

# Defines a coroutine that waits for 1 second before returning a value.
async defun get_user_data()
    println("(Task: fetching user data...)")
    await asyncio.sleep(1) # This pauses the function without blocking the program
    return {"id": 101, "name": "Alex"}
done
```

### 2. The `await` Expression

The `await` keyword is used to pause the execution of a coroutine and wait for another coroutine to complete. It can only be used inside an `async` function. This is the core mechanism that allows the event loop to run other tasks while one is waiting.

```zyx
async defun main()
    println("Calling the async function...")
    let user_data_coro = get_user_data() # This returns a coroutine object

    println("Awaiting the result...")
    let data = await user_data_coro # Execution pauses here until get_user_data is done
    
    println("Result received: ")
    print(data)
done

# The top-level 'await' starts the main coroutine
await main()
```

### 3. Concurrent Task Execution with `asyncio.gather`

To unlock the full power of `async`, the new built-in function `asyncio.gather` runs a list of coroutines concurrently. It starts all of them at once and waits for them all to finish, returning a list of their results. The total time taken is determined by the longest-running coroutine, not the sum of all durations.

```zyx
load "libs.time"
load "libs.math"
load "libs.asyncio"

async defun task(name, duration)
    await asyncio.sleep(duration)
    return "Task '" + name + "' finished."
done

async defun run_concurrently()
    let start = time.time()
    
    let results = await asyncio.gather([
        task("A", 2),
        task("B", 1),
        task("C", 3)
    ])
    
    let duration = time.time() - start
    
    # Total time will be ~3 seconds, not 6 seconds.
    println("All tasks completed in ~" + to_str(math.round(duration)) + "s")
    println(results)
done

await run_concurrently()
```

---

## 🐞 Other Changes & Improvements

*   **New Keywords:** Added `async` and `await` to the language grammar.
*   **New Data Type:** Introduced the internal `<coroutine>` object type.
*   **New library**: Added `libs.asyncio` with event loop, tasks, and coroutine utilities.
*   **Interpreter Core:** The entire interpreter engine has been upgraded to be asynchronous, enabling the event loop to manage the execution stack.
*   **Error Handling:** Tracebacks and error messages have been improved to provide clear context when exceptions occur within `async` functions or during an `await`.

---

Zerionyx 5.0.0 fundamentally changes how concurrent code can be written, making it easier than ever to build fast, scalable, and responsive applications.
