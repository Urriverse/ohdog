![embarrassed_dog](docs/src/assets/embarrassed_dog.png)

# Oh, Dog!

**Oh, Dog!** (Over-engineered static Html DOcument Generator) is a lightweight CLI tool
that turns Markdown into static HTML pages. It supports macros (custom Python snippets inside
your Markdown), dependency management (fetch documentation bases from GitHub), and multi-page
sites – all with a simple workflow.

## Installation

Build it with [build.py](https://github.com/Urriverse/build-py) utility and install as you want, there aren't limits.
Python 3.13+ required.

## Quick Example

```bash
# Create a new project
ohdog init my-doc
cd my-doc

# Edit src/index.md (Markdown with optional macros)

# Build the HTML
ohdog build
```

Your document is now in `out/my-doc/index.html`.

## Basic Commands

- `ohdog init [path]` – initialize a new document
- `ohdog build [path]` – build the project into HTML
- `ohdog vendor [path]` – copy all dependency assets and macros into your project

## Dependencies

List GitHub repositories in `OhDog.toml` under `[general].requires`.  
Run `ohdog vendor` to fetch and copy their assets/macros.

## Macros

Place Python files in `macros/` – each file must define a `macro(content: str) -> str` function.  
Use them in Markdown like:
```
#[mymacro] content goes here [mymacro]#
```

## Multi‑page Mode

Set `mode = "multipage"` in `OhDog.toml` and provide a `_multipage` macro to generate multiple output files.

## Full Documentation

For detailed usage, configuration, macro writing, and advanced features, see the [complete guide](docs/src/index.md) (or the `docs/` folder in this repository).

---

MIT License
