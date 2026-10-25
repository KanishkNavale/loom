# (import operator

# import numpy as np

# from loom.replay_buffers.uniform import ReplayBuffer


# class SegmentTree:
#     def __init__(self, capacity, scalar_op, vector_op, neutral):
#         self.capacity = capacity
#         self.depth = capacity.bit_length() - 1
#         self.scalar_op = scalar_op
#         self.vector_op = vector_op
#         self.values = np.full(2 * capacity, neutral, dtype=np.float64)

#     @property
#     def root(self):
#         return self.values[1]

#     def __getitem__(self, indices):
#         return self.values[indices + self.capacity]

#     def set(self, index, value):
#         values = self.values
#         position = index + self.capacity
#         values[position] = value
#         for _ in range(self.depth):
#             position >>= 1
#             values[position] = self.scalar_op(
#                 values[2 * position], values[2 * position + 1]
#             )

#     def set_many(self, indices, new_values):
#         values = self.values
#         positions = indices + self.capacity
#         values[positions] = new_values
#         for _ in range(self.depth):
#             positions = positions >> 1
#             values[positions] = self.vector_op(
#                 values[2 * positions], values[2 * positions + 1]
#             )


# class SumTree(SegmentTree):
#     def __init__(self, capacity):
#         super().__init__(capacity, operator.add, np.add, 0.0)

#     def find(self, masses):
#         positions = np.ones(masses.shape, dtype=np.int64)
#         for _ in range(self.depth):
#             left = 2 * positions
#             left_values = self.values[left]
#             go_right = left_values <= masses
#             masses = np.where(go_right, masses - left_values, masses)
#             positions = left + go_right
#         return positions - self.capacity


# class PrioritizedReplayBuffer(ReplayBuffer):
#     initial_priority = 1.0

#     def __init__(self, size, alpha, seed=None):
#         if size < 1:
#             raise ValueError("size must be at least 1")
#         if alpha < 0:
#             raise ValueError("alpha must be non-negative")
#         super().__init__(size)
#         capacity = 1 << (size - 1).bit_length()
#         self._alpha = alpha
#         self._limit = size
#         self._rng = np.random.default_rng(seed)
#         self._sum = SumTree(capacity)
#         self._min = SegmentTree(capacity, min, np.minimum, np.inf)
#         self._max = SegmentTree(capacity, max, np.maximum, -np.inf)
#         self._versions = np.zeros(size, dtype=np.int64)

#     def add(self, *args, **kwargs):
#         slot = self._next_idx
#         super().add(*args, **kwargs)
#         self._max.set(slot, -np.inf)
#         replayed_max = self._max.root
#         priority = (
#             replayed_max
#             if replayed_max > 0
#             else self.initial_priority**self._alpha
#         )
#         self._sum.set(slot, priority)
#         self._min.set(slot, priority)
#         self._versions[slot] += 1

#     def _sample_proportional(self, batch_size):
#         segment = self._sum.root / batch_size
#         masses = (
#             np.arange(batch_size) + self._rng.random(batch_size)
#         ) * segment
#         return np.minimum(self._sum.find(masses), len(self._storage) - 1)

#     def sample(self, batch_size, beta):
#         if len(self._storage) == 0:
#             raise ValueError("cannot sample from an empty buffer")
#         if batch_size < 1:
#             raise ValueError("batch_size must be at least 1")
#         if beta < 0:
#             raise ValueError("beta must be non-negative")

#         slots = self._sample_proportional(batch_size)
#         weights = ((self._min.root / self._sum[slots]) ** beta).astype(
#             np.float32
#         )
#         handles = self._versions[slots] * self._limit + slots
#         return (*self._encode_sample(slots.tolist()), weights, handles)

#     def update_priorities(self, idxes, priorities):
#         handles = np.asarray(idxes, dtype=np.int64).ravel()
#         priorities = np.asarray(priorities, dtype=np.float64).ravel()
#         if handles.shape != priorities.shape:
#             raise ValueError("idxes and priorities must have the same length")
#         if not (np.isfinite(priorities).all() and (priorities > 0).all()):
#             raise ValueError("priorities must be finite and positive")
#         slots = handles % self._limit
#         stamped = handles // self._limit
#         current = self._versions[slots]
#         if ((stamped < 1) | (stamped > current)).any():
#             raise ValueError("idxes must be handles returned by sample")
#         live = stamped == current
#         slots, priorities = slots[live][::-1], priorities[live][::-1]
#         slots, first = np.unique(slots, return_index=True)
#         values = priorities[first] ** self._alpha
#         for tree in (self._sum, self._min, self._max):
#             tree.set_many(slots, values)
#         return int(live.sum())
# )
