import importlib as ilib
from pathlib import Path
import markdown
import dep
from log import logger as log
import re
import toml
from typing import Callable, Optional


# ----- Registry for all macros from all sources -----
# key: (dep_name, macro_name) -> callable
# dep_name: full repository name (e.g., "Urriverse/hsb-theme") or "__local__" for project macros
MACRO_REGISTRY = {}

# Built‑in macro: retrieve a macro from a specific dependency
def include_macro(dep_name: str, macro_name: str) -> Optional[Callable[[str], str]]:
    """
    Return a macro callable from the given dependency (or local if dep_name == "__local__").
    Returns None if not found.
    """
    return MACRO_REGISTRY.get((dep_name, macro_name))


def load_macros_from_dir(macros_dir, macros_dict, special_macros_dict, dep_name=None, extra_globals=None):
    """
    Load macros from a directory, injecting extra globals.
    dep_name: full repository name or "__local__" for local project.
    """
    if not macros_dir or not macros_dir.exists():
        return

    extra_globals = extra_globals or {}
    dep_name = dep_name or "__local__"

    for py_file in macros_dir.glob("*.py"):
        macro_name = py_file.stem

        spec = ilib.util.spec_from_file_location(macro_name, py_file)
        module = ilib.util.module_from_spec(spec)

        # Inject extra globals
        for k, v in extra_globals.items():
            setattr(module, k, v)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            log.error(f"failed to load macro '{macro_name}': {e}", file=py_file)

        if hasattr(module, "macro"):
            callable_func = module.macro
            # Register in the global registry
            MACRO_REGISTRY[(dep_name, macro_name)] = callable_func

            # Also put into the normal dicts (highest priority wins)
            if macro_name.startswith('_'):
                special_macros_dict[macro_name] = callable_func
            else:
                macros_dict[macro_name] = callable_func


def parse_and_evaluate_blocks(text, macros, source_file: Path):
    placeholders = {}
    placeholder_counter = 0

    while True:
        lines = text.split('\n')
        stack = []
        found_block = False

        for i, line in enumerate(lines):
            m_start = re.match(r'^#([a-zA-Z0-9_]+)\s*$', line)
            m_end = re.match(r'^#/([a-zA-Z0-9_]+)\s*$', line)

            if m_start:
                stack.append((m_start.group(1), i))
            elif m_end:
                name = m_end.group(1)
                if stack and stack[-1][0] == name:
                    _, start_idx = stack.pop()
                    content = "\n".join(lines[start_idx+1 : i])

                    if name in macros:
                        try:
                            html_out = macros[name](content)
                        except Exception as e:
                            log.log_macro_error(e, name, source_file)
                    else:
                        log.warning(
                            f"unknown macro '{name}'",
                            file=source_file,
                            line=start_idx + 1
                        )
                        html_out = f"<!-- Unknown macro: {name} -->\n<pre>{content}</pre>"

                    ph_id = f"<!-- BLOCK_PH_{placeholder_counter} -->"
                    placeholder_counter += 1
                    placeholders[ph_id] = html_out

                    lines[start_idx : i+1] = [ph_id]
                    text = "\n".join(lines)
                    found_block = True
                    break

        if not found_block:
            break

    return text, placeholders


def preprocess_file(file_path: Path, macros: dict) -> str:
    if not file_path.exists():
        log.error(f"source file not found: {file_path}")

    md_text = file_path.read_text(encoding="utf-8")
    processed_text, placeholders = parse_and_evaluate_blocks(md_text, macros, file_path)
    html_body = markdown.markdown(processed_text, extensions=['extra', 'sane_lists'])

    changed = True
    while changed:
        changed = False
        for ph_id, html_out in placeholders.items():
            if ph_id in html_body:
                html_body = re.sub(rf'<p>\s*{re.escape(ph_id)}\s*</p>', html_out, html_body)
                if ph_id in html_body:
                    html_body = html_body.replace(ph_id, html_out)
                changed = True

    return html_body


def assemble_html(title: str, body_content: str, css_content: str, js_content: str, special_macros: dict) -> str:
    if '_head' in special_macros:
        try:
            head_content = special_macros['_head'](title, css_content, js_content)
        except Exception as e:
            log.log_macro_error(e, "_head")
    else:
        head_content = f"""<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{css_content}
</style>"""

    if '_page' in special_macros:
        try:
            final_html = special_macros['_page'](title, head_content, body_content, js_content)
        except Exception as e:
            log.log_macro_error(e, "_page")
    else:
        final_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
{head_content}
<script>
{js_content}
</script>
</head>
<body>
<div class="kdiag">
{body_content}
</div>
</body>
</html>"""

    return final_html


def main(args):
    project_path = Path(args.project_dir).resolve()
    config_file = project_path / "OhDog.toml"

    if not config_file.exists():
        log.error(f"OhDog.toml not found", file=project_path, hint="run 'init' first to create a project")

    with open(config_file, "rb") as f:
        config = toml.load(f)

    general_config = config.get("general", {})
    title = general_config.get("title", "Untitled Document")
    doc_name = general_config.get("name", "untitled")

    requires_list = general_config.get("requires", [])
    dependency_tree = []
    if requires_list:
        dependency_tree = dep.build_dependency_tree(project_path, requires_list, args.no_cache)
        if dependency_tree:
            tree_names = [name for name, _ in dependency_tree]
            log.note(f"dependency tree: {' -> '.join(tree_names)}")

    # Build DEPS dict and base_dirs list
    DEPS = {name: base_dir for name, base_dir in dependency_tree}
    base_dirs = [base_dir for _, base_dir in dependency_tree]

    css_content = ""
    js_content = ""
    MACROS = {}           # shared, mutable dict – all macros will see it
    special_macros = {}

    # Prepare globals to inject into every macro module
    extra_globals = {
        'MACROS': MACROS,
        'DEPS': DEPS,
        'MACRO_REGISTRY': MACRO_REGISTRY,   # so macros can inspect registry if they want
    }

    # Load macros from dependencies
    for dep_name, base_dir in dependency_tree:
        load_macros_from_dir(
            base_dir / "macros",
            MACROS,
            special_macros,
            dep_name=dep_name,
            extra_globals=extra_globals
        )
        # Also collect assets
        dep_assets = base_dir / "assets"
        if (dep_assets / "style.css").exists():
            css_content += (dep_assets / "style.css").read_text(encoding="utf-8") + "\n"
        if (dep_assets / "script.js").exists():
            js_content += (dep_assets / "script.js").read_text(encoding="utf-8") + "\n"

    # Load local macros (dep_name = "__local__")
    load_macros_from_dir(
        project_path / "macros",
        MACROS,
        special_macros,
        dep_name="__local__",
        extra_globals=extra_globals
    )

    # ----- Inject built‑in include_macro -----
    # It's a normal function; we add it to MACROS so it can be called from other macros.
    # Also register it under "__builtin__" so it can be retrieved if needed.
    MACROS['include_macro'] = include_macro
    MACRO_REGISTRY[('__builtin__', 'include_macro')] = include_macro

    # Load local assets
    local_assets = project_path / "assets"
    if (local_assets / "style.css").exists():
        css_content += (local_assets / "style.css").read_text(encoding="utf-8")
    if (local_assets / "script.js").exists():
        js_content += (local_assets / "script.js").read_text(encoding="utf-8")

    log.compiling(doc_name)

    target_dir = project_path / "out" / doc_name
    target_dir.mkdir(parents=True, exist_ok=True)

    mode = general_config.get("mode", "standalone")

    if mode == "multipage":
        multipage_macro = special_macros.get("_multipage")

        if multipage_macro is None:
            log.error(
                "multipage mode requires a '_multipage' special macro. "
                "Create macros/_multipage.py with a 'macro' function."
            )

        # The lambda now only takes a file path – macros dict is already captured
        try:
            output_files = multipage_macro(lambda f: preprocess_file(f, MACROS))
        except Exception as e:
            log.log_macro_error(e, "_multipage", project_path / "macros" / "_multipage.py")

        if not isinstance(output_files, dict):
            log.error("_multipage macro must return `dict[Path, str|bytes]`")

        has_index = any(out_path.name == "index.html" for out_path in output_files.keys())
        if not has_index:
            log.error("_multipage macro must generate at least 'index.html'")

        for rel_path, content in output_files.items():
            out_file = target_dir / rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(content, bytes):
                out_file.write_bytes(content)
            else:
                final_html = assemble_html(title, content, css_content, js_content, special_macros)
                out_file.write_text(final_html, encoding="utf-8")

        log.finished(f"{doc_name} -> out/{doc_name}/")

    else:
        src_file = project_path / "src" / "index.md"
        if not src_file.exists():
            src_file = project_path / "index.md"
            if not src_file.exists():
                log.error("both index.md & src/index.md not found", file=project_path)

        html_body = preprocess_file(src_file, MACROS)
        final_html = assemble_html(title, html_body, css_content, js_content, special_macros)

        out_file = target_dir / "index.html"
        out_file.write_text(final_html, encoding="utf-8")
        log.finished(f"{doc_name} -> out/{doc_name}/index.html")
