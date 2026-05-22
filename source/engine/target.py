from dataclasses import dataclass
from typing import Tuple, Optional, Self

import time

from .input_controller import InputController


@dataclass(frozen=True)
class MatchResult:
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    score: float = 0.0

    @property
    def box(self) -> tuple[int, int, int, int]:
        """(x, y, w, h)"""
        return (self.x, self.y, self.w, self.h)
    
    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)
    
    def __iter__(self):
        yield self.x
        yield self.y
        yield self.w
        yield self.h
        yield self.score


class Target:
    def __init__(self, ui_element: Optional['SearchRegion'], 
                 match: Optional[MatchResult], 
                 controller: InputController):
        self.ui_element = ui_element
        self.match = match
        self.controller = controller

    @property
    def exists(self) -> bool:
        return self.match is not None
    
    @property
    def name(self) -> str:
        return self.ui_element.name if self.ui_element else "Unknown"
    

    def click(self, offset: Optional[Tuple[int, int]] = None, coords: Optional[Tuple[int, int]] = None, 
              clicks: int = 1, interval: float = 0.1, verify: Optional['SearchRegion'] = None, 
              retries_ver: int = 3, timeout_ver: int = 3, disappear_ver: bool = False, self_ver: bool = True) -> Self:
        """
        coords: Absolute (x, y) override.
        offset: Relative (dx, dy) from the match center.
        verify: SearchRegion to check for after clicking.
        """     
        
        if self.exists:
            if coords:
                target_x, target_y = coords
            else:
                cx, cy = self.match.center
                dx, dy = offset or (0, 0)
                target_x, target_y = cx + dx, cy + dy
        else:
            return self
    
        state0 = None
        if verify is not None and verify.default_target is None:
            state0 = verify.screenshot()

        def perform_click():
            self.controller.click(target_x, target_y, clicks=clicks, interval=interval)

        def is_verified() -> bool:
            if verify is None:
                return True
                
            if state0 is not None:
                # Region Change Check
                current_state = verify.screenshot()
                
                matches = verify.default_strategy.find_matches(current_state, state0, 0.98)
                return len(matches) == 0
            else:
                is_element = verify.check()
                # Element Appearance Check
                if not disappear_ver:
                    return is_element
                # Element Disappearance Check
                return not is_element

        perform_click()

        if verify is None:
            return self

        for attempt in range(retries_ver):
            deadline = time.monotonic() + timeout_ver
            
            while time.monotonic() < deadline:
                if is_verified():
                    return self
                time.sleep(0.1)
            
            if self_ver and self.ui_element and not self.ui_element.check():
                raise RuntimeError(f"Click target disappeared after failed verification.")
                
            print(f"Verifier failed (attempt {attempt + 1}/{retries_ver}). Re-clicking...")
            perform_click()
        raise RuntimeError(f"Verification failed after {retries_ver} retries.")
    
    @property
    def box(self) -> tuple[int, int, int, int] | None:
        if self.exists:
            return self.match.box
        return None

    @property
    def center(self) -> tuple[int, int] | None:
        if self.exists:
            return self.match.center
        return None

    @property
    def score(self) -> float | None:
        if self.exists:
            return self.match.score
        return None
    
    def __bool__(self):
        return self.exists

    def __repr__(self):
        if not self.exists:
            return f"<Target name='{self.name}' NOT FOUND>"

        x, y, w, h = self.match.box
        return (
            f"<Target name='{self.name}' "
            f"box=({x},{y},{w},{h}) "
            f"score={self.match.score:.3f}>"
        )