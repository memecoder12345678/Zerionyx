# Zerion Programming Language

Zerion is an educational programming language designed for learning and task automation.

## Features

- Beginner-friendly syntax perfect for learning
- Clear error messages and helpful debugging
- Extensive libraries for common automation tasks
- Built-in tools for file handling and system tasks
- Educational math and algorithm libraries
- Simple I/O operations for automation scripts

## Best Use Cases

- Learning programming concepts
- Teaching children to code
- Automating repetitive tasks
- Basic system administration
- Educational projects and exercises

## Example

```ruby
# Hello World
println("Hello, World!")

# Simple automation example
load "libs.file"
defun create_backup(file)
    copy(file, to_str(file) + ".bak")
    println("Backup created: " + file + ".bak")
done

# Math learning example
defun is_even(n)
    return n % 2 == 0
done
```

## Performance Note

- Use Python 3.11.9+ for learning and basic tasks
- For faster automation tasks, use PyPy 3.11.11
- Not recommended for computation-heavy applications

## Website

Visit the official Zerion website for an introduction and more information: [Zerion Language Website](https://memecoder12345678.github.io/zerion/)

## Installation

1. Clone the repository
2. Add zerion to your PATH
3. Run zerion files with `python zerion.py file.zer`

## Documentation

Full documentation is available at [Zerion Documentation Website](https://memecoder12345678.github.io/zerion/docs.html)

## License

MIT License - feel free to use and modify as you like
