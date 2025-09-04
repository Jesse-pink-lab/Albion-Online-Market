import time
import threading

class TokenBucket:
    def __init__(self, rate_per_sec: float = 2.0, capacity: int = 4):
        self.rate = rate_per_sec
        self.capacity = capacity
        self.tokens = capacity
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, tokens: float = 1.0):
        while True:
            sleep_for = 0.0
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
                self.last = now
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                need = tokens - self.tokens
                sleep_for = need / self.rate if self.rate > 0 else 0.05
            if sleep_for > 0:
                time.sleep(sleep_for)

bucket = TokenBucket(rate_per_sec=2.0, capacity=4)
