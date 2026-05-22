from dataclasses import dataclass
import logging
import time

from source.engine import StopExecution


@dataclass
class RuntimeState:
    move_animation: bool = False
    floor_lvl: int = 1
    dead_sinners_number: int = 0
    in_dungeon: bool = False

    def reset_dungeon(self):
        self.floor_lvl = 1
        self.dead_sinners_number = 0
        self.in_dungeon = True
        self.move_animation = False

    def update_floor(self, floor):
        self.floor_lvl = floor
    

class StuckMonitor:
    def __init__(self, timeout: float = 30.0, max_errors: int = 5):
        self.timeout = timeout
        self.max_errors = max_errors
        self.error_count = 0
        self.last_activity_time = time.time()

    def report_progress(self):
        self.last_activity_time = time.time()
        self.error_count = 0

    def report_error(self):
        self.error_count += 1
        if self.error_count > self.max_errors:
            self._trigger_termination()

    def is_stuck(self) -> bool:
        return (time.time() - self.last_activity_time) > self.timeout

    def _trigger_termination(self):
        logging.error("Critical Failure: System stuck.")
        raise StopExecution