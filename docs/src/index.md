<!-- this documentation is one-file and without macros, so it's pure markdown --->

# Oh, Dog! – Full Documentation

**Oh, Dog!** (Over‑engineered static Html DOcumentation Generator) is a command‑line tool that builds static HTML documentation from Markdown files. It is designed to be flexible, extensible, and dependency‑aware.

---

## Table of Contents

- [Oh, Dog! – Full Documentation](#oh-dog--full-documentation)
- [Table of Contents](#table-of-contents)
- [Project Structure](#project-structure)
- [Commands Reference](#commands-reference)
  - [`ohdog init [path]`](#ohdog-init-path)
  - [`ohdog build [path]`](#ohdog-build-path)
  - [`ohdog vendor [path]`](#ohdog-vendor-path)
- [Configuration (`OhDog.toml`)](#configuration-ohdogtoml)
  - [`[general]`](#general)
  - [Writing Content](#writing-content)
    - [Markdown Basics](#markdown-basics)
    - [Macros](#macros)
    - [Custom Macros in Python](#custom-macros-in-python)
  - [Dependencies](#dependencies)
    - [Specifying Dependencies](#specifying-dependencies)
    - [The `vendor` Command](#the-vendor-command)
    - [Dependency Resolution & Priority](#dependency-resolution--priority)
  - [Multi‑page Sites](#multipage-sites)
  - [Assets & Styling](#assets--styling)
  - [Error Handling & Logging](#error-handling--logging)
  - [Examples](#examples)
    - [Minimal Project](#minimal-project)
    - [Using a Dependency](#using-a-dependency)
    - [Multi‑page with Custom Layout](#multipage-with-custom-layout)
  - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)

---

## Project Structure

A typical Oh, Dog! project has the following layout:

```
my-docs/
├── OhDog.toml          # Project configuration
├── src/
│   └── index.md        # Main Markdown file (for standalone mode)
├── assets/
│   ├── style.css       # Optional custom CSS
│   └── script.js       # Optional custom JavaScript
├── macros/             # Custom macro Python files
│   └── mymacro.py
└── out/                # Generated HTML (created on build)
    └── my-docs/
        └── index.html
```

When you add dependencies and run `vendor`, additional files may be copied into `assets/` and `macros/`.

---

## Commands Reference

All commands accept a `project_dir` argument (defaults to current directory).

### `ohdog init [path]`

Initializes a new project in the given directory. Creates:

- `OhDog.toml` with basic configuration.
- `src/index.md` with a welcome message.
- `assets/`, `macros/`, and `src/` directories.
- A `.gitignore` that excludes cache and output directories.

**Options:**

- `--from <deps...>` – pre‑populate the `requires` list with one or more dependencies.
- `-f, --force` – overwrite existing files.

Example:
```bash
ohdog init my-cool-docs --from urriverse/hsb-theme urriverse/hsb-charts
```

### `ohdog build [path]`

Compiles the project to HTML. Reads `OhDog.toml` and processes Markdown.

**Options:**

- `--no-cache` – force re‑download all dependencies (ignores cached copies).

The output is placed in `out/<project-name>/`. If `mode = "multipage"` is set, the `_multipage` macro controls the output; otherwise, a single `index.html` is generated from `src/index.md`.

### `ohdog vendor [path]`

Fetches all dependencies listed in `OhDog.toml` and copies their `assets/` and `macros/` into your project (with priority ordering). It also optionally copies the dependency’s `src/index.md` to your project if it doesn’t already exist.

**Options:**

- `-f, --force` – overwrite existing files.
- `--no-cache` – force re‑download all bases.

After vendoring, the `requires` list in `OhDog.toml` is cleared (to avoid endless re‑fetching) – the dependencies are now vendored locally.

---

## Configuration (`OhDog.toml`)

The configuration file is written in [TOML](https://toml.io). It supports two main sections:

### `[general]`

| Key          | Type     | Default              | Description |
|--------------|----------|----------------------|-------------|
| `title`      | string   | Project directory name | The HTML `<title>` and displayed title. |
| `name`       | string   | Project directory name (lowercased) | Used as the output subdirectory name. |
| `mode`       | string   | `"standalone"`        | Set to `"multipage"` for multi‑page output (requires a `_multipage` macro). |
| `requires`   | list of strings | `[]` | GitHub repository names (e.g., `"user/repo"`). They are fetched and used as dependencies. |

**Example:**
```toml
[general]
title = "My Awesome Docs"
name = "awesome-docs"
mode = "multipage"
requires = ["urriverse/hsb-theme", "john/hsb-extras"]
```

> **Note:** After running `vendor`, the `requires` list will be emptied. This is intentional: the assets and macros are now part of your project, so you no longer need the remote dependencies.

---

## Writing Content

### Markdown Basics

Oh, Dog! uses the [Python Markdown](https://python-markdown.github.io/) library with the **Extra** and **Sane Lists** extensions. This gives you:

- Tables
- Definition lists
- Fenced code blocks
- Footnotes
- And more.

Write your main documentation in `src/index.md` (or elsewhere if using a macro).

### Macros

Macros are custom blocks that are replaced with HTML. They are defined in Python files and invoked in your Markdown with special tags.

**Syntax:**

```markdown
#macroname
Content that will be passed to the macro.
#/macroname
```

The macro receives the content as a string and must return an HTML string (which is inserted directly into the page, without further Markdown processing).

#### Built‑in Macros

Oh, Dog! comes with one built‑in macro, **`include_macro`**, which is only available inside other macros (not from Markdown directly). It allows you to retrieve a macro from a **specific** dependency, bypassing the normal priority order. This is useful when several dependencies provide macros with the same name and you need a particular version.

Usage inside a Python macro:

```python
def macro(content: str) -> str:
    # Get the "button" macro from the "john/hsb-extras" dependency
    button = include_macro('john/hsb-extras', 'button')
    if button is None:
        return '<p>Button macro not found</p>'
    return button(content)
```

You can also use it via the global `MACROS` dictionary: `MACROS['include_macro']('dep', 'name')`. Both forms work because `include_macro` is injected as a global.

#### Special Macros

Macros whose filename starts with an underscore (`_`) are treated as **special macros**. They are not invoked directly in Markdown but are used by the build system:

- **`_head`** – receives `(title, css_content, js_content)` and should return the full `<head>` HTML. If not provided, a default head is generated.
- **`_page`** – receives `(title, head_content, body_content, js_content)` and should return the complete HTML document. If not provided, a default page skeleton is used.
- **`_multipage`** – required when `mode = "multipage"`. It receives a `preprocess_file` function and must return a dictionary mapping output paths (relative to the output directory) to either HTML strings or bytes. See [Multi‑page Sites](#multi-page-sites) for details.

### Custom Macros in Python

Place a `.py` file in the `macros/` directory. Each file must define a function named `macro` that accepts a single string (the block content) and returns a string (the HTML).

**Globals available inside every macro module**:

| Name              | Type                 | Description |
|-------------------|----------------------|-------------|
| `MACROS`          | `dict[str, Callable]` | All regular macros (by name). Use this to call other macros: `MACROS['other'](content)`. |
| `DEPS`            | `dict[str, Path]`    | Maps full dependency name (e.g., `"Urriverse/hsb-theme"`) to its local `Path` (the unpacked base directory). Useful for reading files from a specific dependency. |
| `MACRO_REGISTRY`  | `dict[tuple[str, str], Callable]` | Maps `(dep_name, macro_name)` → callable. This is the source of truth for all loaded macros. You can inspect or use it directly, but `include_macro` is the recommended way. |
| `include_macro`   | `Callable[[str, str], Optional[Callable]]` | Built‑in function to retrieve a macro from a specific dependency (or `"__local__"` for project macros). |

**Example:** `macros/greet.py`
```python
def macro(content: str) -> str:
    name = content.strip() or "World"
    # Call another macro if available
    if 'uppercase' in MACROS:
        name = MACROS['uppercase'](name)
    return f"<h1>Hello, {name}!</h1>"
```

You can also read a file from a dependency:

```python
def macro(content: str) -> str:
    theme_path = DEPS.get('Urriverse/hsb-theme')
    if theme_path:
        readme = (theme_path / "README.md").read_text()
        return f"<pre>{readme}</pre>"
    return "<p>Theme not found</p>"
```

**Error handling:** If a macro raises an exception, the build will stop and display a diagnostic message showing the source file and line number where the macro was invoked.

---

## Dependencies

Dependencies are GitHub repositories that provide assets, macros, or even base content. They are fetched on demand and cached in `.hsb_cache/bases/`.

### Specifying Dependencies

In `OhDog.toml` under `[general].requires`, list repository names in the form `"user/repo"`. You can also use a shorthand: if you write just the repo name (without a slash), it is prefixed with `Urriverse/hsb-` – this is convenient for the official Oh, Dog! ecosystem.

Example:
```toml
[general]
requires = ["urriverse/hsb-theme", "charts"]
# charts expands to "Urriverse/hsb-charts"
```

### The `vendor` Command

Running `ohdog vendor` will:

1. Resolve the full dependency tree (including transitive dependencies) by reading each dependency’s `OhDog.toml` (if present).
2. Fetch each repository (using `main` or `master` branch).
3. Copy all files from `<dep>/assets/` into your project’s `assets/` folder.
4. Copy all files from `<dep>/macros/` into your project’s `macros/` folder.
5. If the dependency has a `src/index.md` and your project does not have one (or you used `--force`), it copies that index file.
6. After successful vendoring, the `requires` list is cleared in your local `OhDog.toml`.

Vendoring is idempotent: files that already exist are not overwritten unless `--force` is used.

### Dependency Resolution & Priority

Dependencies are ordered as they appear in `requires` (and then recursively). When copying assets/macros, **later** dependencies have higher priority. That is, if two dependencies provide the same file (e.g., `style.css`), the one that appears later in the tree will overwrite earlier ones (if `--force` is used, the highest priority always wins). This allows you to layer themes and customisations.

However, you can still access macros from **lower‑priority** dependencies using the `include_macro` function, which overrides the priority order.

---

## Multi‑page Sites

To generate more than one page, set `mode = "multipage"` in `OhDog.toml`. Then, you **must** provide a `_multipage` macro (i.e., a file `macros/_multipage.py` that defines `macro`). This macro receives a single argument: a function `preprocess_file`.

**`preprocess_file`** signature:
```python
def preprocess_file(file_path: Path) -> str:
    ...
```

It takes a path to a Markdown file and returns the rendered HTML body (with macros expanded). You can call this function on any Markdown files in your project or dependencies.

Your `_multipage` macro must return a dictionary where:

- Keys are `Path` objects (relative to the output directory, e.g., `Path("index.html")`, `Path("guide/install.html")`).
- Values are either:
  - `str` – interpreted as HTML body; it will be wrapped with the page skeleton (`_head` and `_page` special macros) automatically.
  - `bytes` – written directly (useful for binary assets like images). In this case, no wrapping occurs.

**Example `macros/_multipage.py`:**
```python
from pathlib import Path

def macro(preprocess_file):
    output = {}
    
    # Process main index
    index_content = preprocess_file(Path("src/index.md"))
    output[Path("index.html")] = index_content
    
    # Process a guide page
    guide_content = preprocess_file(Path("src/guide.md"))
    output[Path("guide/index.html")] = guide_content
    
    # Copy an image as bytes
    with open(Path("assets/logo.png"), "rb") as f:
        output[Path("images/logo.png")] = f.read()
    
    return output
```

The build will create all the necessary directories and write the files.

> **Important:** The `_multipage` macro must at least produce an `index.html`; otherwise the build will fail.

---

## Assets & Styling

Oh, Dog! automatically includes:

- `assets/style.css` – concatenated with any dependency CSS (in order of priority).
- `assets/script.js` – concatenated similarly.

These are inserted into the HTML `<head>` (or via the `_head` macro). You can override the default page structure by providing `_head` and `_page` special macros.

If you want to include additional assets (e.g., images, fonts), you can copy them manually or use the `_multipage` macro to output binary files.

---

## Error Handling & Logging

Oh, Dog! provides coloured output to `stderr`:

- **`error`** – stops the build and shows the error location (file:line) if available, plus an optional hint.
- **`warning`** – shows a warning but continues.
- **`info`**, **`compiling`**, **`finished`** – progress messages.

When a macro fails, the build attempts to pinpoint the exact Markdown file and line number where the macro was invoked, making debugging easier.

---

## Examples

### Minimal Project

```bash
mkdir my-docs
cd my-docs
ohdog init .
echo "# My Page\n\nHello, world!" > src/index.md
ohdog build
```

Open `out/my-docs/index.html`.

### Using a Dependency

Add to `OhDog.toml`:
```toml
[general]
requires = ["urriverse/hsb-theme"]
```

Run:
```bash
ohdog build
```

Now your page will be styled with the theme’s CSS and macros.

### Multi‑page with Custom Layout

Create `macros/_multipage.py`:

```python
from pathlib import Path

def macro(preprocess):
    pages = {}
    for md_file in Path("src").glob("*.md"):
        name = md_file.stem
        html = preprocess(md_file)
        pages[Path(f"{name}.html")] = html
    # Ensure index exists
    if Path("index.html") not in pages:
        pages[Path("index.html")] = "<h1>Welcome</h1>"
    return pages
```

Set `mode = "multipage"` in `OhDog.toml` and run `ohdog build`. Each `.md` file becomes a separate HTML page.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `OhDog.toml` not found | Run `ohdog init` first. |
| Dependencies not fetched | Check your internet connection; GitHub may be unreachable. |
| Macro `_multipage` not found | Ensure you have `mode = "multipage"` and a `macros/_multipage.py` file with a `macro` function. |
| Macro error location shows `importlib` | The error occurred inside the macro; check the macro’s implementation. |
| Vendor doesn’t copy my dependency | Ensure the dependency has an `OhDog.toml` and that the repository exists on GitHub. |

---

## Contributing

Oh, Dog! is open source. Feel free to report issues or submit pull requests on the [GitHub repository](https://github.com/Urriverse/ohdog).

---

**Happy dogumenting!** 🐶
