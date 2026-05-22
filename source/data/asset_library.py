import json

import cv2

from source.engine.input_controller import InputController 
from source.engine.path_resolver import PathResolver
from source.engine.search_region import SearchRegion
from source.engine.match_strategy import MatchStrategy, TemplateGrayStrategy, TemplateRGBStrategy, TemplateEdgesStrategy, SIFTMatchStrategy
from .base_path import JSON_PATH


CONFIG = json.load(open(JSON_PATH))


class AssetLibrary:
    _METHOD_MAP = {
        "sqdiff":        cv2.TM_SQDIFF,
        "sqdiff_normed": cv2.TM_SQDIFF_NORMED,
        "ccorr":         cv2.TM_CCORR,
        "ccorr_normed":  cv2.TM_CCORR_NORMED,
        "ccoeff":        cv2.TM_CCOEFF,
        "ccoeff_normed": cv2.TM_CCOEFF_NORMED,
    }

    _STRATEGY_MAP = {
        "gray":  TemplateGrayStrategy,
        "rgb":   TemplateRGBStrategy,
        "edges": TemplateEdgesStrategy,
        "sift":  SIFTMatchStrategy
    }

    def __init__(self, controller: InputController, path_resolver: PathResolver, config: dict = CONFIG):
        self.path_resolver = path_resolver
        self.controller = controller
        self.config = config
        self.default_strategy = TemplateGrayStrategy
        self.default_method = cv2.TM_CCOEFF_NORMED
    
    def _resolve_method(self, method_spec):
        if method_spec is None:
            return self.default_method

        if isinstance(method_spec, int):
            return method_spec

        if isinstance(method_spec, str):
            key = method_spec.lower()
            if key in self._METHOD_MAP:
                return self._METHOD_MAP[key]

        raise ValueError(f"Unknown strategy method: {method_spec!r}")
    
    def _resolve_strategy(self, meta: dict) -> MatchStrategy:
        strategy_name = meta.get("strategy")
        method = self._resolve_method(meta.get("method"))

        if strategy_name is None:
            return self.default_strategy(method=method)

        if hasattr(strategy_name, "find_matches") and callable(getattr(strategy_name, "find_matches")):
            return strategy_name
        

        if isinstance(strategy_name, str):
            strategy_name = strategy_name.lower()
            if strategy_name in self._STRATEGY_MAP:
                strategy = self._STRATEGY_MAP[strategy_name]

                if strategy_name != "sift":
                    return strategy(method=method)
                return strategy()
            
            raise ValueError(f"Unknown strategy string: {strategy_name}")

        raise ValueError(f"Unsupported strategy spec: {strategy_name!r}")

    def get(self, menu: str, name: str) -> SearchRegion:
        """Stamps out a pre-configured SearchRegion."""
        meta = self.config.get(menu, {}).get(name, {})
        region = meta.get("region", (0, 0, 1920, 1080))
        target_name = meta.get("asset", name)

        try:
            self.path_resolver.get(target_name)
            default_target = target_name
        except FileNotFoundError:
            default_target = None
        
        return SearchRegion(
            controller=self.controller, 
            region=region, 
            name=name, 
            default_target=default_target,
            default_strategy=self._resolve_strategy(meta),
            default_conf=meta.get("conf", 0.9),
            path_resolver=self.path_resolver
        )