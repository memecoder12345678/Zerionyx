# Changelog: Version 4.0.2 &mdash; The Data Toolkit & Refinement Update

**Date:** August 26, 2025

Building on the stability established in v4.0.1, this release expands Zerionyx's utility by introducing modern data handling tools and continuing to refine the interpreter's reliability and security. This update is focused on empowering developers with more robust tools for real-world scripting.

---

## New Features

### 1. Introducing the `json` Standard Library

To meet the growing demand for data interchange, the `json` library is now an official part of the Zerionyx standard library. You can now effortlessly parse and stringify JSON data—a critical feature for working with web APIs, configuration files, and modern automation tasks.

*   **`json.parse(string)`:** Converts a JSON string into a Zerionyx `hashmap` or `list`.
*   **`json.stringify(object)`:** Converts a `hashmap` or `list` into a JSON string.

```zyx
# Usage Example
load "libs.json"

# Parse a JSON string
user_json = '{"name": "memecoder", "projects": ["Zerionyx", "DCry"]}'
user_data = json.parse(user_json)
println("Welcome, " + user_data$"name")

# Stringify a hashmap
new_data = {"status": "active", "version": 4.0.2}
json_string = json.stringify(new_data)
println("Current status: " + json_string)
```

---

## 🐞 Bug Fixes & Improvements

1.  **Interpreter Security &mdash; Hidden Attribute Protection**
    *   Fixed a critical vulnerability where internal interpreter-managed attributes (e.g., internal object metadata) could be accessed and potentially modified from user scripts, which could lead to unexpected behavior or crashes.
    *   Access to these internal properties is now properly restricted, ensuring a more stable and secure execution environment.

2.  **Enhanced Type Error Diagnostics**
    *   Error messages for type mismatches (e.g., adding a string to a number) now provide more context, including the types of both operands involved, making debugging faster and more intuitive for learners.

3.  **Performance Tune-up for `HashMap`**
    *   Optimized the underlying implementation of `HashMap` for faster key lookups and insertions, resulting in a noticeable performance improvement in scripts that heavily rely on dictionary-like objects.

---

Zerionyx 4.0.2 marks a significant step forward in scripting capability. By introducing a vital data-handling tool like the `json` library and hardening the interpreter's core, this release empowers users to build more complex and reliable automation scripts with confidence.