# Changelog: Version 5.0.3-LTS — Async Console & Python Interop

**Date:** September 1, 2025

Zerionyx 5.0.3-LTS is the third Long-Term Support (LTS) release in the 5.0.x series.
This update focuses on **asynchronous console utilities** and **Python interoperability**, making interactive programs and scripting even more seamless in async workflows.

---

## ✨ New Features

* **`libs.asyncio` Console Expansion**
  Added powerful new coroutine-based console and execution utilities:

  * **input(prompt="")** → Asynchronously reads a line of text from the console without blocking the event loop
  * **get\_password(prompt="")** → Asynchronously and securely reads a password from the console without echoing input
  * **println(value="")** → Asynchronously prints a value to the console, followed by a newline
  * **print(value="")** → Asynchronously prints a value to the console without a trailing newline
  * **clear()** → Asynchronously clears the console screen

* **Python Interop**

  * **pyexec(code, args={})** → Asynchronously executes a block of Python code in a separate thread and returns the resulting environment

---

## 🛠 Bug Fixes

* **Async File I/O**

  * Fixed rare race condition when two coroutines attempted to write to the same file concurrently.
  * Improved error messages for missing file permissions in `asyncio.read()` and `asyncio.write()`.

* **Networking**

  * Fixed `asyncio.downl()` incorrectly timing out on slow but active connections.

---

Zerionyx 5.0.3-LTS strengthens async support for **interactive apps, secure console input, and embedded Python execution**, expanding the possibilities for developers building modern async-first applications.
