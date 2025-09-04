import threading
import time
from typing import Optional


class TokenBucket:
    def __init__(self, rate_per_sec: float = 2.0, capacity: int = 4):
        self._rate = max(0.0, rate_per_sec)
        self._cap = max(1, int(capacity))
        self._tokens = float(self._cap)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = max(0.0, now - self._last)
        self._last = now
        if self._rate > 0:
            self._tokens = min(self._cap, self._tokens + elapsed * self._rate)

    def try_acquire(self, n: int = 1) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    def acquire(
        self,
        n: int = 1,
        timeout: Optional[float] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> bool:
        """
        Block until n tokens are available, or until timeout/cancel.
        Returns True on success, False on timeout/cancel.
        """
        deadline = None if timeout is None else (time.monotonic() + max(0.0, timeout))
        sleep_min = 0.01
        while True:
            if self.try_acquire(n):
                return True
            if cancel_event and cancel_event.is_set():
                return False
            now = time.monotonic()
            if deadline is not None and now >= deadline:
                return False
            with self._lock:
                need = max(0.0, n - self._tokens)
                wait = sleep_min if self._rate <= 0 else max(sleep_min, need / max(self._rate, 1e-9))
            remaining = float("inf") if deadline is None else max(0.0, deadline - now)
            time.sleep(min(wait, remaining, 0.25))

    @property
    def rate(self) -> float:
        return self._rate

    @rate.setter
    def rate(self, value: float) -> None:
        with self._lock:
            self._rate = max(0.0, float(value))

    @property
    def capacity(self) -> int:
        return self._cap

    @capacity.setter
    def capacity(self, value: int) -> None:
        with self._lock:
            self._cap = max(1, int(value))
            self._tokens = min(self._tokens, self._cap)

    @property
    def tokens(self) -> float:
        return self._tokens

    @tokens.setter
    def tokens(self, value: float) -> None:
        with self._lock:
            self._tokens = float(value)


bucket = TokenBucket(rate_per_sec=2.0, capacity=4)
