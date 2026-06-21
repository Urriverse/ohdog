import shutil
import urllib.request
import urllib.error
import zipfile
import toml
from collections import deque
from log import logger

def resolve_require_name(name):
    if "/" not in name:
        return f"Urriverse/ohdog-{name}"
    return name

def fetch_dep(name, project_path, no_cache=False):
    full_name = resolve_require_name(name)
    user, repo = full_name.split("/", 1)
    cache_dir = project_path / ".hsb_cache" / "bases" / f"{user}_{repo}"
    
    if no_cache and cache_dir.exists():
        shutil.rmtree(cache_dir)
    
    if cache_dir.exists():
        for d in cache_dir.iterdir():
            if d.is_dir():
                return d
                
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/main.zip"
    zip_path = cache_dir / "repo.zip"
    
    logger.info(f"{full_name}")
    try:
        urllib.request.urlretrieve(zip_url, zip_path)
    except urllib.error.HTTPError:
        zip_url = zip_url.replace("/main.zip", "/master.zip")
        try:
            urllib.request.urlretrieve(zip_url, zip_path)
        except Exception as e2:
            logger.error(f"failed to fetch '{full_name}': {e2}")
    except Exception as e:
        logger.error(f"network error while fetching '{full_name}': {e}")
        
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(cache_dir)
    zip_path.unlink()
    
    for d in cache_dir.iterdir():
        if d.is_dir():
            return d
    return None

def build_dependency_tree(project_path, requires_list, no_cache=False):
    tree = []   # list of (name, base_dir)
    visited = set()
    queue = deque(requires_list)
    
    while queue:
        name = queue.popleft()
        if name in visited:
            continue
        visited.add(name)
        
        base_dir = fetch_dep(name, project_path, no_cache)
        if not base_dir:
            logger.warning(f"skipping '{name}' (fetch failed)")
            continue
            
        tree.append((name, base_dir))
        
        config_file = base_dir / "OhDog.toml"
        if config_file.exists():
            try:
                with open(config_file, "rb") as f:
                    config = toml.load(f)
                requires = config.get("base", {}).get("requires", [])
                queue.extend(requires)
            except Exception as e:
                logger.warning(f"failed to parse OhDog.toml from '{name}': {e}")
    
    return tree
