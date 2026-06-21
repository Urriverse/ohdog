import shutil
from log import logger as log
from pathlib import Path
import toml
import dep
import re


def copy_tree_with_priority(src, dst, priority_map, current_priority, overwrite=False):
    if not src or not src.exists(): return 0
    copied = 0
    for item in src.rglob('*'):
        if item.is_file():
            rel = item.relative_to(src)
            target = dst / rel
            
            should_copy = False
            if overwrite:
                should_copy = True
            elif not target.exists():
                should_copy = True
            elif rel not in priority_map:
                should_copy = True
            elif current_priority < priority_map[rel]:
                should_copy = True
            
            if should_copy:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                priority_map[rel] = current_priority
                copied += 1
    return copied

def main(args):
    project_path = Path(args.project_dir).resolve()
    config_file = project_path / "OhDog.toml"
    
    if not config_file.exists():
        log.error("OhDog.toml not found", file=project_path, hint="run 'init' first")
        
    with open(config_file, "rb") as f:
        config = toml.load(f)
        
    requires_list = config.get("general", {}).get("requires", [])
    
    if not requires_list:
        log.finished(f"vendored 0 asset(s) and 0 macro(s)")
        log.note("project has no dependencies, nothing to vendor")
        return
    
    dependency_tree = dep.build_dependency_tree(project_path, requires_list, args.no_cache)
    
    if not dependency_tree:
        log.error("failed to build dependency tree")
    
    tree_names = [p.name for p in dependency_tree]
    log.compiling(f"vendoring: {' -> '.join(tree_names)}")
    
    asset_priority_map = {}
    macro_priority_map = {}
    
    total_assets = 0
    total_macros = 0
    
    for priority, base_dir in enumerate(dependency_tree):
        assets_copied = copy_tree_with_priority(
            base_dir / "assets",
            project_path / "assets",
            asset_priority_map,
            priority,
            overwrite=args.force
        )
        macros_copied = copy_tree_with_priority(
            base_dir / "macros",
            project_path / "macros",
            macro_priority_map,
            priority,
            overwrite=args.force
        )
        total_assets += assets_copied
        total_macros += macros_copied
    
    index_file = project_path / "src" / "index.md"
    if dependency_tree:
        first_base = dependency_tree[0]
        base_index = first_base / "src" / "index.md"
        if base_index.exists() and (not index_file.exists() or args.force):
            (project_path / "src").mkdir(parents=True, exist_ok=True)
            shutil.copy2(base_index, index_file)
    
    log.finished(f"vendored {total_assets} asset(s) and {total_macros} macro(s)")
    
    config_content = config_file.read_text(encoding="utf-8")
    new_content = re.sub(
        r'(requires\s*=\s*\[)([^\]]*)(\])',
        r'\1\3',
        config_content
    )
    config_file.write_text(new_content, encoding="utf-8")
