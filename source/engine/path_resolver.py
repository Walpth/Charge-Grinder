import os
from typing import Dict

class PathResolver:
    """Utility to map asset names to their physical file paths."""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self._paths: Dict[str, str] = self._collect_paths()

    def _collect_paths(self) -> Dict[str, str]:
        paths = {}
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                if not file.lower().endswith(".png"):
                    continue

                name = os.path.splitext(file)[0]
                if name in paths:
                    raise ValueError(f"Duplicate image name detected: {name} in {root}")
                paths[name] = os.path.join(root, file).replace("\\", "/")
        return paths

    def get(self, target: str) -> str:
        """Returns the physical path. If passed an existing path, returns it directly."""
        if os.path.isfile(target):
            return target
            
        if target not in self._paths:
            raise FileNotFoundError(f"Asset '{target}' not found in {self.base_dir}")
            
        return self._paths[target]