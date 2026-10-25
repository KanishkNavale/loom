import random

import numpy as np

from loom.abstracts import BaseDataClass


class Transition(BaseDataClass):
    current_state: np.ndarray
    action: np.ndarray
    reward: float
    next_state: np.ndarray
    done: bool


class ReplayBuffer:
    def __init__(self, max_size: int) -> None:
        if max_size <= 0:
            raise ValueError("`max_size` must be a positive integer")

        self.max_size = max_size
        self._storage: list[Transition] = []

    @property
    def current_size(self) -> int:
        return len(self._storage)

    @property
    def is_full(self) -> bool:
        return len(self._storage) == self.max_size

    def add(self, transition: Transition) -> None:
        if self.current_size < self.max_size:
            self._storage.append(transition)
            return

        self._storage.pop(0)
        self._storage.append(transition)

    def sample(self, batch_size: int) -> list[Transition]:
        if not self._storage:
            raise ValueError("cannot sample from an empty buffer")

        if batch_size >= self.current_size:
            return list(self._storage)

        return random.sample(self._storage, k=batch_size)
