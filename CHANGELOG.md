# Changelog: Version 5.0.1-LTS — Stability & Fixes

**Date:** August 31, 2025

Zerionyx 5.0.1-LTS is the first Long-Term Support (LTS) patch release for the 5.0.x series.
This update focuses on stability by fixing critical issues discovered in 5.0.0, ensuring smoother adoption of the asynchronous engine for production workloads.

---

## 🛠 Bug Fixes

* **Correct Float (`cfloat`)**
  Fixed precision errors in `cfloat` arithmetic where certain operations produced incorrect rounding in edge cases. Calculations are now consistent with the IEEE 754 standard.

* **Decorators Library**
  Resolved multiple issues in `libs.decorators`:

  * Decorators failing to apply on `async defun` are now correctly supported.
  * Nested decorators no longer cause unexpected stack overflows.
  * Error messages are clearer when applying invalid decorators.

---

## 📦 Distribution Note

This patch release follows the same cleaned packaging policy as **5.0.0**, keeping only runtime essentials for end-users while removing development clutter.

---

Zerionyx 5.0.1-LTS brings improved reliability, making it the recommended version for anyone deploying applications built on the asynchronous runtime.
