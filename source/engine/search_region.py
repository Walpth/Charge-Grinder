import copy
import os
import time
from typing import Callable, Optional, Dict, Any, List, Tuple, Self

import cv2
import numpy as np

from .cache import generate_template_cache_key
from .input_controller import InputController
from .path_resolver import PathResolver
from .target import MatchResult, Target
from .match_strategy import MatchStrategy


class ImageNotFoundException(Exception): pass

def safe_imread(path, flags=cv2.IMREAD_COLOR):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None

    if not data:
        return None

    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, flags)
    return img


class SearchRegion:
    _template_cache: dict[tuple, np.ndarray] = {}

    def __init__(self, controller: InputController, region: tuple, name: str = None, 
                 default_target: str | np.ndarray = None, default_strategy: MatchStrategy = None, 
                 default_conf: float = 0.9, path_resolver: PathResolver = None, cache: int = 100):
        """Represents a specific region of the screen to search for targets.

        Args:
            controller: The InputController to use for screenshots and interactions.
            region: A tuple (x, y, w, h) defining the search area relative to the full screen.
            name: An optional name for logging and debugging purposes.
            default_target: A default target identifier (e.g., image filename or key) to use if none is provided in locate calls.
            default_strategy: A default matching strategy to use if none is provided in locate calls.
            default_conf: A default confidence threshold to use if none is provided in locate calls.
            path_resolver: An optional PathResolver to convert target keys into actual file paths.
            cache: The maximum number of templates to keep in memory per region instance.
        """
        self.controller = controller
        self.region = region
        self.name = name or "Region"
        
        self.default_target = default_target
        self.default_strategy = default_strategy
        self.default_conf = default_conf
        self.path_resolver = path_resolver

        self._override_raw = None
        self._transform_params: Optional[Dict[str, Any]] = None

    def screenshot(self) -> np.ndarray:
        return self.controller.screenshot(region=self.region)

    def _resolve_target(self, target: str = None, conf: float = None, strategy=None) -> tuple[str, Any, float]:
        """Resolves the physical path using the injected PathResolver."""
        t = target or self.default_target
        if not t:
            raise ValueError(f"SearchRegion '{self.name}' has no target to locate.")

        if self.path_resolver:
            path = self.path_resolver.get(t)
        else:
            path = t if os.path.isfile(t) else None
            if not path:
                raise FileNotFoundError(f"No PathResolver provided, and '{t}' is not a valid file path.")

        final_strategy = strategy or self.default_strategy
        final_conf = conf or self.default_conf

        return path, final_strategy, final_conf

    def get_template(self, path: str = None) -> np.ndarray:
        raw_identity = f"inmem:{id(self._override_raw)}" if self._override_raw is not None else path

        tp = self._transform_params or {}
        custom = tp.get("func")
        custom_kwargs = tp.get("fkwargs")
        custom_key = tp.get("fkey")

        comp = float(self.controller.comp)
        key = generate_template_cache_key(raw_identity, custom, custom_kwargs, custom_key, comp)
        if key in self._template_cache:
            return self._template_cache[key]
        
        if self._override_raw is not None:
            raw = self._override_raw
        else:
            raw = safe_imread(path, cv2.IMREAD_UNCHANGED)
            if raw is None:
                raise FileNotFoundError(f"Missing asset at {path}")
        
        comp = float(self.controller.comp)
        if comp < 1.0:
            new_w = max(1, int(raw.shape[1] * comp))
            new_h = max(1, int(raw.shape[0] * comp))
            resized = cv2.resize(raw, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            resized = raw

        if custom:
            modified = custom(resized, **(custom_kwargs or {}))
            if not isinstance(modified, np.ndarray):
                raise TypeError("custom transform must return np.ndarray!")
        else:
            modified = resized

        self._template_cache[key] = modified
        return modified
    
    def template(self, image) -> Self:
        clone = copy.copy(self)
        clone._override_raw = image
        clone._template_cache = self._template_cache
        return clone

    def transform(self, func: Optional[Callable[[np.ndarray], np.ndarray]] = None,
                        fkwargs: Optional[Dict[str, Any]] = None,
                        fkey: Optional[str] = None) -> Self:
        clone = copy.copy(self)
        clone._transform_params = {
            "func": func,
            "fkwargs": dict(fkwargs) if fkwargs else None,
            "fkey": str(fkey) if fkey is not None else None
        }
        clone._template_cache = self._template_cache
        return clone

    def _normalize_coords(self, x, y, w, h) -> Tuple[int,int,int,int]:
        comp = float(self.controller.comp)
        if comp < 1.0:  # upscale internal coords to full hd
            x = int(round(x / comp))
            y = int(round(y / comp))
            w = max(1, int(round(w / comp)))
            h = max(1, int(round(h / comp)))
        return x, y, w, h
    
    def _build_located(self, x, y, w, h, score) -> Target:
        x, y, w, h = self._normalize_coords(x, y, w, h)

        match_data = MatchResult(
            x=x + self.region[0],
            y=y + self.region[1],
            w=w,
            h=h,
            score=score
        )
        return Target(self, match_data, self.controller)

    def locate(self, target: str = None, conf: float = None, wait: float = 0.0) -> Target:
        if wait < 0:
            raise ValueError("wait must be >= 0")
        
        path, strategy, final_conf = self._resolve_target(target, conf)
        tpl = self.get_template(path)
        deadline = time.monotonic() + wait

        while True:
            screen_crop = self.screenshot()
            matches = strategy.find_matches(screen_crop, tpl, final_conf)

            if matches:
                x, y, w, h, score = matches[0]
                return self._build_located(x, y, w, h, score)

            if time.monotonic() >= deadline:
                return Target(self, None, self.controller)

            time.sleep(0.1)
    
    def locate_all_in(self, screen_image: np.ndarray, target: str = None, conf: float = None) -> List[Target]:
        path, strategy, final_conf = self._resolve_target(target, conf)
        tpl = self.get_template(path)

        matches = strategy.find_matches(screen_image, tpl, final_conf)
        if not matches:
            return []

        results = []
        for x, y, w, h, score in matches:
            results.append(self._build_located(x, y, w, h, score))
        return results
    
    def locate_all(self, target: str = None, conf: float = None) -> List[Target]:
        screen_crop = self.screenshot()
        return self.locate_all_in(screen_crop, target=target, conf=conf)

    def locate_in(self, screen_image: np.ndarray, target: str = None, conf: float = None) -> Target:
        path, strategy, final_conf = self._resolve_target(target, conf)
        tpl = self.get_template(path)

        matches = strategy.find_matches(screen_image, tpl, final_conf)
        if not matches:
            return Target(self, None, self.controller)
        
        x, y, w, h, score = matches[0]
        return self._build_located(x, y, w, h, score)


    def try_locate(self, target: str = None, conf: float = None, wait: float = 0.0) -> Target:
        result = self.locate(target=target, conf=conf, wait=wait)
        if not result.exists:
            target_name = target or self.name
            raise ImageNotFoundException(f"SearchTarget '{target_name}' not found in region '{self.name}'.")
        return result
    
    def try_locate_in(self, screen_image: np.ndarray, target: str = None, conf: float = None) -> Target:
        result = self.locate_in(screen_image=screen_image, target=target, conf=conf)
        if not result.exists:
            target_name = target or self.name
            raise ImageNotFoundException(f"SearchTarget '{target_name}' not found in provided image.")
        return result
    
    def check(self, target: str = None, conf: float = None, wait: float = 0.0) -> bool:
        result = self.locate(target=target, conf=conf, wait=wait)
        return result.exists
    
    def check_in(self, screen_image: np.ndarray, target: str = None, conf: float = None) -> bool:
        result = self.locate_in(screen_image=screen_image, target=target, conf=conf)
        return result.exists