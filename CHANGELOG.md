# Changelog: Version 4.0.5 — **Concurrency & Reliability Update**

**Date:** August 29, 2025

Zerionyx 4.0.5 focuses on improving concurrency primitives and overall runtime reliability. This release adds a first-class `channel` library for safe thread communication, introduces a new `is_close` function in `libs.math` for robust floating-point comparison, and fixes several correctness and stability issues (deep copy, threading startup, floating-point behavior, and numeric comparisons).

---

## ✨ New Features

### Channel library (`libs.channel`)

A simple, safe message-passing primitive for thread-to-thread communication. Channels make it easy to send and receive values between threads without manual locking.

```zyx
load "libs.threading"
load "libs.channel"
load "libs.time"

println("--- Channel Demo ---")

let messages = channel.new()

defun worker()
    println("  (Worker thread started)")
    time.sleep(2)
    println("  (Worker sending message: 'Hello from thread!')")
    channel.send(messages, "Hello from thread!")

    time.sleep(1)
    println("  (Worker sending message: 'Work done.')")
    channel.send(messages, "Work done.")
    println("  (Worker thread finished)")
done

println("Main: Starting worker thread...")
let t = threading.start(worker)

println("Main: Waiting to receive a message...")
let msg1 = channel.recv(messages)
println("Main: Received -> " + to_str(msg1))

println("Main: Waiting for the next message...")
let msg2 = channel.recv(messages)
println("Main: Received -> " + to_str(msg2))

threading.join(t)
println("--- Demo Finished ---")
```

### Floating-point comparison (`libs.math.is_close`)

A new utility function to compare two floating-point numbers with tolerance. This prevents false negatives from rounding errors.

```zyx
load "libs.math"

println(math.is_close(0.1 + 0.2, 0.3))     # true
println(math.is_close(1.0000000001, 1.0))  # true  
println(math.is_close(1.1, 1.2))           # false
```

---

## 🐞 Bug Fixes & Improvements

* **List deep-copy fix:** Fixed an issue where copying lists could drop or omit elements — deep copies now preserve full data and internal structure.
* **Threading `start` stability:** Fixed bugs in `libs.threading` that caused `start` to behave inconsistently or fail in edge cases. Thread startup and lifecycle handling are now more robust.
* **Added `libs.channel`:** New standard library for channel-based message passing between threads.
* **Added `math.is_close`:** New floating-point comparison function with tolerance to handle rounding errors reliably.
* **Floating-point fixes:** Corrected floating-point handling bugs that caused incorrect results or instability in numeric operations.
* **Numeric comparison fix:** Fixed edge cases in numeric comparisons so equality/ordering behaves correctly across integer/float boundaries.

---

Zerionyx 4.0.5 tightens concurrency primitives and hardens numeric behavior — a practical release that makes parallel code safer and numerical logic more reliable.
