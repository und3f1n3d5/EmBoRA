#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small DQN-like module used by architecture-aligned agents.

The class follows standard DQN patterns: a policy network, a slower target
network, replay buffer, epsilon-greedy action selection, Bellman targets and
periodic target synchronization. It intentionally remains lightweight so smoke
experiments run quickly on CPU.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple
import random

try:  # pragma: no cover - exercised when torch is installed
    import torch
    import torch.nn as nn
    import torch.optim as optim
except Exception:  # pragma: no cover
    torch = None  # type: ignore
    nn = None  # type: ignore
    optim = None  # type: ignore


@dataclass
class Transition:
    state: List[float]
    action_index: int
    reward: float
    next_state: List[float]
    done: bool = False
    meta: Dict[str, object] | None = None


class _QNetwork(nn.Module):  # type: ignore[misc]
    def __init__(self, input_dim: int, output_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, output_dim),
        )

    def forward(self, x):  # pragma: no cover - trivial torch wrapper
        return self.net(x)


class DQNPolicy:
    """DQN-like epsilon-greedy policy with replay training.

    Side effects: select_action may decay no state; add_transition and train_step
    mutate replay/network/epsilon. If PyTorch is unavailable, it degrades to a
    deterministic heuristic while preserving the public fields used by metrics.
    """

    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        *,
        lr: float = 1e-3,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_min: float = 0.01,
        epsilon_decay: float = 0.995,
        buffer_size: int = 1000,
        batch_size: int = 32,
        target_update_frequency: int = 1000,
    ):
        self.input_dim = int(input_dim)
        self.output_dim = int(output_dim)
        self.gamma = float(gamma)
        self.epsilon = float(epsilon)
        self.epsilon_min = float(epsilon_min)
        self.epsilon_decay = float(epsilon_decay)
        self.batch_size = int(batch_size)
        self.target_update_frequency = int(target_update_frequency)
        self.replay_buffer: Deque[Transition] = deque(maxlen=int(buffer_size))
        self.train_steps = 0
        self.last_loss: Optional[float] = None
        self.torch_enabled = torch is not None and nn is not None and optim is not None
        if self.torch_enabled:
            self.policy_net = _QNetwork(self.input_dim, self.output_dim)
            self.target_net = _QNetwork(self.input_dim, self.output_dim)
            self.target_net.load_state_dict(self.policy_net.state_dict())
            self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
            self.loss_fn = nn.SmoothL1Loss()
        else:
            self.policy_net = None
            self.target_net = None
            self.optimizer = None
            self.loss_fn = None

    def select_action(self, state: List[float], legal_count: int, *, eval_mode: bool = False) -> int:
        """Return an action index in [0, legal_count); side-effect free in eval mode."""
        legal_count = max(1, min(int(legal_count), self.output_dim))
        if (not eval_mode) and random.random() < self.epsilon:
            return random.randrange(legal_count)
        if not self.torch_enabled:
            # Deterministic fallback: choose index from a simple score.
            return int(abs(sum(state)) * 1000) % legal_count
        with torch.no_grad():  # type: ignore[union-attr]
            x = torch.tensor([state], dtype=torch.float32)
            q_values = self.policy_net(x)[0][:legal_count]
            return int(torch.argmax(q_values).item())

    def add_transition(self, transition: Transition) -> None:
        """Append a transition to replay; mutates replay buffer."""
        self.replay_buffer.append(transition)

    def train_step(self) -> Optional[float]:
        """Run one minibatch DQN update when enough samples exist; mutates network."""
        if len(self.replay_buffer) < min(self.batch_size, 4) or not self.torch_enabled:
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            return None
        batch_size = min(self.batch_size, len(self.replay_buffer))
        batch = random.sample(list(self.replay_buffer), batch_size)
        states = torch.tensor([b.state for b in batch], dtype=torch.float32)
        actions = torch.tensor([[b.action_index] for b in batch], dtype=torch.long)
        rewards = torch.tensor([[b.reward] for b in batch], dtype=torch.float32)
        next_states = torch.tensor([b.next_state for b in batch], dtype=torch.float32)
        dones = torch.tensor([[1.0 if b.done else 0.0] for b in batch], dtype=torch.float32)
        q = self.policy_net(states).gather(1, actions)
        with torch.no_grad():
            next_q = self.target_net(next_states).max(1, keepdim=True)[0]
            target = rewards + (1.0 - dones) * self.gamma * next_q
        loss = self.loss_fn(q, target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self.train_steps += 1
        if self.train_steps % self.target_update_frequency == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.last_loss = float(loss.item())
        return self.last_loss
