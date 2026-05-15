# ============================================================================
# АГЕНТ С ФИКСИРОВАННОЙ СТРАТЕГИЕЙ И ЭМОЦИОНАЛЬНЫМ МОДУЛЕМ
# ============================================================================

# Версия с поддержкой трех фиксированных стратегий:
# 1. ALWAYS_COOPERATE - всегда сотрудничать
# 2. ALWAYS_DEFECT - всегда предавать
# 3. TIT_FOR_TAT - копировать действие оппонента

# Все эмоциональные компоненты СОХРАНЕНЫ И АКТИВНЫ:
# - Модуль оценки текущего состояния (ОТС)
# - Эмоциональный модуль DQN
# - Параметры состояния (настроение, усталость, ресурсы и т.д.)
# - Черты характера и приоритеты ценностей

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
    SILENT = 50 # Никаких логов
    MINIMAL = 40 # Только самое важное (ХОД, ИТОГ, ОШИБКИ)
    NORMAL = 30 # Стандартные логи (рекомендуется)
    VERBOSE = 20 # Расширенные логи (обучение, рефлексия)
    DEBUG = 10 # Все логи (для отладки)

# ============================================================================
# ПЕРЕЧИСЛЕНИЯ (ENUMS)
# ============================================================================

class FixedStrategy(Enum):
    """✅ НОВОЕ: Типы фиксированных стратегий"""
    ALWAYS_COOPERATE = "always_cooperate"
    ALWAYS_DEFECT = "always_defect"
    TIT_FOR_TAT = "tit_for_tat"

class ActionType(Enum):
    """Типы действий агента"""
    GAME_ACTION = "game_action"
    REFOCUS = "refocus"
    REFLECTION = "reflection"

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
# БАЗОВЫЕ КЛАССЫ ДАННЫХ
# ============================================================================

@dataclass
class GameResult:
    """Результат игрового действия"""
    action: str
    payoff: float
    game_state: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь"""
        return {
            'action': self.action,
            'payoff': self.payoff,
            'game_state': self.game_state,
        }

@dataclass
class GameState:
    """Состояние игры"""
    game_parameters: Dict[str, float] = field(default_factory=dict)
    available_actions: List[Dict[str, Any]] = field(default_factory=list)
    opponent_last_action: Optional[str] = None  # ✅ НОВОЕ: Для TIT-FOR-TAT

    def copy(self):
        return GameState(
            game_parameters=self.game_parameters.copy(),
            available_actions=[a.copy() for a in self.available_actions],
            opponent_last_action=self.opponent_last_action
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
        """Создать ценности в зависимости от типа личности"""
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
        else: # NEUTRAL
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
    action_history: List[str] = field(default_factory=list)  # ✅ НОВОЕ: История действий

    def increment_refocus_count(self):
        """Увеличить счетчик рефокусов"""
        self.refocus_count += 1
        self.total_refocus_count += 1

    def reset_refocus_count(self):
        """Сбросить счетчик рефокусов"""
        self.refocus_count = 0

    def calculate_overall_state(self) -> float:
        """Рассчитать общее состояние по формуле архитектуры"""
        # Формула: Общее состояние = благополучие + настроение - усталость
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

    def record_action(self, action: str):
        """✅ НОВОЕ: Записать действие в историю"""
        self.action_history.append(action)
        if len(self.action_history) > 100:  # Хранить последние 100 действий
            self.action_history.pop(0)

# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================

class AgentLogger:
    """Специализированный логгер для агента"""

    def __init__(self, agent_name: str, log_level: int = LogLevel.NORMAL):
        self.agent_name = agent_name
        self.turn = 0
        self.log_level = log_level
        self.log_entries = []

        self.logger = logging.getLogger(f"Agent_{agent_name}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []

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
        for vtype_name, priority in sorted_priorities[:3]:
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

    def log_rational_decision(self, action: str, strategy: str = ""):
        """✅ НОВОЕ: Логирование решения с фиксированной стратегией"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug(f"🤔 РАЦИОНАЛЬНЫЙ МОДУЛЬ (РМ - ФИКСИРОВАННАЯ СТРАТЕГИЯ):")
        self.logger.debug(f" • Действие: {action}")
        self.logger.debug(f" • Стратегия: {strategy}")
        self.logger.debug("")

    def log_fixed_strategy_info(self, strategy: FixedStrategy):
        """✅ НОВОЕ: Логирование информации о фиксированной стратегии"""
        if not self._should_log(LogLevel.NORMAL):
            return
        strategy_names = {
            FixedStrategy.ALWAYS_COOPERATE: "ВСЕГДА СОТРУДНИЧАТЬ ☺️",
            FixedStrategy.ALWAYS_DEFECT: "ВСЕГДА ПРЕДАВАТЬ 😈",
            FixedStrategy.TIT_FOR_TAT: "ОКО ЗА ОКО 🔄"
        }
        self.logger.info(f"📋 СТРАТЕГИЯ АГЕНТА: {strategy_names.get(strategy, 'НЕИЗВЕСТНАЯ')}")
        self.logger.info("")

    def log_action_execution(self, action: str, strategy: str = ""):
        """Логирование выполнения действия"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        strategy_str = f" ({strategy})" if strategy else ""
        self.logger.debug(f"⚙️ ДЕЙСТВИЕ: {action}{strategy_str}")
        self.logger.debug("")

    def log_learning(self, em_buffer_size: int, em_loss: Optional[float] = None,
                    em_epsilon: Optional[float] = None):
        """✅ НОВОЕ: Логирование обучения (только ЭМ)"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("📚 ОБУЧЕНИЕ МОДУЛЕЙ:")
        if em_buffer_size >= 16:
            loss_str = f"loss: {em_loss:.4f}" if em_loss is not None else "обучение"
            epsilon_str = f"ε: {em_epsilon:.3f}" if em_epsilon is not None else ""
            self.logger.debug(f" • ЭМ: ✓ {loss_str} {epsilon_str} (буфер: {em_buffer_size})")
        else:
            self.logger.debug(f" • ЭМ: ⏳ {em_buffer_size}/16 (ожидание)")
        self.logger.debug(" • РМ: ⚫ ФИКСИРОВАННАЯ СТРАТЕГИЯ (обучение не требуется)")
        self.logger.debug("")

    def log_turn_summary(self, turn: int, overall_state: float, action: str):
        """Логирование итога хода"""
        if not self._should_log(LogLevel.NORMAL):
            return
        separator = "=" * 80
        self.logger.info(f"📋 ХОД {turn} ИТОГ:")
        self.logger.info(f" • Действие: {action}")
        self.logger.info(f" • Состояние: {overall_state:+.3f}")
        self.logger.info(f"{separator}\n")

# ============================================================================
# ЧЕРТЫ ХАРАКТЕРА
# ============================================================================

class CharacterTraits:
    """Черты характера с chunk_1 и chunk_2"""

    def __init__(self, personality: PersonalityType, intensity: EmotionalIntensityType):
        self.personality = personality
        self.intensity = intensity
        self._initialize_chunks()

    def _initialize_chunks(self):
        """Инициализировать chunk_1 и chunk_2"""
        # chunk_1: пороговое значение (0.3 до 1.0)
        if self.personality == PersonalityType.OPTIMISTIC:
            self.chunk_1 = 0.3
        elif self.personality == PersonalityType.PESSIMISTIC:
            self.chunk_1 = 0.7
        else:
            self.chunk_1 = 0.5

        # chunk_2: коэффициент интенсивности (0.5 до 1.5)
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
# ОЦЕНКА ТЕКУЩЕГО СОСТОЯНИЯ (ОТС)
# ============================================================================

class CurrentStateEvaluation:
    """Модуль оценки текущего состояния"""

    def __init__(self, logger: AgentLogger, character_traits: CharacterTraits):
        self.logger = logger
        self.character_traits = character_traits

    def calculate_threshold(self, state: AgentState) -> float:
        """Рассчитать пороговое значение"""
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
        """Оценить изменения ценностей"""
        max_focus = 0.0
        reaction_intensity = 0.0
        max_focus_value_type = ValueType.SECURITY
        threshold = self.calculate_threshold(state)

        # Если есть фокус - оцениваем только её
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
            # БЕЗ ФОКУСА - стандартное вычисление
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

# ============================================================================
# DQN СЕТЬ
# ============================================================================

class DQNNetwork(nn.Module):
    """Простая DQN сеть"""

    def __init__(self, input_size: int, num_actions: int, hidden_size: int = 128):
        super(DQNNetwork, self).__init__()
        self.num_actions = num_actions

        self.encoder = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU()
        )

        self.action_head = nn.Linear(hidden_size, num_actions)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Прямой проход"""
        features = self.encoder(x)
        action_q = self.action_head(features)
        return action_q

# ============================================================================
# ДЕЙСТВИЯ
# ============================================================================

@dataclass
class ActionOption:
    """Опция действия"""
    name: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        if self.params:
            params_str = ", ".join([f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                                   for k, v in self.params.items()])
            return f"{self.name}({params_str})"
        return self.name

# ============================================================================
# ЭМОЦИОНАЛЬНЫЙ МОДУЛЬ (АКТИВНЫЙ)
# ============================================================================

class EmotionalModule:
    """✅ Эмоциональный модуль с DQN (ОСТАЕТСЯ АКТИВНЫМ)"""

    def __init__(self, available_actions: List[str], logger: AgentLogger, device='cpu'):
        self.available_actions = available_actions
        self.logger = logger
        self.device = device
        self.replay_buffer = []

        num_actions = len(available_actions)

        self.q_network = DQNNetwork(
            input_size=16,
            num_actions=num_actions,
            hidden_size=128
        ).to(device)

        self.target_network = DQNNetwork(
            input_size=16,
            num_actions=num_actions,
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

    def build_input_features(self, values: Values, state: AgentState) -> np.ndarray:
        """Построить входные признаки"""
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

    def select_action_greedy(self, state_features: np.ndarray) -> Tuple[str, int]:
        """Жадный выбор действия"""
        features_tensor = torch.FloatTensor(state_features).unsqueeze(0).to(self.device)
        with torch.no_grad():
            action_q = self.q_network(features_tensor)
            action_q = action_q.cpu().numpy()[0]
            action_idx = np.argmax(action_q)
            action_name = self.available_actions[action_idx]
        return action_name, action_idx

    def select_action_explore(self) -> Tuple[str, int]:
        """Случайный выбор действия"""
        action_idx = np.random.randint(0, len(self.available_actions))
        action_name = self.available_actions[action_idx]
        return action_name, action_idx

    def select_action(self, state_features: np.ndarray, training: bool = True) -> Tuple[str, int]:
        """Epsilon-greedy выбор"""
        if training and np.random.random() < self.epsilon:
            return self.select_action_explore()
        else:
            return self.select_action_greedy(state_features)

    def forward(self, values: Values, state: AgentState) -> Tuple[ActionOption, float]:
        """Выбрать действие и интенсивность"""
        features = self.build_input_features(values, state)
        action_name, action_idx = self.select_action(features, training=True)
        self.last_action_idx = action_idx

        action_option = ActionOption(name=action_name, params={})

        # Эмоциональная интенсивность
        emotional_intensity = np.clip(state.mood + np.random.randn() * 0.3, -1.5, 1.5)

        return action_option, emotional_intensity

    def add_experience(self, state_features: np.ndarray, action_idx: int,
                      reward: float, next_state_features: np.ndarray, done: bool):
        """Добавить опыт"""
        experience = {
            'state': state_features.astype(np.float32),
            'action': action_idx,
            'reward': float(reward),
            'next_state': next_state_features.astype(np.float32),
            'done': bool(done)
        }
        self.replay_buffer.append(experience)
        if len(self.replay_buffer) > 1000:
            self.replay_buffer.pop(0)

    def train_on_feedback(self, reaction_intensity: float, values: Values,
                         state: AgentState, next_values: Optional[Values] = None,
                         next_state: Optional[AgentState] = None):
        """Обучить на фидбеке"""
        current_features = self.build_input_features(values, state)
        if next_state is not None and next_values is not None:
            next_features = self.build_input_features(next_values, next_state)
        else:
            next_features = current_features

        action_idx = self.last_action_idx
        self.add_experience(
            state_features=current_features,
            action_idx=action_idx,
            reward=reaction_intensity,
            next_state_features=next_features,
            done=False
        )

        if len(self.replay_buffer) >= 16:
            self.last_loss = self._train_batch(batch_size=min(32, len(self.replay_buffer) // 2))

    def _train_batch(self, batch_size: int) -> float:
        """Обучить на батче"""
        batch_indices = np.random.choice(len(self.replay_buffer), batch_size, replace=False)
        batch = [self.replay_buffer[i] for i in batch_indices]

        states = torch.FloatTensor(np.array([exp['state'] for exp in batch])).to(self.device)
        actions = torch.LongTensor([exp['action'] for exp in batch]).to(self.device)
        rewards = torch.FloatTensor([exp['reward'] for exp in batch]).to(self.device)
        next_states = torch.FloatTensor(np.array([exp['next_state'] for exp in batch])).to(self.device)
        dones = torch.FloatTensor([exp['done'] for exp in batch]).to(self.device)

        with torch.no_grad():
            next_q_values = self.target_network(next_states).max(1)[0]
            target_q = rewards + (1 - dones) * self.gamma * next_q_values

        current_q = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        loss = self.criterion(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.update_counter += 1
        if self.update_counter % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        return float(loss.item())

# ============================================================================
# РАЦИОНАЛЬНЫЙ МОДУЛЬ С ФИКСИРОВАННОЙ СТРАТЕГИЕЙ (НОВЫЙ!)
# ============================================================================

class FixedStrategyRationalModule:
    """✅ НОВОЕ: Рациональный модуль с фиксированной стратегией вместо DQN"""

    def __init__(self, strategy: FixedStrategy, available_actions: List[str],
                 logger: AgentLogger):
        """
        Args:
            strategy: FixedStrategy.ALWAYS_COOPERATE, ALWAYS_DEFECT или TIT_FOR_TAT
            available_actions: список доступных действий (например, ['cooperate', 'defect'])
            logger: логгер
        """
        self.strategy = strategy
        self.available_actions = available_actions
        self.logger = logger

    def forward(self, values: Values, state: AgentState,
               emotional_action: ActionOption, emotional_intensity: float,
               game_state: GameState) -> Tuple[ActionOption, ActionType]:
        """
        Выбрать действие согласно фиксированной стратегии

        ✅ СОХРАНЯЕМ ВСЕ ЭМОЦИОНАЛЬНЫЕ КОМПОНЕНТЫ, но действие выбираем по стратегии
        """

        if self.strategy == FixedStrategy.ALWAYS_COOPERATE:
            return self._always_cooperate()
        elif self.strategy == FixedStrategy.ALWAYS_DEFECT:
            return self._always_defect()
        elif self.strategy == FixedStrategy.TIT_FOR_TAT:
            return self._tit_for_tat(game_state)
        else:
            # Fallback
            return ActionOption(name=self.available_actions[0], params={}), ActionType.GAME_ACTION

    def _always_cooperate(self) -> Tuple[ActionOption, ActionType]:
        """Всегда сотрудничать"""
        action = ActionOption(name='cooperate', params={})
        self.logger.log_rational_decision(str(action), "ALWAYS_COOPERATE")
        return action, ActionType.GAME_ACTION

    def _always_defect(self) -> Tuple[ActionOption, ActionType]:
        """Всегда предавать"""
        action = ActionOption(name='defect', params={})
        self.logger.log_rational_decision(str(action), "ALWAYS_DEFECT")
        return action, ActionType.GAME_ACTION

    def _tit_for_tat(self, game_state: GameState) -> Tuple[ActionOption, ActionType]:
        """Копировать действие оппонента (Oko za oko)"""
        if game_state.opponent_last_action is None:
            # Первый ход - сотрудничаем
            action = ActionOption(name='cooperate', params={})
            self.logger.log_rational_decision(str(action), "TIT_FOR_TAT (first move)")
        elif game_state.opponent_last_action == 'cooperate':
            # Оппонент сотрудничал - сотрудничаем
            action = ActionOption(name='cooperate', params={})
            self.logger.log_rational_decision(str(action), "TIT_FOR_TAT (opponent cooperated)")
        else:
            # Оппонент предал - предаем
            action = ActionOption(name='defect', params={})
            self.logger.log_rational_decision(str(action), "TIT_FOR_TAT (opponent defected)")

        return action, ActionType.GAME_ACTION

# ============================================================================
# ИГРОВОЙ АДАПТЕР
# ============================================================================

class GameAdapter:
    """Адаптер между агентом и игрой"""

    def __init__(self, game_state: GameState, logger: AgentLogger):
        self.game_state = game_state
        self.logger = logger

    def translate_game_state_to_values(self, game_result: GameResult, values: Values):
        """Перевести результат игры в ценности агента"""
        # PAYOFF
        payoff_change = game_result.payoff
        new_payoff = values.current_values.get(ValueType.PAYOFF, 50.0) + payoff_change
        values.update_value(ValueType.PAYOFF, new_payoff)

        # SECURITY
        if 'risk' in game_result.game_state:
            security = (1.0 - game_result.game_state['risk']) * 100.0
            values.update_value(ValueType.SECURITY, security)

        # RELATIONSHIPS
        if 'cooperation_level' in game_result.game_state:
            relationships = game_result.game_state['cooperation_level'] * 100.0
            values.update_value(ValueType.RELATIONSHIPS, relationships)

        # EQUALITY
        if 'trust' in game_result.game_state:
            equality = game_result.game_state['trust'] * 100.0
            values.update_value(ValueType.EQUALITY, equality)

# ============================================================================
# ГЛАВНЫЙ КЛАСС АГЕНТА
# ============================================================================

class Agent:
    """
    ✅ НОВОЕ: Агент с фиксированной рациональной стратегией
    и активным эмоциональным модулем

    Все эмоциональные компоненты СОХРАНЕНЫ И ФУНКЦИОНАЛЬНЫ:
    - Модуль оценки текущего состояния (ОТС)
    - Эмоциональный модуль DQN (обучаемый)
    - Параметры состояния (настроение, усталость, ресурсы, благополучие)
    - Черты характера и приоритеты ценностей

    Рациональный модуль ЗАМЕНЕН на фиксированную стратегию:
    - ALWAYS_COOPERATE - всегда сотрудничать
    - ALWAYS_DEFECT - всегда предавать
    - TIT_FOR_TAT - копировать действие оппонента
    """

    def __init__(self, name: str, personality: PersonalityType,
                 emotional_intensity: EmotionalIntensityType,
                 strategy: FixedStrategy,  # ✅ НОВОЕ: параметр стратегии
                 log_level: int = LogLevel.NORMAL,
                 game_actions: Optional[List[str]] = None,
                 device: str = 'cpu'):
        """
        Args:
            name: имя агента
            personality: тип личности
            emotional_intensity: интенсивность эмоций
            strategy: фиксированная стратегия (ALWAYS_COOPERATE, ALWAYS_DEFECT, TIT_FOR_TAT)
            log_level: уровень логирования
            game_actions: список доступных действий в игре
            device: 'cpu' или 'cuda'
        """
        self.name = name
        self.personality = personality
        self.emotional_intensity = emotional_intensity
        self.strategy = strategy  # ✅ НОВОЕ: сохраняем стратегию
        self.device = device

        # Логирование
        self.logger = AgentLogger(name, log_level)
        self.logger.log_fixed_strategy_info(strategy)

        # Черты характера
        self.character_traits = CharacterTraits(personality, emotional_intensity)

        # Ценности
        self.values = Values.create_by_personality(personality)

        # Состояние
        self.state = AgentState()

        # Игровое состояние
        if game_actions is None:
            game_actions = ['cooperate', 'defect']

        self.game_state = GameState(
            game_parameters={'cooperation': 0.5, 'trust': 0.5, 'risk': 0.3},
            available_actions=[{'name': a, 'params': []} for a in game_actions],
            opponent_last_action=None
        )

        # Модули
        self.ots = CurrentStateEvaluation(self.logger, self.character_traits)

        # ✅ ЭМОЦИОНАЛЬНЫЙ МОДУЛЬ ОСТАЕТСЯ АКТИВНЫМ
        self.emotional_module = EmotionalModule(game_actions, self.logger, device=device)

        # ✅ РАЦИОНАЛЬНЫЙ МОДУЛЬ ЗАМЕНЕН НА ФИКСИРОВАННУЮ СТРАТЕГИЮ
        self.rational_module = FixedStrategyRationalModule(
            strategy=strategy,
            available_actions=game_actions,
            logger=self.logger
        )

        # Игровой адаптер
        self.game_adapter = GameAdapter(self.game_state, self.logger)

        # Счетчики
        self._turn_count = 0

    def update_game_state(self, game_state: GameState):
        """Обновить состояние игры, сохраняя последнюю реакцию оппонента для TIT_FOR_TAT"""
        previous_opponent_action = getattr(self.game_state, 'opponent_last_action', None)
        self.game_state = game_state

        if getattr(self.game_state, 'opponent_last_action', None) is None:
            self.game_state.opponent_last_action = previous_opponent_action

    def _normalize_action_name(self, action_name: Optional[str]) -> Optional[str]:
        """Нормализовать имя действия для сопоставления между играми."""
        if action_name is None:
            return None

        normalized = str(action_name).strip().lower()
        if '(' in normalized:
            normalized = normalized.split('(', 1)[0].strip()

        if 'cooperate' in normalized:
            return 'cooperate'
        if 'defect' in normalized:
            return 'defect'
        if 'opera' in normalized:
            return 'opera'
        if 'fight' in normalized:
            return 'fight'
        if 'accept' in normalized:
            return 'accept'
        if 'reject' in normalized:
            return 'reject'
        return normalized

    def _infer_opponent_last_action(self, own_action: Optional[str], game_result: GameResult) -> Optional[str]:
        """Восстановить последнее действие оппонента по своему действию и наблюдаемому результату.

        Это нужно потому, что основной цикл в main.py передает агенту только его собственный
        action и payoff. Для игр с однозначным восстановлением действия оппонента из пары
        (собственное действие, payoff) мы сохраняем это действие в self.game_state.opponent_last_action,
        чтобы стратегия TIT_FOR_TAT корректно работала на следующем ходе.
        """
        own_action_normalized = self._normalize_action_name(own_action)
        payoff = float(game_result.payoff)
        state_keys = set(game_result.game_state.keys()) if isinstance(game_result.game_state, dict) else set()

        # Iterated Prisoner's Dilemma
        if {'cooperation_level', 'security_level'} & state_keys:
            if own_action_normalized == 'cooperate':
                if np.isclose(payoff, 3.0):
                    return 'cooperate'
                if np.isclose(payoff, 0.0):
                    return 'defect'
            elif own_action_normalized == 'defect':
                if np.isclose(payoff, 5.0):
                    return 'cooperate'
                if np.isclose(payoff, 1.0):
                    return 'defect'

        # Battle of the Sexes
        if {'agreement_level', 'mutual_satisfaction'} & state_keys:
            if own_action_normalized == 'opera':
                if np.isclose(payoff, 3.0):
                    return 'opera'
                if np.isclose(payoff, 0.0):
                    return 'fight'
            elif own_action_normalized == 'fight':
                if np.isclose(payoff, 2.0):
                    return 'fight'
                if np.isclose(payoff, 0.0):
                    return 'opera'

        # Ultimatum Game: однозначно восстановить предложение/ответ оппонента по payoff нельзя.
        return None

    def update_from_game(self, game_result: GameResult):
        """Обновить ценности из результата игры и сохранить последнее действие оппонента."""
        self.values.update_previous_values()
        self.game_adapter.translate_game_state_to_values(game_result, self.values)

        own_last_action = self.state.action_history[-1] if self.state.action_history else None
        inferred_opponent_action = self._infer_opponent_last_action(own_last_action, game_result)
        if inferred_opponent_action is not None:
            self.game_state.opponent_last_action = inferred_opponent_action

    def update_wellbeing(self):
        """Обновить благополучие на основе ценностей"""
        total = 0.0
        for vtype in ValueType:
            current = self.values.current_values.get(vtype, 50.0)
            desired = self.values.desired_values.get(vtype, 100.0)
            priority = self.values.value_priorities.get(vtype, 0.25)
            distance = (current - desired) / 100.0
            weighted_distance = distance * priority
            total += weighted_distance
            total = 1 - total
        self.state.wellbeing = np.clip(total / len(ValueType), -1.0, 1.0)

    def update_agent_state_properly(self):
        """Обновить состояние агента"""
        self.update_wellbeing()
        if abs(self.state.mood) > 0.5:
            self.state.consume_resources(0.02)

    def take_turn(self, turn_number: int) -> Dict[str, Any]:
        """
        Выполнить один ход

        ✅ ВСЕ ЭМОЦИОНАЛЬНЫЕ КОМПОНЕНТЫ СОХРАНЕНЫ И АКТИВНЫ
        Рациональный модуль просто выбирает действие по стратегии
        """
        self.logger.log_turn_start(turn_number)
        self._turn_count += 1

        prev_values = self.values.copy()
        prev_state = copy.deepcopy(self.state)

        # === 1. ЛОГИРОВАНИЕ СОСТОЯНИЙ ===
        self.logger.log_game_state(self.game_state)
        self.logger.log_agent_state(self.state)
        self.logger.log_values(self.values)
        self.logger.log_priorities({vt.name: self.values.value_priorities[vt] for vt in ValueType})

        # === 2. ОЦЕНКА ТЕКУЩЕГО СОСТОЯНИЯ (ОТС) ===
        reaction_intensity, max_focus_value_type = self.ots.evaluate_values_changes(
            self.values, self.state
        )
        self.logger.log_ots_evaluation(reaction_intensity, max_focus_value_type.name)

        # Обновить настроение
        self.state.mood += reaction_intensity / 10.0
        self.state.mood = np.clip(self.state.mood, -0.5, 0.5)

        # === 3. ЭМОЦИОНАЛЬНЫЙ МОДУЛЬ ===
        # ✅ ЭМ ОСТАЕТСЯ АКТИВНЫМ - выбирает действие через DQN
        emotional_action, emotional_intensity = self.emotional_module.forward(
            self.values, self.state
        )
        self.logger.log_emotional_response(str(emotional_action), emotional_intensity)

        # Обновить усталость
        self.state.update_fatigue(emotional_intensity)

        # === 4. РАЦИОНАЛЬНЫЙ МОДУЛЬ ===
        # ✅ РМ ТЕПЕРЬ ПРОСТО ВОЗВРАЩАЕТ ДЕЙСТВИЕ ПО СТРАТЕГИИ
        rational_action, action_type = self.rational_module.forward(
            self.values, self.state, emotional_action, emotional_intensity,
            self.game_state
        )

        # Записать действие в историю
        self.state.record_action(rational_action.name)

        # === 5. ЛОГИРОВАНИЕ И ОБУЧЕНИЕ ===
        self.logger.log_action_execution(str(rational_action), self.strategy.value)

        # Обновить состояние агента
        self.update_agent_state_properly()

        # Применить затухание усталости и стабилизацию настроения
        self.state.apply_fatigue_decay()

        # ✅ ОБУЧЕНИЕ ТОЛЬКО ЭМОЦИОНАЛЬНОГО МОДУЛЯ (РМ не обучается)
        self.emotional_module.train_on_feedback(
            reaction_intensity=reaction_intensity,
            values=self.values,
            state=self.state
        )

        # Логирование обучения
        self.logger.log_learning(
            em_buffer_size=len(self.emotional_module.replay_buffer),
            em_loss=self.emotional_module.last_loss,
            em_epsilon=self.emotional_module.epsilon
        )

        overall_state = self.state.calculate_overall_state()
        self.logger.log_turn_summary(turn_number, overall_state, str(rational_action))

        return {
            'turn': turn_number,
            'action': rational_action.name,
            'strategy': self.strategy.value,
            'emotional_intensity': float(emotional_intensity),
            'mood': float(self.state.mood),
            'fatigue': float(self.state.fatigue),
            'wellbeing': float(self.state.wellbeing),
            'overall_state': float(overall_state),
            'payoff': float(self.values.current_values.get(ValueType.PAYOFF, 0.0))
        }

    def get_info(self) -> Dict[str, Any]:
        """Получить информацию об агенте"""
        return {
            'name': self.name,
            'personality': self.personality.name,
            'emotional_intensity': self.emotional_intensity.name,
            'strategy': self.strategy.name,
            'strategy_value': self.strategy.value,
            'turn_count': self._turn_count,
            'character_traits': {
                'chunk_1': self.character_traits.chunk_1,
                'chunk_2': self.character_traits.chunk_2,
            },
            'current_state': {
                'wellbeing': float(self.state.wellbeing),
                'mood': float(self.state.mood),
                'fatigue': float(self.state.fatigue),
                'resources': float(self.state.resources),
            },
            'values': {
                vtype.name: {
                    'current': float(self.values.current_values.get(vtype, 0.0)),
                    'desired': float(self.values.desired_values.get(vtype, 100.0)),
                    'priority': float(self.values.value_priorities.get(vtype, 0.25))
                }
                for vtype in ValueType
            },
            'emotional_module': {
                'buffer_size': len(self.emotional_module.replay_buffer),
                'epsilon': float(self.emotional_module.epsilon),
                'last_loss': float(self.emotional_module.last_loss) if self.emotional_module.last_loss else None
            }
        }

# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("АГЕНТ С ФИКСИРОВАННОЙ СТРАТЕГИЕЙ И ЭМОЦИОНАЛЬНЫМ МОДУЛЕМ")
    print("="*80)

    # Создать агента с фиксированной стратегией
    agent = Agent(
        name="StrategyBot",
        personality=PersonalityType.PESSIMISTIC,
        emotional_intensity=EmotionalIntensityType.HIGH,
        strategy=FixedStrategy.TIT_FOR_TAT,  # ✅ Выбираем стратегию: TIT_FOR_TAT
        log_level=LogLevel.NORMAL,
        game_actions=['cooperate', 'defect'],
        device='cpu'
    )

    print(f"\n✅ Создан агент {agent.name}")
    print(f"   Стратегия: {agent.strategy.value}")
    print(f"   Личность: {agent.personality.name}")
    print(f"   Интенсивность эмоций: {agent.emotional_intensity.name}")

    # Информация об агенте
    info = agent.get_info()
    print(f"\n📊 Информация об агенте:")
    print(f"   Chunk_1 (порог): {info['character_traits']['chunk_1']:.2f}")
    print(f"   Chunk_2 (интенсивность): {info['character_traits']['chunk_2']:.2f}")

    print("\n" + "="*80)
    print("✅ УСПЕШНО: Файл готов к использованию!")
    print("="*80)
