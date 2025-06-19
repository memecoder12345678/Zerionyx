<p align="center">
  <img src="docs/favicon.ico" alt="Zerionyx Logo" width="150" />
  <h1 align="center">Zerionyx Programming Language</h1>
  <p align="center">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-00ffcc?style=for-the-badge&logo=Open%20Source%20Initiative" alt="License" /></a>
    <img src="https://img.shields.io/badge/build-passing-00ffcc?style=for-the-badge&logo=githubactions" alt="Build Status" />
    <img src="https://img.shields.io/badge/python-3.11%2B-00ffcc?style=for-the-badge&logo=python" alt="Python 3.11+" />
    <img src="https://img.shields.io/badge/Zerionyx-v2.2.9-00ffcc?style=for-the-badge&logo=lightning" alt="Zerionyx v2.2.9" />
  </p>
</p>

---

## Overview

**Zerionyx** is an educational programming language built in Python, designed for **learning** and **lightweight task automation**. It offers:

* Beginner-friendly syntax
* Immediate visual feedback and clear error diagnostics
* Built-in libraries (math, algorithms, data structures)
* File handling and scripting support
* Lightweight yet expressive—ideal for teaching and prototyping

---

## Why Zerionyx?

* **Great for learners** who want to understand programming fundamentals
* **Perfect for educators** to create interactive demos and tools
* **Not suited** for high-performance or production-scale applications

---

## Interactive Shell Demo

<p align="center">
  <img src="demo.svg" alt="Zerionyx Interactive Shell Demo" />
</p>

---

## Features

* Intuitive and consistent syntax
* Educational standard libraries (e.g., math, algorithms)
* Visual error diagnostics to help learners
* File I/O and automation commands
* Interactive shell with REPL support

---

## Code Samples

```ruby
# Hello World
println("Hello, World!")

# Arithmetic
x = 10
y = 20
println(x + y)

# Function definition
defun add(a, b)
    return a + b
done

# One-line function
defun add(a, b) -> a + b

println(add(5, 3))

# Lists
nums = [1, 2, 3, 4, 5]
println(nums)
```

---

## Getting Started

### 1. Clone this repo

```bash
git clone https://github.com/memecoder12345678/Zerionyx.git
cd Zerionyx
```

### 2. Run a Zerionyx script

```bash
python ./interpreter/Zerionyx.py examples/demo.zer
```

### 3. Launch interactive shell

```bash
python ./interpreter/Zerionyx.py
```

Then type commands like `grammar`, `license`, etc.

### 4. Full Documentation

👉 [Zerionyx Docs](https://memecoder12345678.github.io/Zerionyx/docs.html)

---

## Recommended Setup

* **Python 3.11+** for best compatibility
* **PyPy 3.11** for faster performance (optional)
* Use with **Zerionyx Editor** for syntax highlighting (**recommended**)

---

## Contributing

Contributions are welcome! To get involved:

1. Fork the repo
2. Branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Describe feature"`
4. Push & open a Pull Request 🎉

---

## Acknowledgments

Thanks to the open-source makers and template authors (Owne Readme, Jeff Nyman) for README inspiration ([github.com][2], [en.wikipedia.org][1], [makeareadme.com][3]).

---

## License

Zerionyx is released under the **MIT License**. See [LICENSE](LICENSE).

---

## Contact

* GitHub: [memecoder12345678](https://github.com/memecoder12345678)
* Docs: [memecoder12345678.github.io/Zerionyx](https://memecoder12345678.github.io/Zerionyx)

---
[1]: https://en.wikipedia.org/wiki/README?utm_source=chatgpt.com "README"
[2]: https://github.com/jehna/readme-best-practices?utm_source=chatgpt.com "Best practices for writing a README for your open source project - GitHub"
[3]: https://www.makeareadme.com/?utm_source=chatgpt.com "Make a README"
