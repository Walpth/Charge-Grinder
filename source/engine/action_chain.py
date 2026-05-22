import time
from typing import Callable, Optional

from .search_region import SearchRegion

class ActionChain:
    def __init__(self, controller, max_attempts: int = 5):
        self.controller = controller
        self.max_attempts = max_attempts
        self.steps = []
        self.warp_points = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.run()

    # Builder Methods

    def warp(self, region: 'SearchRegion') -> 'ActionChain':
        """Defines a resume point."""
        self.warp_points.append((region, len(self.steps)))
        return self

    def click(self, region: 'SearchRegion', verify: Optional['SearchRegion'] = None) -> 'ActionChain':
        self.steps.append({'type': 'click', 'region': region, 'verify': verify})
        return self

    def coord_click(self, x: int, y: int, verify: Optional['SearchRegion'] = None) -> 'ActionChain':
        self.steps.append({'type': 'coord', 'pos': (x, y), 'verify': verify})
        return self

    def call(self, func: Callable) -> 'ActionChain':
        self.steps.append({'type': 'call', 'func': func})
        return self


    def _resolve_verifiers(self):
        """Implicitly sets the next UI element as the verifier for the current click."""
        for i, step in enumerate(self.steps[:-1]):
            if step.get('verify') is None:
                for next_step in self.steps[i+1:]:
                    if next_step['type'] == 'click':
                        step['verify'] = next_step['region']
                        break

    def _find_current_state_index(self) -> int:
        """
        Resume logic: Scans the screen to find which step to warp to.
        """
        for region, index in self.warp_points:
            if region.check():
                return index
        raise RuntimeError("No recognized UI state found to resume from.")

    def run(self):
        self._resolve_verifiers()
        
        attempt = 0
        while attempt < self.max_attempts:
            current_idx = self._find_current_state_index()
            
            try:
                for i in range(current_idx, len(self.steps)):
                    step = self.steps[i]
                    
                    if step['type'] == 'call':
                        step['func']()
                    
                    elif step['type'] == 'click':
                        target = step['region'].locate()
                        if not target:
                            raise RuntimeError(f"Could not find {step['region'].name}")
                        target.click(verify=step['verify'])
                        
                    elif step['type'] == 'coord':
                        from .target import Target, MatchResult
                        Target(None, MatchResult(), self.controller).click(
                            coords=step['pos'], 
                            verify=step['verify']
                        )
                
                return
                
            except RuntimeError as e:
                if "No recognized UI" in str(e):
                    raise e
                
                attempt += 1
                print(f"Chain interrupted: {e}. Recovering (Attempt {attempt}/{self.max_attempts})...")
                time.sleep(0.2)
                
        raise RuntimeError(f"ActionChain failed after {self.max_attempts} attempts.")