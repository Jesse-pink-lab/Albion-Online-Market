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
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
            self.last = now
            need = tokens - self.tokens
            if need > 0:
                time.sleep(need / self.rate)
                self.tokens = 0
            else:
                self.tokens -= tokens

bucket = TokenBucket(rate_per_sec=2.0, capacity=4)
