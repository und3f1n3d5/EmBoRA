#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ ИСПРАВЛЕННЫЙ КОД АГЕНТА
РАЦИОНАЛЬНЫЙ МОДУЛЬ СТРЕМИТСЯ ТОЛЬКО К МАКСИМИЗАЦИИ ВЫИГРЫША

Изменение логики:
- РМ игнорирует ЭМ полностью при выборе действий
- РМ работает ТОЛЬКО с выигрышем (payoff) из игры
- ЭМ по-прежнему вычисляется и логируется для анализа
- Все эмоциональные метрики сохраняются для сравнения агентов
"""

import logging
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
import numpy as np
from datetime import datetime
import json
import copy

# ============================================================================
# УРОВНИ ЛОГИРОВАНИЯ И КОНФИГУРАЦИЯ
# ============================================================================

class LogLevel:
    """Уровни логирования для разных количеств деталей"""
    SILENT = 50      # Никаких логов
    MINIMAL = 40     # Только самое важное (ХОД, ИТОГ, ОШИБКИ)
    NORMAL = 30      # Стандартные логи (рекомендуется)
    VERBOSE = 20     # Расширенные логи (обучение, рефлексия)
    DEBUG = 10       # Все логи (для отладки)

# ============================================================================
# БАЗОВЫЕ КЛАССЫ И ПЕРЕЧИСЛЕНИЯ
# ============================================================================

class ActionType(Enum):
    """Типы действий агента"""
    GAME_ACTION = "game_action"
    REFOCUS = "refocus"
    REFLECTION = "reflection"

@dataclass
class GameResult:
    """Результат игрового действия"""
    action: str
    payoff: float
    game_state: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для update_from_game"""
        return {
            'action': self.action,
            'payoff': self.payoff,
            'game_state': self.game_state,
        }

# ============================================================================
# ЛОГИРОВАНИЕ (УЛУЧШЕНО)
# ============================================================================

class AgentLogger:
    """Специализированный логгер для агента с уровнями и форматированием"""

    def __init__(self, agent_name: str, log_level: int = LogLevel.NORMAL):
        self.agent_name = agent_name
        self.turn = 0
        self.log_level = log_level
        self.log_entries = []

        # Настройка логирования
        self.logger = logging.getLogger(f"Agent_{agent_name}")
        self.logger.setLevel(logging.DEBUG)

        # Удалить старые обработчики
        self.logger.handlers = []

        # Консоль с пользовательским форматом
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _should_log(self, level: int) -> bool:
        """Проверить нужно ли логировать на данном уровне"""
        return level >= self.log_level

    def log_turn_start(self, turn: int):
        """Логирование начала хода"""
        if not self._should_log(LogLevel.MINIMAL):
            return
        self.turn = turn
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f"ХОД {turn} НАЧАЛО")
        self.logger.info(f"{separator}\n")

    def log_game_state(self, game_state: 'GameState'):
        """Логирование состояния игры"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("📊 СОСТОЯНИЕ ИГРЫ:")
        for param, value in game_state.game_parameters.items():
            self.logger.debug(f" • {param}: {value:.2f}")
        self.logger.debug("")

    def log_agent_state(self, agent_state: 'AgentState'):
        """Логирование состояния агента"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("🧠 СОСТОЯНИЕ АГЕНТА:")
        self.logger.debug(f" • Благополучие: {agent_state.wellbeing:.2f}")
        self.logger.debug(f" • Настроение: {agent_state.mood:.2f}")
        self.logger.debug(f" • Усталость: {agent_state.fatigue:.2f}")
        self.logger.debug(f" • Ресурсы: {agent_state.resources:.2f}")
        self.logger.debug("")

    def log_values(self, values: 'Values'):
        """Логирование ценностей"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("📈 ЦЕННОСТИ:")
        for vtype in ValueType:
            current = values.current_values.get(vtype, 0)
            previous = values.previous_values.get(vtype, 0)
            desired = values.desired_values.get(vtype, 100)
            change = current - previous
            change_str = f"({change:+.1f})" if change != 0 else "(без изм)"
            self.logger.debug(
                f" • {vtype.name}: {current:.1f}/{desired:.1f} "
                f"[пред: {previous:.1f}] {change_str}"
            )
        self.logger.debug("")

    def log_priorities(self, priorities: Dict[str, float]):
        """Логирование приоритетов"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("⚡ ПРИОРИТЕТЫ:")
        sorted_priorities = sorted(priorities.items(), key=lambda x: x[1], reverse=True)
        for vtype_name, priority in sorted_priorities[:3]:  # Только топ 3
            bar_len = int(priority * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            self.logger.debug(f" • {vtype_name}: {priority:.2f} [{bar}]")
        self.logger.debug("")

    def log_ots_evaluation(self, reaction_intensity: float, max_focus_value: str):
        """Логирование оценки ОТС"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("🎯 ОЦЕНКА ТЕКУЩЕГО СОСТОЯНИЯ (ОТС):")
        emoji = "😊" if reaction_intensity > 0 else "😠"
        self.logger.debug(f" • Интенсивность: {reaction_intensity:+.3f} {emoji}")
        self.logger.debug(f" • На ценность: {max_focus_value}")
        self.logger.debug("")

    def log_emotional_response(self, action: str, intensity: float):
        """Логирование эмоциональной реакции"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        emoji = "😊" if intensity > 0.5 else "😐" if intensity > -0.5 else "😠"
        self.logger.debug(f"💭 ЭМОЦИОНАЛЬНЫЙ МОДУЛЬ (ЭМ):")
        self.logger.debug(f" • Действие: {action}")
        self.logger.debug(f" • Интенсивность: {intensity:+.3f} {emoji}")
        self.logger.debug("")

    def log_rational_decision(self, action: str, action_type: str, override: bool = False):
        """Логирование рационального решения"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        override_str = "⚠️ ПЕРЕОПРЕДЕЛЕНО" if override else "✓"
        self.logger.debug(f"🤔 РАЦИОНАЛЬНЫЙ МОДУЛЬ (РМ):")
        self.logger.debug(f" • Опция: {action} {override_str}")
        self.logger.debug(f" • Тип: {action_type}")
        self.logger.debug("")

    def log_action_execution(self, action: str, action_type: str, params: Optional[Dict] = None):
        """Логирование выполнения действия"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        param_str = ""
        if params:
            param_str = " | " + ", ".join([f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                                          for k, v in params.items()])
        self.logger.debug(f"⚙️ ДЕЙСТВИЕ: {action} ({action_type}){param_str}")
        self.logger.debug("")

    def log_learning(self, em_buffer_size: int, rm_buffer_size: int,
                     em_loss: Optional[float] = None, rm_loss: Optional[float] = None,
                     em_epsilon: Optional[float] = None, rm_epsilon: Optional[float] = None):
        """Логирование обучения с потерями И epsilon"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("📚 ОБУЧЕНИЕ МОДУЛЕЙ:")

        # ЭМ
        if em_buffer_size >= 16:
            loss_str = f"loss: {em_loss:.4f}" if em_loss is not None else "обучение"
            epsilon_str = f"ε: {em_epsilon:.3f}" if em_epsilon is not None else ""
            self.logger.debug(f" • ЭМ: ✓ {loss_str} {epsilon_str} (буфер: {em_buffer_size})")
        else:
            self.logger.debug(f" • ЭМ: ⏳ {em_buffer_size}/16 (ожидание)")

        # РМ
        if rm_buffer_size >= 16:
            loss_str = f"loss: {rm_loss:.4f}" if rm_loss is not None else "обучение"
            epsilon_str = f"ε: {rm_epsilon:.3f}" if rm_epsilon is not None else ""
            self.logger.debug(f" • РМ: ✓ {loss_str} {epsilon_str} (буфер: {rm_buffer_size})")
        else:
            self.logger.debug(f" • РМ: ⏳ {rm_buffer_size}/16 (ожидание)")
        self.logger.debug("")

    def log_reflection(self, turn: int, priority_changes: Dict, desired_changes: Dict):
        """Логирование стратегической рефлексии"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.info(f"🔮 СТРАТЕГИЧЕСКАЯ РЕФЛЕКСИЯ (ход {turn}):")
        # Приоритеты
        self.logger.info(" Изменения приоритетов:")
        for vtype_name, new_priority in list(priority_changes.items())[:3]:
            self.logger.info(f" • {vtype_name}: {new_priority:.2f}")
        # Желаемые значения
        self.logger.info(" Изменения целей:")
        for vtype_name, new_desired in list(desired_changes.items())[:3]:
            self.logger.info(f" • {vtype_name}: {new_desired:.1f}")
        self.logger.info("")

    def log_recovery(self, fatigue: float, mood: float, resources: float):
        """Логирование восстановления"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("🔄 ВОССТАНОВЛЕНИЕ:")
        self.logger.debug(f" • Усталость: {fatigue:.2f} | Настроение: {mood:+.2f} | Ресурсы: {resources:.2f}")
        self.logger.debug("")

    def log_turn_summary(self, turn: int, overall_state: float, action: str, payoff: float = 0.0):
        """Логирование итога хода"""
        if not self._should_log(LogLevel.NORMAL):
            return
        separator = "=" * 80
        self.logger.info(f"📋 ХОД {turn} ИТОГ:")
        self.logger.info(f" • Действие: {action}")
        self.logger.info(f" • Выигрыш: {payoff:+.3f} 💰")
        self.logger.info(f" • Состояние: {overall_state:+.3f}")
        self.logger.info(f"{separator}\n")

    def log_episode_summary(self, num_turns: int, total_payoff: float, avg_payoff: float):
        """Логирование итога эпизода"""
        if not self._should_log(LogLevel.NORMAL):
            return
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f"📊 ИТОГ ЭПИЗОДА ({num_turns} ходов)")
        self.logger.info(f" • Общий выигрыш: {total_payoff:+.3f} 💰")
        self.logger.info(f" • Средний выигрыш за ход: {avg_payoff:+.3f} 💰")
        self.logger.info(f"{separator}\n")

# ============================================================================
# ПЕРЕЧИСЛЕНИЯ (ENUMS)
# ============================================================================

class ValueType(Enum):
    """Типы ценностей"""
    SECURITY = "Безопасность"
    EQUALITY = "Равенство"
    RELATIONSHIPS = "Отношения"
    PAYOFF = "Выигрыш"

class PersonalityType(Enum):
    """Типы личности"""
    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    NEUTRAL = "neutral"

class EmotionalIntensityType(Enum):
    """Типы интенсивности эмоций"""
    HIGH = "high"
    LOW = "low"
    NEUTRAL = "neutral"

# ============================================================================
# КЛАССЫ ДАННЫХ (DATACLASSES)
# ============================================================================

@dataclass
class GameState:
    """Состояние игры"""
    game_parameters: Dict[str, float] = field(default_factory=dict)
    available_actions: List[Dict[str, Any]] = field(default_factory=list)

    def copy(self):
        return GameState(
            game_parameters=self.game_parameters.copy(),
            available_actions=[a.copy() for a in self.available_actions]
        )

@dataclass
class Values:
    """Система ценностей агента"""
    current_values: Dict[ValueType, float] = field(default_factory=dict)
    previous_values: Dict[ValueType, float] = field(default_factory=dict)
    desired_values: Dict[ValueType, float] = field(default_factory=dict)
    value_priorities: Dict[ValueType, float] = field(default_factory=dict)

    def __post_init__(self):
        """Инициализация значений по умолчанию"""
        if not self.current_values:
            for vtype in ValueType:
                self.current_values[vtype] = 50.0
                self.previous_values[vtype] = 50.0
                self.desired_values[vtype] = 100.0
                self.value_priorities[vtype] = 0.25

    @staticmethod
    def create_by_personality(personality_type: PersonalityType) -> 'Values':
        """Приоритеты зависят от типа личности"""
        values = Values()
        if personality_type == PersonalityType.OPTIMISTIC:
            values.value_priorities[ValueType.PAYOFF] = 1.2
            values.value_priorities[ValueType.RELATIONSHIPS] = 0.9
            values.value_priorities[ValueType.SECURITY] = 0.5
            values.value_priorities[ValueType.EQUALITY] = 0.4
        elif personality_type == PersonalityType.PESSIMISTIC:
            values.value_priorities[ValueType.SECURITY] = 1.5
            values.value_priorities[ValueType.PAYOFF] = 0.6
            values.value_priorities[ValueType.RELATIONSHIPS] = 0.5
            values.value_priorities[ValueType.EQUALITY] = 0.4
        else:  # NEUTRAL
            for vtype in ValueType:
                values.value_priorities[vtype] = 0.8
        return values

    def copy(self) -> 'Values':
        """Копировать состояние ценностей"""
        return Values(
            current_values=self.current_values.copy(),
            previous_values=self.previous_values.copy(),
            desired_values=self.desired_values.copy(),
            value_priorities=self.value_priorities.copy()
        )

    def update_value(self, value_type: ValueType, value: float):
        """Обновить значение ценности"""
        self.current_values[value_type] = np.clip(value, 0.0, 100.0)

    def update_previous_values(self):
        """Обновить предыдущие значения"""
        self.previous_values = self.current_values.copy()

    def set_desired_value(self, value_type: ValueType, desired: float):
        """Установить желаемое значение ценности"""
        self.desired_values[value_type] = np.clip(desired, 0.0, 100.0)

    def set_priority(self, value_type: ValueType, priority: float):
        """Установить приоритет ценности"""
        self.value_priorities[value_type] = np.clip(priority, 0.0, 1.5)

@dataclass
class AgentState:
    """Внутреннее состояние агента"""
    wellbeing: float = 0.5
    mood: float = 0.0
    fatigue: float = 0.0
    resources: float = 1.0
    focused_value: Optional[ValueType] = None
    refocus_count: int = 0
    total_refocus_count: int = 0

    def increment_refocus_count(self):
        """Увеличить счетчик рефокусов"""
        self.refocus_count += 1
        self.total_refocus_count += 1

    def reset_refocus_count(self):
        """Сбросить счетчик рефокусов"""
        self.refocus_count = 0

    def calculate_overall_state(self) -> float:
        """Рассчитать общее состояние"""
        overall = self.wellbeing + self.mood - self.fatigue
        return overall

    def update_fatigue(self, emotional_intensity: float):
        """Обновить усталость на основе интенсивности эмоции"""
        intensity_effect = abs(emotional_intensity) / 10.0
        self.fatigue += intensity_effect
        self.fatigue = np.clip(self.fatigue, 0.0, 1.0)

    def consume_resources(self, amount: float):
        """Потребить ресурсы"""
        self.resources -= amount
        self.resources = np.clip(self.resources, 0.0, 1.0)

    def recover_resources(self, recovery_rate: float = 0.05):
        """Восстановить ресурсы"""
        self.resources += recovery_rate
        self.resources = np.clip(self.resources, 0.0, 1.0)

    def apply_fatigue_decay(self):
        """Применить затухание усталости и стабилизацию настроения"""
        self.fatigue -= 0.05
        self.fatigue = max(0.0, self.fatigue)
        self.mood *= 0.9
        if abs(self.mood) < 0.01:
            self.mood = 0.0

# ============================================================================
# DQN СЕТЬ С ПАРАМЕТРАМИ
# ============================================================================

class DQNNetworkWithParams(nn.Module):
    """
    Двухголовая DQN сеть для выбора действий И параметров
    """
    def __init__(self, input_size: int, num_actions: int, num_param_bins: int = 10, hidden_size: int = 128):
        super(DQNNetworkWithParams, self).__init__()
        self.num_actions = num_actions
        self.num_param_bins = num_param_bins

        # Общий энкодер
        self.encoder = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU()
        )

        # Голова для действий
        self.action_head = nn.Linear(hidden_size, num_actions)

        # Голова для параметров
        self.param_head = nn.Linear(hidden_size, num_actions * num_param_bins)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Прямой проход
        Returns:
            action_q_values: (batch_size, num_actions)
            param_q_values: (batch_size, num_actions, num_param_bins)
        """
        features = self.encoder(x)
        action_q = self.action_head(features)
        param_q = self.param_head(features)
        param_q = param_q.view(-1, self.num_actions, self.num_param_bins)
        return action_q, param_q

# ============================================================================
# КОМПОНЕНТЫ АРХИТЕКТУРЫ
# ============================================================================

class CurrentStateEvaluation:
    """✅ Модуль оценки текущего состояния (ОТС)"""

    def __init__(self, logger: AgentLogger, character_traits: 'CharacterTraits'):
        self.logger = logger
        self.character_traits = character_traits

    def calculate_threshold(self, state: AgentState) -> float:
        """Пороговые модификаторы"""
        chunk_1 = self.character_traits.get_chunk_1()
        fatigue_mod = 1.0 if state.fatigue > 0.6 else 0.0
        mood_mod = 1.0 if abs(state.mood) > 0.25 else 0.0
        threshold = chunk_1 - fatigue_mod - mood_mod
        return np.clip(threshold, 0.1, 1.5)

    def calculate_urgency(self, current: float, desired: float, priority: float) -> float:
        """Рассчитать срочность для ценности"""
        distance = current - desired
        if distance >= 0:
            return priority * 0.5
        else:
            percentage_below = abs(distance) / desired if desired > 0 else 0
            urgency_value = priority * (-1.0 - percentage_below)
            return np.clip(urgency_value, -1, 1)

    def evaluate_values_changes(self, values: Values, state: AgentState) -> Tuple[float, ValueType]:
        """Полная реализация с правильной интенсивностью"""
        max_focus = 0.0
        reaction_intensity = 0.0
        max_focus_value_type = ValueType.SECURITY
        threshold = self.calculate_threshold(state)

        if state.focused_value is not None:
            value_type = state.focused_value
            current = values.current_values.get(value_type, 50.0)
            desired = values.desired_values.get(value_type, 100.0)
            priority = values.value_priorities.get(value_type, 0.25)
            urgency = self.calculate_urgency(current, desired, priority)
            intensity = urgency * priority
            focus = abs(intensity - 0.1)
            return intensity, value_type
        else:
            for value_type in ValueType:
                current = values.current_values.get(value_type, 50.0)
                desired = values.desired_values.get(value_type, 100.0)
                priority = values.value_priorities.get(value_type, 0.25)
                urgency = self.calculate_urgency(current, desired, priority)
                intensity = urgency * priority
                focus = abs(intensity - 0.1)
                if focus >= threshold:
                    if focus > max_focus:
                        max_focus = focus
                        reaction_intensity = intensity
                        max_focus_value_type = value_type
            return reaction_intensity, max_focus_value_type

class CharacterTraits:
    """Черты характера с chunk_1 и chunk_2"""

    def __init__(self, personality: PersonalityType, intensity: EmotionalIntensityType):
        self.personality = personality
        self.intensity = intensity
        self._initialize_chunks()

    def _initialize_chunks(self):
        """Инициализировать chunk_1 и chunk_2"""
        if self.personality == PersonalityType.OPTIMISTIC:
            self.chunk_1 = 0.3
        elif self.personality == PersonalityType.PESSIMISTIC:
            self.chunk_1 = 0.7
        else:
            self.chunk_1 = 0.5

        if self.intensity == EmotionalIntensityType.HIGH:
            self.chunk_2 = 1.5
        elif self.intensity == EmotionalIntensityType.LOW:
            self.chunk_2 = 0.5
        else:
            self.chunk_2 = 1.0

    def get_chunk_1(self) -> float:
        """Получить пороговое значение"""
        return self.chunk_1

    def get_chunk_2(self) -> float:
        """Получить коэффициент интенсивности"""
        return self.chunk_2

    def get_emotional_baseline(self) -> float:
        """Базовая линия эмоциональности"""
        baseline = 0.0
        if self.personality == PersonalityType.OPTIMISTIC:
            baseline += 0.3
        elif self.personality == PersonalityType.PESSIMISTIC:
            baseline -= 0.3
        if self.intensity == EmotionalIntensityType.HIGH:
            baseline *= 1.5
        elif self.intensity == EmotionalIntensityType.LOW:
            baseline *= 0.5
        return baseline

# ============================================================================
# СТРАТЕГИЯ ВЫБОРА ДЕЙСТВИЙ С ПАРАМЕТРАМИ
# ============================================================================

@dataclass
class ActionOption:
    """Опция действия с параметрами"""
    name: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        if self.params:
            params_str = ", ".join([f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                                   for k, v in self.params.items()])
            return f"{self.name}({params_str})"
        return self.name

class ActionSpaceBuilder:
    """Конструктор пространства действий с параметрами"""

    def __init__(self, game_actions: Optional[List[Dict[str, Any]]] = None):
        self.game_actions = game_actions or []
        self.base_actions = []
        self._build_action_space()

    def _build_action_space(self):
        """Построить полное пространство действий"""
        self.base_actions = []
        for action_spec in self.game_actions:
            action_name = action_spec.get('name', 'unknown')
            has_params = action_spec.get('params', [])
            if has_params:
                self.base_actions.append({
                    'name': action_name,
                    'has_params': True,
                    'param_specs': has_params
                })
            else:
                self.base_actions.append({
                    'name': action_name,
                    'has_params': False,
                    'param_specs': []
                })

    def get_action_features_size(self) -> int:
        """Получить размер вектора признаков"""
        return len(self.base_actions) * 2

# ============================================================================
# ЭМОЦИОНАЛЬНЫЙ МОДУЛЬ
# ============================================================================

class EmotionalModule:
    """
    ✅ Эмоциональный модуль с обучением действий И параметров
    """

    def __init__(self, action_space: ActionSpaceBuilder, logger: AgentLogger,
                 num_param_bins: int = 10, device='cpu'):
        self.action_space = action_space
        self.logger = logger
        self.device = device
        self.replay_buffer = []
        self.num_param_bins = num_param_bins

        num_actions = len(action_space.base_actions)

        self.q_network = DQNNetworkWithParams(
            input_size=16,
            num_actions=num_actions,
            num_param_bins=num_param_bins,
            hidden_size=128
        ).to(device)

        self.target_network = DQNNetworkWithParams(
            input_size=16,
            num_actions=num_actions,
            num_param_bins=num_param_bins,
            hidden_size=128
        ).to(device)

        self.target_network.load_state_dict(self.q_network.state_dict())
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()

        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01

        self.update_counter = 0
        self.target_update_freq = 1000
        self.last_loss = None
        self.gamma = 0.99

        self.last_action_idx = 0
        self.last_param_bin_idx = 0

    def build_input_features(self, values: Values, state: AgentState) -> np.ndarray:
        """Полная информация о ценностях для предсказания"""
        features = []
        for vtype in ValueType:
            current = values.current_values.get(vtype, 50.0)
            desired = values.desired_values.get(vtype, 100.0)
            priority = values.value_priorities.get(vtype, 0.25)
            current_norm = current / 100.0
            desired_norm = desired / 100.0
            features.extend([current_norm, desired_norm, priority])
        features.extend([
            state.wellbeing,
            state.mood,
            state.fatigue,
            state.resources
        ])
        return np.array(features, dtype=np.float32)

    def discretize_param(self, continuous_value: float, min_val: float = 0.0,
                        max_val: float = 1.0) -> int:
        """Дискретизировать непрерывный параметр"""
        normalized = (continuous_value - min_val) / (max_val - min_val)
        normalized = np.clip(normalized, 0.0, 0.999)
        bin_idx = int(normalized * self.num_param_bins)
        return bin_idx

    def undiscretize_param(self, bin_idx: int, min_val: float = 0.0,
                          max_val: float = 1.0) -> float:
        """Восстановить непрерывное значение из индекса бина"""
        normalized = (bin_idx + 0.5) / self.num_param_bins
        continuous_value = min_val + normalized * (max_val - min_val)
        return continuous_value

    def select_action_and_param_greedy(self, state_features: np.ndarray) -> Tuple[str, int, float, int]:
        """Выбрать лучшее действие И параметр"""
        features_tensor = torch.FloatTensor(state_features).unsqueeze(0).to(self.device)
        with torch.no_grad():
            action_q, param_q = self.q_network(features_tensor)
            action_q = action_q.cpu().numpy()[0]
            param_q = param_q.cpu().numpy()[0]

        action_idx = np.argmax(action_q)
        action_name = self.action_space.base_actions[action_idx]['name']

        param_q_for_action = param_q[action_idx]
        param_bin_idx = np.argmax(param_q_for_action)

        action_spec = self.action_space.base_actions[action_idx]
        if action_spec['has_params']:
            param_value = self.undiscretize_param(param_bin_idx, min_val=1.0, max_val=10.0)
        else:
            param_value = 0.0

        return action_name, action_idx, param_value, param_bin_idx

    def select_action_and_param_explore(self) -> Tuple[str, int, float, int]:
        """Выбрать случайное действие И параметр"""
        action_idx = np.random.randint(0, len(self.action_space.base_actions))
        action_name = self.action_space.base_actions[action_idx]['name']

        param_bin_idx = np.random.randint(0, self.num_param_bins)

        action_spec = self.action_space.base_actions[action_idx]
        if action_spec['has_params']:
            param_value = self.undiscretize_param(param_bin_idx, min_val=1.0, max_val=10.0)
        else:
            param_value = 0.0

        return action_name, action_idx, param_value, param_bin_idx

    def select_action(self, state_features: np.ndarray, training: bool = True) -> Tuple[str, int, float, int]:
        """Epsilon-greedy выбор действия И параметра"""
        if training and np.random.random() < self.epsilon:
            return self.select_action_and_param_explore()
        else:
            return self.select_action_and_param_greedy(state_features)

    def generate_action_params(self, action_name: str, param_value: float) -> Dict[str, float]:
        """Сгенерировать параметры для действия"""
        params = {}
        for action_spec in self.action_space.base_actions:
            if action_spec['name'] == action_name and action_spec['has_params']:
                for param_name in action_spec['param_specs']:
                    params[param_name] = param_value
        return params

    def forward(self, values: Values, state: AgentState) -> Tuple[ActionOption, float]:
        """Выбрать действие + параметры и вернуть интенсивность"""
        features = self.build_input_features(values, state)
        action_name, action_idx, param_value, param_bin_idx = self.select_action(features, training=True)

        self.last_action_idx = action_idx
        self.last_param_bin_idx = param_bin_idx

        params = self.generate_action_params(action_name, param_value)
        action_option = ActionOption(name=action_name, params=params)

        # Эмоциональная интенсивность
        emotional_intensity = np.clip(state.mood + np.random.randn() * 0.3, -1.5, 1.5)

        return action_option, emotional_intensity

    def add_experience(self, state_features: np.ndarray, action_idx: int, param_bin_idx: int,
                      reward: float, next_state_features: np.ndarray, done: bool):
        """Добавить полный переход с параметрами"""
        experience = {
            'state': state_features.astype(np.float32),
            'action': action_idx,
            'param_bin': param_bin_idx,
            'reward': float(reward),
            'next_state': next_state_features.astype(np.float32),
            'done': bool(done)
        }
        self.replay_buffer.append(experience)
        if len(self.replay_buffer) > 1000:
            self.replay_buffer.pop(0)

    def train_on_feedback(self, reaction_intensity: float, values: Values,
                         state: AgentState, game_state: GameState,
                         emotional_action: ActionOption, emotional_intensity: float,
                         next_values: Optional[Values] = None,
                         next_state: Optional[AgentState] = None):
        """Обучение ЭМ на фидбеке от ОТС"""
        current_features = self.build_input_features(values, state)

        if next_state is not None and next_values is not None:
            next_features = self.build_input_features(next_values, next_state)
        else:
            next_features = current_features

        action_idx = self.last_action_idx
        param_bin_idx = self.last_param_bin_idx

        self.add_experience(
            state_features=current_features,
            action_idx=action_idx,
            param_bin_idx=param_bin_idx,
            reward=reaction_intensity,
            next_state_features=next_features,
            done=False
        )

        if len(self.replay_buffer) >= 16:
            self.last_loss = self._train_batch(batch_size=min(32, len(self.replay_buffer) // 2))

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def _train_batch(self, batch_size: int):
        """Обучение с Target Network"""
        indices = np.random.choice(len(self.replay_buffer), batch_size, replace=False)
        batch = [self.replay_buffer[i] for i in indices]

        states = torch.FloatTensor(np.array([exp['state'] for exp in batch])).to(self.device)
        actions = torch.LongTensor([exp['action'] for exp in batch]).to(self.device)
        param_bins = torch.LongTensor([exp['param_bin'] for exp in batch]).to(self.device)
        rewards = torch.FloatTensor([exp['reward'] for exp in batch]).to(self.device)
        next_states = torch.FloatTensor(np.array([exp['next_state'] for exp in batch])).to(self.device)
        dones = torch.FloatTensor([1.0 - float(exp['done']) for exp in batch]).to(self.device)

        # Q-значения текущей сети
        action_q, param_q = self.q_network(states)

        action_q_for_actions = action_q.gather(1, actions.unsqueeze(1)).squeeze(1)

        batch_indices = torch.arange(batch_size, device=self.device)
        param_q_for_actions = param_q[batch_indices, actions, :]
        param_q_for_selected = param_q_for_actions.gather(1, param_bins.unsqueeze(1)).squeeze(1)

        # Целевые Q-значения от TARGET СЕТИ
        with torch.no_grad():
            next_action_q, next_param_q = self.target_network(next_states)
            max_next_action_q = torch.max(next_action_q, dim=1)[0]
            best_next_actions = torch.argmax(next_action_q, dim=1)
            next_param_q_for_best = next_param_q[batch_indices, best_next_actions, :]
            max_next_param_q = torch.max(next_param_q_for_best, dim=1)[0]

        # BELLMAN EQUATION
        target_action_q = rewards + (self.gamma * max_next_action_q * dones)
        target_param_q = rewards + (self.gamma * max_next_param_q * dones)

        action_loss = self.criterion(action_q_for_actions, target_action_q)
        param_loss = self.criterion(param_q_for_selected, target_param_q)

        total_loss = action_loss + param_loss

        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), max_norm=1.0)
        self.optimizer.step()

        self.update_counter += 1
        if self.update_counter % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())

        return total_loss.item()

# ============================================================================
# РАЦИОНАЛЬНЫЙ МОДУЛЬ (✅ ИСПРАВЛЕННЫЙ - МАКСИМИЗИРУЕТ ТОЛЬКО ВЫИГРЫШ)
# ============================================================================

class RationalModule:
    """
    ✅ ОБНОВЛЕНО: Рациональный модуль, который ИГНОРИРУЕТ ЭМ полностью
    и МАКСИМИЗИРУЕТ ТОЛЬКО ВЫИГРЫШ в игре

    Ключевые изменения:
    - РМ работает ТОЛЬКО с rewards из game_state (payoff)
    - РМ НЕ смотрит на выход ЭМ при обучении
    - ЭМ по-прежнему вычисляется для логирования и анализа
    - Все метрики ЭМ сохраняются в experience для сравнения агентов
    """

    def __init__(self, action_space: 'ActionSpaceBuilder', logger: 'AgentLogger',
                 num_param_bins: int = 10, device='cpu'):
        self.action_space = action_space
        self.logger = logger
        self.device = device
        self.replay_buffer = []
        self.num_param_bins = num_param_bins

        # Опции РМ: только игровые действия
        self.options = []
        self._build_options()

        num_options = len(self.options)

        self.q_network = DQNNetworkWithParams(
            input_size=8,  # УМЕНЬШЕНО: РМ работает с меньшим input
            num_actions=num_options,
            num_param_bins=num_param_bins,
            hidden_size=128
        ).to(device)

        self.target_network = DQNNetworkWithParams(
            input_size=8,
            num_actions=num_options,
            num_param_bins=num_param_bins,
            hidden_size=128
        ).to(device)

        self.target_network.load_state_dict(self.q_network.state_dict())
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()

        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01

        self.update_counter = 0
        self.target_update_freq = 1000
        self.last_loss = None
        self.gamma = 0.99

        self.last_option_idx = 0
        self.last_param_bin_idx = 0

    def _build_options(self):
        """Построить опции РМ (только игровые действия!)"""
        for action_spec in self.action_space.base_actions:
            self.options.append({
                'type': 'game_action',
                'name': action_spec['name'],
                'has_params': action_spec['has_params'],
                'param_specs': action_spec['param_specs']
            })

    def build_input_features(self, game_state: 'GameState') -> np.ndarray:
        """
        ✅ НОВОЕ: РМ работает ТОЛЬКО с параметрами игры
        Ignores emotional state completely
        """
        features = []

        # Добавить параметры игры
        if hasattr(game_state, 'game_parameters'):
            for param_name in sorted(game_state.game_parameters.keys()):
                param_value = game_state.game_parameters.get(param_name, 0.0)
                param_norm = param_value / 100.0  # Нормализовать
                features.append(param_norm)

        # Дополнить до 8 признаков нулями если необходимо
        while len(features) < 8:
            features.append(0.0)

        return np.array(features[:8], dtype=np.float32)

    def discretize_param(self, continuous_value: float, min_val: float = 0.0,
                        max_val: float = 1.0) -> int:
        """Дискретизировать параметр"""
        normalized = (continuous_value - min_val) / (max_val - min_val)
        normalized = np.clip(normalized, 0.0, 0.999)
        bin_idx = int(normalized * self.num_param_bins)
        return bin_idx

    def undiscretize_param(self, bin_idx: int, min_val: float = 0.0,
                          max_val: float = 1.0) -> float:
        """Восстановить параметр"""
        normalized = (bin_idx + 0.5) / self.num_param_bins
        continuous_value = min_val + normalized * (max_val - min_val)
        return continuous_value

    def select_option_greedy(self, state_features: np.ndarray) -> Tuple[int, int, float]:
        """Выбрать лучшую опцию И параметр (greedy)"""
        features_tensor = torch.FloatTensor(state_features).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action_q, param_q = self.q_network(features_tensor)
            action_q = action_q.cpu().numpy()[0]
            param_q = param_q.cpu().numpy()[0]

        option_idx = np.argmax(action_q)
        param_q_for_option = param_q[option_idx]
        param_bin_idx = np.argmax(param_q_for_option)

        # Восстановить значение параметра
        option_spec = self.options[option_idx]
        if option_spec['has_params']:
            param_value = self.undiscretize_param(param_bin_idx, min_val=1.0, max_val=10.0)
        else:
            param_value = 0.0

        return option_idx, param_bin_idx, param_value

    def select_option_explore(self) -> Tuple[int, int, float]:
        """Выбрать случайную опцию И параметр"""
        option_idx = np.random.randint(0, len(self.options))
        param_bin_idx = np.random.randint(0, self.num_param_bins)

        option_spec = self.options[option_idx]
        if option_spec['has_params']:
            param_value = self.undiscretize_param(param_bin_idx, min_val=1.0, max_val=10.0)
        else:
            param_value = 0.0

        return option_idx, param_bin_idx, param_value

    def forward(self, game_state: 'GameState') -> Tuple['ActionOption', int]:
        """
        ✅ НОВОЕ: Выбрать действие ТОЛЬКО на основе game_state
        Полностью игнорирует выход ЭМ
        """
        features = self.build_input_features(game_state)

        if np.random.random() < self.epsilon:
            option_idx, param_bin_idx, param_value = self.select_option_explore()
        else:
            option_idx, param_bin_idx, param_value = self.select_option_greedy(features)

        self.last_option_idx = option_idx
        self.last_param_bin_idx = param_bin_idx

        option_spec = self.options[option_idx]
        option_name = option_spec['name']

        params = {}
        if option_spec['has_params']:
            for param_name in option_spec['param_specs']:
                params[param_name] = param_value

        action_option = ActionOption(name=option_name, params=params)

        return action_option, option_idx

    def add_experience(self, state_features: np.ndarray, option_idx: int, param_bin_idx: int,
                      payoff: float, next_state_features: np.ndarray, done: bool,
                      emotional_intensity: float = 0.0, em_action_name: str = ""):
        """
        ✅ ОБНОВЛЕНО: Добавить опыт с tracking ЭМ metrics для анализа

        Args:
            payoff: ВЫИГРЫШ из игры (это то, что максимизирует РМ!)
            emotional_intensity: для логирования и анализа (НЕ для обучения)
            em_action_name: для логирования и анализа (НЕ для обучения)
        """
        experience = {
            'state': state_features.astype(np.float32),
            'option': option_idx,
            'param_bin': param_bin_idx,
            'payoff': float(payoff),  # ✅ ВОТ ЧТО МАКСИМИЗИРУЕТ РМ!
            'next_state': next_state_features.astype(np.float32),
            'done': bool(done),
            # Информация для анализа (не влияет на обучение):
            'emotional_intensity': float(emotional_intensity),
            'em_action_name': str(em_action_name)
        }
        self.replay_buffer.append(experience)
        if len(self.replay_buffer) > 1000:
            self.replay_buffer.pop(0)

    def train_on_feedback(self, payoff: float, game_state: 'GameState',
                         next_game_state: Optional['GameState'] = None,
                         emotional_intensity: float = 0.0, em_action_name: str = ""):
        """
        ✅ ОБНОВЛЕНО: Обучение РМ на PAYOFF (выигрыш из игры)

        РМ игнорирует emotional_intensity - это для логирования
        """
        current_features = self.build_input_features(game_state)

        if next_game_state is not None:
            next_features = self.build_input_features(next_game_state)
        else:
            next_features = current_features

        option_idx = self.last_option_idx
        param_bin_idx = self.last_param_bin_idx

        # ✅ Добавляем PAYOFF, а не emotional_intensity!
        self.add_experience(
            state_features=current_features,
            option_idx=option_idx,
            param_bin_idx=param_bin_idx,
            payoff=payoff,  # ✅ ВЫИГРЫШ из игры
            next_state_features=next_features,
            done=False,
            emotional_intensity=emotional_intensity,  # Для анализа
            em_action_name=em_action_name  # Для анализа
        )

        if len(self.replay_buffer) >= 16:
            self.last_loss = self._train_batch(batch_size=min(32, len(self.replay_buffer) // 2))

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def _train_batch(self, batch_size: int):
        """Обучение на батче с PAYOFF максимизацией"""
        indices = np.random.choice(len(self.replay_buffer), batch_size, replace=False)
        batch = [self.replay_buffer[i] for i in indices]

        states = torch.FloatTensor(np.array([exp['state'] for exp in batch])).to(self.device)
        options = torch.LongTensor([exp['option'] for exp in batch]).to(self.device)
        param_bins = torch.LongTensor([exp['param_bin'] for exp in batch]).to(self.device)
        payoffs = torch.FloatTensor([exp['payoff'] for exp in batch]).to(self.device)  # ✅ PAYOFF!
        next_states = torch.FloatTensor(np.array([exp['next_state'] for exp in batch])).to(self.device)
        dones = torch.FloatTensor([1.0 - float(exp['done']) for exp in batch]).to(self.device)

        # Q-значения текущей сети
        action_q, param_q = self.q_network(states)

        action_q_for_options = action_q.gather(1, options.unsqueeze(1)).squeeze(1)

        batch_indices = torch.arange(batch_size, device=self.device)
        param_q_for_options = param_q[batch_indices, options, :]
        param_q_for_selected = param_q_for_options.gather(1, param_bins.unsqueeze(1)).squeeze(1)

        # Целевые Q-значения от TARGET СЕТИ
        with torch.no_grad():
            next_action_q, next_param_q = self.target_network(next_states)
            max_next_action_q = torch.max(next_action_q, dim=1)[0]
            best_next_options = torch.argmax(next_action_q, dim=1)
            next_param_q_for_best = next_param_q[batch_indices, best_next_options, :]
            max_next_param_q = torch.max(next_param_q_for_best, dim=1)[0]

        # ✅ BELLMAN с PAYOFF (то, что РМ максимизирует!)
        target_action_q = payoffs + (self.gamma * max_next_action_q * dones)
        target_param_q = payoffs + (self.gamma * max_next_param_q * dones)

        action_loss = self.criterion(action_q_for_options, target_action_q)
        param_loss = self.criterion(param_q_for_selected, target_param_q)

        total_loss = action_loss + param_loss

        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), max_norm=1.0)
        self.optimizer.step()

        self.update_counter += 1
        if self.update_counter % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())

        return total_loss.item()

# ============================================================================
# ОСНОВНОЙ АГЕНТ
# ============================================================================

class EmotionalRationalAgent:
    """
    Рациональный baseline-агент с сохранённым эмоциональным контуром.

    Важная семантика этого файла:
    1. Эмоциональный модуль НЕ участвует в выборе действия.
       Он вычисляется, логируется и обновляет внутренние переменные агента.
    2. Рациональный модуль выбирает только игровые действия и обучается только
       на payoff, полученном от игры.
    3. mood / wellbeing / fatigue / resources сохраняются и меняются для
       последующего сравнения с эмоционально-рациональным и эмоциональным
       агентами, но НЕ подаются во вход РМ и НЕ влияют на поведение.
    """

    def __init__(self, personality: PersonalityType = PersonalityType.NEUTRAL,
                 intensity: EmotionalIntensityType = EmotionalIntensityType.NEUTRAL,
                 game_actions: Optional[List[Dict[str, Any]]] = None,
                 log_level: int = LogLevel.NORMAL,
                 device: str = 'cpu'):

        self.personality = personality
        self.intensity = intensity
        self.device = device

        self.name = f"RationalAgent_{personality.value}"
        self.logger = AgentLogger(self.name, log_level=log_level)
        self.character_traits = CharacterTraits(personality, intensity)

        if not game_actions:
            game_actions = [
                {'name': 'cooperate', 'params': []},
                {'name': 'defect', 'params': []},
            ]

        self.action_space = ActionSpaceBuilder(game_actions)
        self.ots = CurrentStateEvaluation(self.logger, self.character_traits)
        self.emotional_module = EmotionalModule(self.action_space, self.logger, device=device)
        self.rational_module = RationalModule(self.action_space, self.logger, device=device)

        self.values = Values.create_by_personality(personality)
        self.agent_state = AgentState()
        self.state = self.agent_state
        self.game_state = GameState(available_actions=game_actions)

        self.episode_payoffs: List[float] = []
        self.episode_emotional_actions: List[Tuple[ActionOption, float]] = []
        self.episode_rational_choices: List[Tuple[ActionOption, int]] = []
        self.turn_counter = 0
        self.episode_counter = 0
        self.total_payoff = 0.0

        self._last_values_before_action: Optional[Values] = None
        self._last_state_before_action: Optional[AgentState] = None
        self._last_game_state_before_action: Optional[GameState] = None
        self._last_reaction_intensity: float = 0.0
        self._last_focus_value: Optional[ValueType] = None
        self._last_emotion_value: float = 0.0
        self._last_emotion_action: str = ""

    def update_game_state(self, game_state: GameState):
        """Обновить игровое состояние агента снаружи, как это делает main.py."""
        self.game_state = self._copy_game_state(game_state)

    def _copy_game_state(self, game_state: GameState) -> GameState:
        """Безопасно скопировать GameState даже если он пришёл из другого модуля."""
        if hasattr(game_state, 'copy'):
            try:
                return game_state.copy()
            except Exception:
                pass
        return GameState(
            game_parameters=dict(getattr(game_state, 'game_parameters', {}) or {}),
            available_actions=[dict(a) for a in getattr(game_state, 'available_actions', []) or []]
        )

    @staticmethod
    def _normalize_game_value(value: float) -> float:
        """Привести игровые показатели к шкале 0..100."""
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 50.0
        if 0.0 <= value <= 1.0:
            value *= 100.0
        return float(np.clip(value, 0.0, 100.0))

    def calculate_overall_state(self) -> float:
        """Рассчитать общее состояние."""
        return self.agent_state.calculate_overall_state()

    def update_wellbeing(self):
        """
        Обновить wellbeing из системы ценностей.

        wellbeing отражает взвешенную близость текущих значений к желаемым.
        Это нужно для логирования и сравнения, но результат НЕ передаётся в
        rational_module.forward().
        """
        weighted_satisfaction = 0.0
        total_weight = 0.0
        for vtype in ValueType:
            current = float(self.values.current_values.get(vtype, 50.0))
            desired = max(float(self.values.desired_values.get(vtype, 100.0)), 1e-6)
            priority = max(float(self.values.value_priorities.get(vtype, 0.25)), 0.0)
            closeness = 1.0 - abs(desired - current) / desired
            closeness = float(np.clip(closeness, 0.0, 1.0))
            weighted_satisfaction += priority * closeness
            total_weight += priority
        satisfaction = 0.5 if total_weight <= 0 else weighted_satisfaction / total_weight
        self.agent_state.wellbeing = float(np.clip(2.0 * satisfaction - 1.0, -1.0, 1.0))

    def apply_mood_update_from_ots(self, reaction_intensity: float):
        """Обновить настроение по эмоциональной реакции ОТС."""
        mood_delta = float(reaction_intensity) / 10.0
        self.agent_state.mood = float(np.clip(self.agent_state.mood + mood_delta, -0.5, 0.5))

    def update_values_from_game_result(self, game_result: GameResult):
        """
        Перевести результат игры в ценности агента.

        Это нужно, чтобы у рационального baseline сохранялись value/wellbeing/mood
        traces для сравнения с другими агентами. Эти значения не используются РМ.
        """
        game_state = dict(getattr(game_result, 'game_state', {}) or {})
        payoff = float(getattr(game_result, 'payoff', 0.0))

        current_payoff_value = self.values.current_values.get(ValueType.PAYOFF, 50.0)
        self.values.update_value(ValueType.PAYOFF, current_payoff_value + payoff)

        relationship_keys = [
            'cooperation_level', 'agreement_level', 'trust_level',
            'mutual_satisfaction', 'relationships', 'relationship_level'
        ]
        for key in relationship_keys:
            if key in game_state:
                self.values.update_value(ValueType.RELATIONSHIPS, self._normalize_game_value(game_state[key]))
                break

        equality_keys = [
            'equality_level', 'fairness_level', 'inequality_aversion',
            'preference_difference', 'fairness', 'equality'
        ]
        for key in equality_keys:
            if key in game_state:
                self.values.update_value(ValueType.EQUALITY, self._normalize_game_value(game_state[key]))
                break

        if 'security_level' in game_state:
            self.values.update_value(ValueType.SECURITY, self._normalize_game_value(game_state['security_level']))
        elif 'risk' in game_state:
            risk = self._normalize_game_value(game_state['risk'])
            self.values.update_value(ValueType.SECURITY, 100.0 - risk)
        elif 'trust_level' in game_state:
            self.values.update_value(ValueType.SECURITY, self._normalize_game_value(game_state['trust_level']))

    def update_agent_state_after_game(self, reaction_intensity: float, emotional_intensity: float):
        """
        Обновить внутреннее состояние после результата игры.

        Важно: этот блок сохраняет динамику состояния, но не влияет на действие РМ.
        """
        self.apply_mood_update_from_ots(reaction_intensity)
        self.update_wellbeing()
        self.agent_state.update_fatigue(emotional_intensity)
        if abs(emotional_intensity) > 0.75 or abs(self.agent_state.mood) > 0.4:
            self.agent_state.consume_resources(0.02)
        self.agent_state.recover_resources(recovery_rate=0.05)
        self.agent_state.apply_fatigue_decay()
        self.state = self.agent_state

    def make_action(self, game_state: GameState) -> Tuple[ActionOption, ActionType, Dict[str, Any]]:
        """
        Выбрать действие.

        1. сохранить контекст до действия;
        2. посчитать ОТС и ЭМ для логирования / будущего состояния;
        3. НЕ использовать ЭМ в выборе;
        4. вызвать РМ только на game_state;
        5. вернуть действие РМ.
        """
        self.turn_counter += 1
        self.update_game_state(game_state)

        self._last_values_before_action = self.values.copy()
        self._last_state_before_action = copy.deepcopy(self.agent_state)
        self._last_game_state_before_action = self._copy_game_state(self.game_state)

        self.logger.log_turn_start(self.turn_counter)
        self.logger.log_game_state(self.game_state)
        self.logger.log_agent_state(self.agent_state)
        self.logger.log_values(self.values)

        reaction_intensity, max_focus_value_type = self.ots.evaluate_values_changes(
            self.values, self.agent_state
        )
        self._last_reaction_intensity = float(reaction_intensity)
        self._last_focus_value = max_focus_value_type
        self.logger.log_ots_evaluation(reaction_intensity, max_focus_value_type.name)

        em_action, em_intensity = self.emotional_module.forward(self.values, self.agent_state)
        self._last_emotion_value = float(em_intensity)
        self._last_emotion_action = str(em_action)
        self.logger.log_emotional_response(str(em_action), em_intensity)

        rm_action, rm_option_idx = self.rational_module.forward(self.game_state)
        self.logger.log_rational_decision(str(rm_action), "GAME_ACTION", override=False)
        self.logger.log_action_execution(str(rm_action), "GAME_ACTION", rm_action.params)

        self.episode_emotional_actions.append((em_action, float(em_intensity)))
        self.episode_rational_choices.append((rm_action, rm_option_idx))

        info = {
            'turn': self.turn_counter,
            'action': str(rm_action),
            'action_type': ActionType.GAME_ACTION.name,
            'em_action': str(em_action),
            'em_intensity': float(em_intensity),
            'emotional_intensity': float(em_intensity),
            'reaction_intensity': float(reaction_intensity),
            'rm_action': str(rm_action),
            'mood': float(self.agent_state.mood),
            'wellbeing': float(self.agent_state.wellbeing),
            'fatigue': float(self.agent_state.fatigue),
            'resources': float(self.agent_state.resources),
            'overall_state': float(self.calculate_overall_state()),
        }
        return rm_action, ActionType.GAME_ACTION, info

    def update_from_game(self, game_result: GameResult):
        """
        Обновить агента после результата игры.

        - РМ обучается только на payoff.
        - ЭМ обучается на affective feedback от ОТС.
        - Ценности, mood, wellbeing, fatigue обновляются для анализа и графиков,
          но НЕ влияют на будущий выбор РМ.
        """
        payoff = float(getattr(game_result, 'payoff', 0.0))
        self.episode_payoffs.append(payoff)
        self.total_payoff += payoff

        prev_game_state = self._last_game_state_before_action or self._copy_game_state(self.game_state)
        prev_values = self._last_values_before_action or self.values.copy()
        prev_state = self._last_state_before_action or copy.deepcopy(self.agent_state)

        if self.episode_emotional_actions:
            em_action, em_intensity = self.episode_emotional_actions[-1]
        else:
            em_action, em_intensity = ActionOption("unknown"), 0.0

        self.values.update_previous_values()
        self.game_state.game_parameters = dict(getattr(game_result, 'game_state', {}) or {})
        self.update_values_from_game_result(game_result)

        reaction_intensity, focus_value = self.ots.evaluate_values_changes(self.values, self.agent_state)
        self._last_reaction_intensity = float(reaction_intensity)
        self._last_focus_value = focus_value

        self.update_agent_state_after_game(
            reaction_intensity=reaction_intensity,
            emotional_intensity=float(em_intensity)
        )

        next_game_state = self._copy_game_state(self.game_state)

        self.rational_module.train_on_feedback(
            payoff=payoff,
            game_state=prev_game_state,
            next_game_state=next_game_state,
            emotional_intensity=float(em_intensity),
            em_action_name=str(getattr(em_action, 'name', em_action))
        )

        self.emotional_module.train_on_feedback(
            reaction_intensity=reaction_intensity,
            values=prev_values,
            state=prev_state,
            game_state=prev_game_state,
            emotional_action=em_action,
            emotional_intensity=float(em_intensity),
            next_values=self.values,
            next_state=self.agent_state
        )

        self.logger.log_learning(
            em_buffer_size=len(self.emotional_module.replay_buffer),
            rm_buffer_size=len(self.rational_module.replay_buffer),
            em_loss=self.emotional_module.last_loss,
            rm_loss=self.rational_module.last_loss,
            em_epsilon=self.emotional_module.epsilon,
            rm_epsilon=self.rational_module.epsilon
        )

        overall_state = self.calculate_overall_state()
        self.logger.log_recovery(self.agent_state.fatigue, self.agent_state.mood, self.agent_state.resources)
        self.logger.log_turn_summary(
            self.turn_counter,
            overall_state,
            str(getattr(game_result, 'action', 'unknown')),
            payoff
        )

    def reset_episode(self):
        """Сбросить состояние для нового эпизода, сохранив обученные DQN-модули."""
        self.episode_payoffs = []
        self.episode_emotional_actions = []
        self.episode_rational_choices = []
        self.turn_counter = 0
        self.episode_counter += 1
        self.total_payoff = 0.0
        self.agent_state.fatigue *= 0.5
        self.agent_state.mood *= 0.5
        self.agent_state.recover_resources(recovery_rate=0.2)
        self.agent_state.reset_refocus_count()
        self.state = self.agent_state
        self._last_values_before_action = None
        self._last_state_before_action = None
        self._last_game_state_before_action = None
        self._last_reaction_intensity = 0.0
        self._last_focus_value = None
        self._last_emotion_value = 0.0
        self._last_emotion_action = ""

    def get_episode_stats(self) -> Dict[str, float]:
        """Получить статистику эпизода."""
        if not self.episode_payoffs:
            return {
                'episode': self.episode_counter,
                'total_payoff': 0.0,
                'avg_payoff': 0.0,
                'max_payoff': 0.0,
                'min_payoff': 0.0,
                'num_turns': 0,
                'final_mood': float(self.agent_state.mood),
                'final_wellbeing': float(self.agent_state.wellbeing),
                'final_fatigue': float(self.agent_state.fatigue),
                'final_resources': float(self.agent_state.resources),
                'final_overall_state': float(self.calculate_overall_state()),
            }
        total = float(sum(self.episode_payoffs))
        avg = total / len(self.episode_payoffs)
        max_p = float(max(self.episode_payoffs))
        min_p = float(min(self.episode_payoffs))
        return {
            'episode': self.episode_counter,
            'total_payoff': total,
            'avg_payoff': avg,
            'max_payoff': max_p,
            'min_payoff': min_p,
            'num_turns': len(self.episode_payoffs),
            'final_mood': float(self.agent_state.mood),
            'final_wellbeing': float(self.agent_state.wellbeing),
            'final_fatigue': float(self.agent_state.fatigue),
            'final_resources': float(self.agent_state.resources),
            'final_overall_state': float(self.calculate_overall_state()),
        }

# Backward-compatible aliases for main.py and older wrappers.
Agent = EmotionalRationalAgent
RationalAgent = EmotionalRationalAgent

# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================================================

if __name__ == "__main__":
    # Определить игровые действия
    game_actions = [
        {'name': 'cooperate', 'params': ['strength']},
        {'name': 'defect', 'params': ['aggressiveness']},
        {'name': 'neutral', 'params': []}
    ]

    # Создать агента
    agent = EmotionalRationalAgent(
        personality=PersonalityType.NEUTRAL,
        intensity=EmotionalIntensityType.NEUTRAL,
        game_actions=game_actions,
        log_level=LogLevel.NORMAL
    )

    # Симуляция простой игры
    print("🎮 СИМУЛЯЦИЯ ИГРЫ")
    print("=" * 80)

    for episode in range(3):
        print(f"\n📊 ЭПИЗОД {episode + 1}")
        agent.reset_episode()

        for turn in range(5):
            # Инициализировать игровое состояние
            agent.game_state = GameState(
                game_parameters={'opponent_strength': 0.5 + turn * 0.1, 'round': turn},
                available_actions=game_actions
            )

            # Агент выбирает действие
            action, action_type, info = agent.make_action(agent.game_state)

            # Симуляция результата игры (random payoff)
            payoff = np.random.uniform(-1.0, 2.0)

            game_result = GameResult(
                action=action.name,
                payoff=payoff,
                game_state={'opponent_strength': 0.5 + turn * 0.1}
            )

            # Обновить состояние от результата
            agent.update_from_game(game_result)

        # Итоги эпизода
        stats = agent.get_episode_stats()
        print(f"\n📈 Итоги: Выигрыш={stats['total_payoff']:.2f} | "
              f"Средний={stats['avg_payoff']:.2f} | Макс={stats['max_payoff']:.2f}")

    print("\n" + "=" * 80)
    print("✅ Симуляция завершена!")
    print(f"Всего эпизодов: {agent.episode_counter}")
    print(f"Всего ходов: {agent.turn_counter}")
