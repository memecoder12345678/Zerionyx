# Pseudo-OOP Design Philosophy in Zerionyx

## Overview

Zerionyx does not implement classical Object-Oriented Programming (OOP).  
Instead, it provides a **module-based logical structure** that mimics OOP-like organization, while remaining fundamentally procedural and stateless unless explicitly managed.

This document outlines the design philosophy, usage patterns, and conventions behind the **Pseudo-OOP** model in Zerionyx.

---

## Objectives

- Organize logic into clearly separated modules
- Enable structured and readable function access
- Allow entrypoint-based initialization
- Simulate object-like behavior without instantiations
- Preserve simplicity by avoiding class and inheritance hierarchies

---

## Core Concepts

| Concept             | Zerionyx Term           | Similar OOP Concept          |
|---------------------|-------------------------|------------------------------|
| Logical group        | `module`                | `class`                      |
| Initialization       | `__start__()`           | constructor (`__init__`)     |
| Function inside module | `component`           | method                       |
| Global state         | `dependency`            | field / attribute            |
| Parameters           | `inputs`                | parameters                   |
| Function call        | `module>func(args)`     | `object.method(args)`        |

---

## Calling Convention

External component access is done via the `>` operator:

```zerionyx
math>sqrt(49)
````

This accesses the `sqrt` component inside the `math` module.

---

## Module Inclusion with `load`

Zerionyx uses the `load` keyword to include external modules into the current source file.

```zerionyx
load "math"
```

Unlike dynamic import systems in other languages, `load` in Zerionyx behaves **exactly like `#include` in C** — it **injects the contents of the target file directly** into the source code at compile time. No namespace isolation is performed by default.

This design decision emphasizes performance, transparency, and compilation simplicity, at the cost of requiring clear module boundaries by convention.

---

## Behavioral Guidelines

* Each module may define a `__start__()` function as an optional entrypoint.
* Components (functions) may be accessed internally or externally using `module>name()`.
* Dependencies (module-level variables) act as internal shared state.
* All parameters passed to components are referred to as **inputs**.
* Modules must be loaded via `load` before being accessed.

---

## Use Cases

* Grouping related logic into maintainable modules
* Simulating encapsulated behavior without object instantiation
* Sharing common data across components using dependencies
* Building structured programs with minimal abstraction overhead

---

## Recommended Conventions

* Treat dependencies as controlled shared state — avoid uncontrolled mutation
* Place initialization logic inside `__start__` if needed
* Use consistent naming for components and dependencies
* Limit the size and scope of each module to preserve modularity

---

## Zen of Pseudo-OOP (Zerionyx Edition)

> * Modules are better than classes for clarity and control.
> * Functions are better than methods for flexibility.
> * Explicit access (`module>func`) is better than implicit resolution.
> * Initialization should be optional, not enforced.
> * Load what you need, structure what you load.
> * Composition over inheritance.
> * State should be managed, not hidden.
> * Structure matters more than syntax.

---

## Closing Notes

Zerionyx’s Pseudo-OOP model is a pragmatic, lightweight approach to program structure.
It emphasizes **modularity, explicitness, and performance** over traditional abstraction, while still offering familiar organizational patterns for developers coming from OOP backgrounds.

> "Object-oriented thinking, module-oriented execution."
