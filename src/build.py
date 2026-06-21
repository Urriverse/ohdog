import importlib as ilib
from pathlib import Path
import markdown
import dep
from log import logger as log
import re

import toml


def load_macros_from_dir(macros_dir, macros_dict, special_macros_dict):
    if not macros_dir or not macros_dir.exists(): return
    
    for py_file in macros_dir.glob("*.py"):
        macro_name = py_file.stem
        
        spec = ilib.util.spec_from_file_location(macro_name, py_file)
        module = ilib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, "macro"):
            if macro_name[0] == '_':
                special_macros_dict[macro_name] = module.macro
            else:
                macros_dict[macro_name] = module.macro

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
    if 'head' in special_macros:
        try:
            head_content = special_macros['_head'](title, css_content, js_content)
        except Exception as e:
            log.log_macro_error(e, "[head]")
    else:
        head_content = f"""<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{css_content}
</style>"""
    
    if 'page' in special_macros:
        try:
            final_html = special_macros['_page'](title, head_content, body_content, js_content)
        except Exception as e:
            log.log_macro_error(e, "[page]")
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
    
    requires_list = config.get("base", {}).get("requires", [])
    if requires_list:
        dependency_tree = dep.build_dependency_tree(project_path, requires_list, args.no_cache)
        if dependency_tree:
            tree_names = [p.name for p in dependency_tree]
            log.note(f"dependency tree: {' -> '.join(tree_names)}")
    else:
        dependency_tree = []
    
    css_content = ""
    js_content = ""
    macros = {}
    special_macros = {}
    
    for base_dir in dependency_tree:
        dep_assets = base_dir / "assets"
        if (dep_assets / "style.css").exists():
            css_content += (dep_assets / "style.css").read_text(encoding="utf-8") + "\n"
        if (dep_assets / "script.js").exists():
            js_content += (dep_assets / "script.js").read_text(encoding="utf-8") + "\n"
        load_macros_from_dir(base_dir / "macros", macros, special_macros)
    
    local_assets = project_path / "assets"
    if (local_assets / "style.css").exists():
        css_content += (local_assets / "style.css").read_text(encoding="utf-8")
    if (local_assets / "script.js").exists():
        js_content += (local_assets / "script.js").read_text(encoding="utf-8")
    load_macros_from_dir(project_path / "macros", macros, special_macros)
    
    log.compiling(doc_name)
    
    target_dir = project_path / "out" / doc_name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    if general_config.get("mode"):
        multipage_macro = macros.get("_multipage")

        if multipage_macro is None:
            log.error(
                "multipage mode is not supported. write "
                "[multipage] macro or get it using dependencies."
            )

        try:
            output_files = multipage_macro(lambda f, m: preprocess_file(f, m))
        except Exception as e:
            log.log_macro_error(e, "_multipage", project_path / "macros" / "_multipage.py")
        
        if not isinstance(output_files, dict):
            log.error("[multipage] macro must return `dict[Path, str|bytes]`")
        
        has_index = any(out_path.name == "index.html" for out_path in output_files.keys())
        
        if not has_index:
            log.error("[multipage] macro must generate at least 'index.html'")
        
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
        
        html_body = preprocess_file(src_file, macros)
        final_html = assemble_html(title, html_body, css_content, js_content, special_macros)
        
        out_file = target_dir / "index.html"
        out_file.write_text(final_html, encoding="utf-8")
        log.finished(f"{doc_name} -> out/{doc_name}/index.html")
