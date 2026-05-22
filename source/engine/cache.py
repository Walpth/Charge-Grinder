import inspect
import hashlib
import json
from typing import Callable, Optional, Dict, Any, Tuple


def _stable_func_id(func: Callable) -> Tuple[str, str]:
    if func is None:
        return ("none", "none")
    try:
        src = inspect.getsource(func)
        digest = hashlib.sha256(src.encode("utf-8")).hexdigest()
        return ("src", digest)
    except (OSError, TypeError, IOError):
        try:
            name = f"{func.__module__}.{func.__qualname__}"
            return ("name", name)
        except Exception:
            return ("id", str(id(func)))

def _stable_kwargs_hash(kwargs: Optional[Dict[str, Any]]) -> str:
    if not kwargs:
        return ""
    try:
        s = json.dumps(kwargs, sort_keys=True, default=lambda o: repr(o), separators=(',',':'))
    except Exception:
        items = tuple(sorted((k, repr(v)) for k, v in kwargs.items()))
        s = repr(items)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def generate_template_cache_key(
        raw_identity: str, 
        custom: Optional[Callable], 
        custom_kwargs: Optional[Dict[str, Any]], 
        custom_key_override: Optional[str],
        comp: float
    ) -> Tuple:
    if custom_key_override:
        custom_id = ("override", str(custom_key_override))
    else:
        custom_id = _stable_func_id(custom)
        
    kwargs_hash = _stable_kwargs_hash(custom_kwargs)
    
    return (raw_identity, custom_id, kwargs_hash, comp)