from pathlib import Path
from log import logger as log
import defaults


def main(args):
    target_path = Path(args.path).resolve()
    requires_list = args.base_from if args.base_from else []
    
    log.compiling(f"initializing {target_path.name}")
    
    if target_path.exists() and any(target_path.iterdir()):
        if not args.force:
            log.error(
                f"directory '{target_path}' is not empty",
                hint="use --force to initialize anyway"
            )
    
    target_path.mkdir(parents=True, exist_ok=True)
    
    (target_path / "assets").mkdir(exist_ok=True)
    (target_path / "macros").mkdir(exist_ok=True)
    (target_path / "src").mkdir(exist_ok=True)
    
    title = target_path.name.replace('-', ' ').replace('_', ' ').title()
    if title == '.':
        title = "My Documentation"
    
    name = target_path.name.lower().replace(' ', '-')
    if name == '.':
        name = "default"
    
    if requires_list:
        requires_str = "[" + ", ".join(f'"{r}"' for r in requires_list) + "]"
    else:
        requires_str = "[]"
    
    scheme_file = target_path / "OhDog.toml"
    if not scheme_file.exists() or args.force:
        scheme_file.write_text(
            defaults.DEFAULT_CONFIG.format(title=title, name=name, requires=requires_str),
            encoding="utf-8"
        )
    
    index_file = target_path / "src" / "index.md"
    if not index_file.exists() or args.force:
        index_file.write_text(defaults.DEFAULT_INDEX_MD.format(title=title), encoding="utf-8")
    
    gitignore = target_path / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(defaults.GITIGNORE_CONTENT, encoding="utf-8")
    
    log.finished(f"{name} initialized")
