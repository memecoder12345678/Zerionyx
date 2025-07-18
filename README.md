<p align="center">
  <img src="docs/favicon.ico" alt="Zerionyx Logo" width="200" />
  <h1 align="center">Zerionyx Programming Language</h1>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.11%2B-00ffcc?style=for-the-badge&logo=python" alt="Python 3.11+" />
    <img src="https://img.shields.io/badge/donate-Monero-00ffcc?style=for-the-badge&logo=monero" />
    <img src="https://img.shields.io/badge/Zerionyx-v2.4.6-00ffcc?style=for-the-badge&logo=lightning" alt="Zerionyx v2.2.9" />
    <img src="https://img.shields.io/badge/build-passing-00ffcc?style=for-the-badge&logo=githubactions" alt="Build Status" />
    <img src="https://img.shields.io/github/contributors/memecoder12345678/Zerionyx?style=for-the-badge&color=00ffcc">
    <img src="https://img.shields.io/github/stars/memecoder12345678/Zerionyx?style=for-the-badge&color=00ffcc">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-00ffcc?style=for-the-badge&logo=Open%20Source%20Initiative" alt="License" /></a>
  </p>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Why Zerionyx?](#why-zerionyx)
- [Interactive Shell Demo](#interactive-shell-demo)
- [Features](#features)
- [Code Samples](#code-samples)
- [Getting Started](#getting-started)
- [Recommended Setup](#recommended-setup)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Looking for Contributors](#looking-for-contributors)
- [Support Zerionyx 💸](#support-zerionyx-)
- [Acknowledgments](#acknowledgments)
- [License](#license)
- [Contact](#contact)

---

## Overview

**Zerionyx** is an educational programming language built in Python, designed for **learning** and **lightweight task automation**.  
Designed to be minimal yet powerful &mdash; **Zerionyx bridges the gap between learning and real-world scripting.**

It offers:

* Beginner-friendly syntax  
* Immediate visual feedback and clear error diagnostics  
* Built-in libraries (math, algorithms, data structures)  
* File handling and scripting support  
* Lightweight yet expressive &mdash; ideal for teaching and prototyping

---

## Why Zerionyx?

* **Great for learners** who want to understand programming fundamentals  
* **Perfect for educators** to create interactive demos and tools  
* **Optimized for simplicity over performance** &mdash; not intended for large-scale production systems

---

## Interactive Shell Demo

<p align="center">
  <img src="imgs/demo.svg" alt="Zerionyx Interactive Shell Demo" />
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
print("Hello, World!\n")

# Arithmetic
x = 10
y = 20
println(x + y)
println(x - y)
println(x * y)
println(x / y)
println(x % y)
println(x // y)
println(x ^ y)

# Function definition
defun add(a, b)
    return a + b
done

# One-line function
defun add(a, b) -> a += b

println(add(5, 3))

# Lists
nums = [1, 2, 3, 4, 5]
println(nums)
println((nums>0))
println((nums>4))

# HashMaps
users = {"name": "admin", "password": "admin"}
println(users)
println((users>"name"))
println((users>"password"))

# Bytes
str_enc = to_bytes(to_hex("Hello, World!"))
println(to_str(str_enc))
println((str_enc>0))
println((str_enc>4))

# PyObject
os = pyexec("import os", {})
println(type(os))
r = pyexec("os.system('echo Hello, World!')", {os})

# Conditional
if x > y do
    println("X is greater")
elif x < y do
    println("Y is greater")
else
    println("X is equals to Y")
done

# For-in loop
for i in nums do
    println(i)
done

# For loop
for i = 1 to 11 do
    println(i)
done

# While loop
a = 100
while a < 100 do
    a -= 1
done
println(a)

# NameSpace
namespace m
    pi = 3.14
    defun area(r) -> pi * r * r
done

println(m.area(5))
```

For more examples, check the [`tests`](tests) folder for a full overview.

---
## Getting Started

### 1. Clone this repo

```bash
git clone https://github.com/memecoder12345678/Zerionyx.git
cd Zerionyx
```

### 2. Install required packages

```bash
python -m pip install -r requirements.txt
```

### 3. Run a Zerionyx script

```bash
python zerionyx.py tests/HaloWorld.zer
```

### 4. Launch interactive shell

```bash
python zerionyx.py
```

Use commands such as `grammar`, `license`, etc. for more details.

### 5. Full Documentation

👉 [Zerionyx Docs](https://memecoder12345678.github.io/Zerionyx/docs.html)

---

## Recommended Setup

* **Python 3.11+** for best compatibility
* **PyPy 3.11** for faster performance (optional)

---

## Roadmap

* [x] Add basic REPL and shell commands
* [x] Add algorithms & data structure libraries
* [X] Integrate debugger support
* [X] Improving interpreter performance 
* [ ] Creating developer tools (debuggers, profilers, code formatters)
* [ ] Creating **VS Code plugin**
---

## Contributing

Contributions are welcome! To get involved:

1. Fork the repo
2. Branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Describe feature"`
4. Push & open a Pull Request 🎉

---

## Looking for Contributors

Zerionyx is growing fast &mdash; and we're looking for awesome people to help shape its future.

We're especially looking for contributors interested in: 
  
- Writing test suites and improving interpreter performance  
- Creating developer tools (debuggers, profilers, code formatters)  

**Requirements?**  

> No strict rules &mdash; if you're passionate about compilers, VMs, or language design, join in!

### How to join:

1. Fork the repo & check open issues  
2. Pick a task or open a proposal  
3. Join the project by opening a Pull Request  
4. Or reach out via [GitHub issues](https://github.com/memecoder12345678/Zerionyx/issues)

Let’s make Zerionyx better, together 💚

---
## Support Zerionyx 💸

If you find this project useful and want to support its development **anonymously and securely**, you can donate via **Monero (XMR)**:

**Monero Address:**  
```
49vK21oktPG6TXymtpzPNcWh9u2nBCJ4v9wcX2Xo5iWJf8p4ZFBVhv6Y2SLo6qxCmsPMi3Q14RcXsf8USjtrgmyzJubFfpm
```

**Monero QR:**  
<p align="center">
  <img src="imgs/qr.png" alt="Monero Donation QR Code" width="200"/>
</p>

> Use wallets like [Feather Wallet](https://featherwallet.org/) or [Monero GUI](https://www.getmonero.org/downloads/) to send donations.



---
## Acknowledgments

Thanks to the open-source makers and template authors (Owne Readme, Jeff Nyman) for README inspiration ([github.com][2], [en.wikipedia.org][1], [makeareadme.com][3]).

---

## License

Zerionyx is released under the **MIT License**. See [LICENSE](LICENSE).

---

## Contact

* GitHub: [memecoder12345678](https://github.com/memecoder12345678)
* Official website: [memecoder12345678.github.io/Zerionyx](https://memecoder12345678.github.io/Zerionyx)
* Docs: [memecoder12345678.github.io/Zerionyx/docs.html](https://memecoder12345678.github.io/Zerionyx/docs.html)

[1]: https://en.wikipedia.org/wiki/README "README"
[2]: https://github.com/jehna/readme-best-practices "Best practices for writing a README for your open source project - GitHub"
[3]: https://www.makeareadme.com/ "Make a README"
