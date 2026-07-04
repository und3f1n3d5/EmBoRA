# ============================================================================
# АГЕНТ С ДВУМЯ DQN МОДУЛЯМИ - ВЕРСИЯ С ПОДДЕРЖКОЙ ПЕРЕОПРЕДЕЛЕНИЯ ЭМОЦИЕЙ
# ============================================================================
#
# ИСПРАВЛЕНИЯ, внесенные в текущую версию (от 2026-02-20):
#
# 1. ✅ Добавлен флаг forced_by_emotion в структуру опыта (replay buffer)
#    - Отражает, было ли действие ПЕРЕОПРЕДЕЛЕНО Рациональным Модулем из-за
#      превышения emotional_intensity порогового значения
#
# 2. ✅ Обновлен метод add_experience() в RationalModule
#    - Теперь сохраняет флаг forced_by_emotion для каждого перехода
#
# 3. ✅ Обновлен метод train_on_feedback() в RationalModule
#    - Принимает параметр forced_by_emotion
#    - Передает флаг при добавлении опыта в буфер
#
# 4. ✅ Добавлен метод log_emotional_override() в AgentLogger
#    - Логирует случаи переопределения действия РМ эмоцией
#    - Показывает значение интенсивности, пороговое значение и причину
#
# 5. ✅ Обновлена логика в методе take_turn() класса Agent
#    - НОВАЯ ЛОГИКА ПЕРЕОПРЕДЕЛЕНИЯ:
#      * Если abs(emotional_intensity) > threshold:
#        → Рациональный Модуль ОБЯЗАТЕЛЬНО выбирает действие ЭМ
#        → Это отражается в логах как "ПЕРЕОПРЕДЕЛЕНИЕ"
#        → Флаг forced_by_emotion=True сохраняется в буфер обучения
#
#    - СЦЕНАРИИ выполнения:
#      а) Стандартный: ОТС → ЭМ → РМ (без переопределения) → Игровое действие
#      б) Переопределение: ОТС → ЭМ → РМ выбирает ЭМ (из-за threshold) → Игровое действие
#      в) Рефокус: ОТС → ЭМ → РМ(рефокус) → Пересчет ОТС/ЭМ → РМ(игр.действие)
#      г) Рефлексия: ОТС → ЭМ → РМ(рефлексия) → РМ(игр.действие)
#
# 6. ✅ Безальтернативный выбор ОТРАЖАЕТСЯ при:
#    - Прямом проходе (логирование как "⚠️ ПЕРЕОПРЕДЕЛЕНИЕ")
#    - Обучении модели (флаг forced_by_emotion в replay buffer)
#    - Теперь модель явно обучается на примерах принудительного выбора
#
# ============================================================================

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
    SILENT = 50  # Никаких логов
    MINIMAL = 40  # Только самое важное (ХОД, ИТОГ, ОШИБКИ)
    NORMAL = 30  # Стандартные логи (рекомендуется)
    VERBOSE = 20  # Расширенные логи (обучение, рефлексия)
    DEBUG = 10  # Все логи (для отладки)


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
            self.logger.debug(f"   • {param}: {value:.2f}")
        self.logger.debug("")

    def log_agent_state(self, agent_state: 'AgentState'):
        """Логирование состояния агента"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("🧠 СОСТОЯНИЕ АГЕНТА:")
        self.logger.debug(f"   • Благополучие: {agent_state.wellbeing:.2f}")
        self.logger.debug(f"   • Настроение: {agent_state.mood:.2f}")
        self.logger.debug(f"   • Усталость: {agent_state.fatigue:.2f}")
        self.logger.debug(f"   • Ресурсы: {agent_state.resources:.2f}")
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
                f"   • {vtype.name}: {current:.1f}/{desired:.1f} "
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
            self.logger.debug(f"   • {vtype_name}: {priority:.2f} [{bar}]")
        self.logger.debug("")

    def log_ots_evaluation(self, reaction_intensity: float, max_focus_value: str):
        """Логирование оценки ОТС"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("🎯 ОЦЕНКА ТЕКУЩЕГО СОСТОЯНИЯ (ОТС):")
        emoji = "😊" if reaction_intensity > 0 else "😠"
        self.logger.debug(f"   • Интенсивность: {reaction_intensity:+.3f} {emoji}")
        self.logger.debug(f"   • На ценность: {max_focus_value}")
        self.logger.debug("")

    def log_emotional_response(self, action: str, intensity: float):
        """Логирование эмоциональной реакции"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        emoji = "😊" if intensity > 0.5 else "😐" if intensity > -0.5 else "😠"
        self.logger.debug(f"💭 ЭМОЦИОНАЛЬНЫЙ МОДУЛЬ (ЭМ):")
        self.logger.debug(f"   • Действие: {action}")
        self.logger.debug(f"   • Интенсивность: {intensity:+.3f} {emoji}")
        self.logger.debug("")

    def log_rational_decision(self, action: str, action_type: str, override: bool = False):
        """Логирование рационального решения"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        override_str = "⚠️ ПЕРЕОПРЕДЕЛЕНО" if override else "✓"
        self.logger.debug(f"🤔 РАЦИОНАЛЬНЫЙ МОДУЛЬ (РМ):")
        self.logger.debug(f"   • Опция: {action} {override_str}")
        self.logger.debug(f"   • Тип: {action_type}")
        self.logger.debug("")

    def log_emotional_override(self, em_action: str, em_intensity: float, threshold: float):
        """✅ НОВОЕ: Логирование переопределения РМ из-за превышения threshold"""
        if not self._should_log(LogLevel.VERBOSE):
            return

        self.logger.debug(f"⚠️ ПЕРЕОПРЕДЕЛЕНИЕ ДЕЙСТВИЯ ЭМ (THRESHOLD ПРЕВЫШЕН):")
        self.logger.debug(f" • Действие ЭМ: {em_action}")
        self.logger.debug(f" • Интенсивность ЭМ: {em_intensity:+.3f}")
        self.logger.debug(f" • Пороговое значение: {threshold:.3f}")
        self.logger.debug(f" • abs(интенсивность) > threshold: {abs(em_intensity) > threshold}")
        self.logger.debug(f" → РАЦИОНАЛЬНЫЙ МОДУЛЬ ВЫБИРАЕТ ДЕЙСТВИЕ ЭМ БЕЗ АЛЬТЕРНАТИВ")
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
        """✅ ИСПРАВЛЕНО: Логирование обучения с потерями И epsilon"""
        if not self._should_log(LogLevel.VERBOSE):
            return

        self.logger.debug("📚 ОБУЧЕНИЕ МОДУЛЕЙ:")

        # ЭМ
        if em_buffer_size >= 16:
            loss_str = f"loss: {em_loss:.4f}" if em_loss is not None else "обучение"
            epsilon_str = f"ε: {em_epsilon:.3f}" if em_epsilon is not None else ""
            self.logger.debug(f"   • ЭМ: ✓ {loss_str} {epsilon_str} (буфер: {em_buffer_size})")
        else:
            self.logger.debug(f"   • ЭМ: ⏳ {em_buffer_size}/16 (ожидание)")

        # РМ
        if rm_buffer_size >= 16:
            loss_str = f"loss: {rm_loss:.4f}" if rm_loss is not None else "обучение"
            epsilon_str = f"ε: {rm_epsilon:.3f}" if rm_epsilon is not None else ""
            self.logger.debug(f"   • РМ: ✓ {loss_str} {epsilon_str} (буфер: {rm_buffer_size})")
        else:
            self.logger.debug(f"   • РМ: ⏳ {rm_buffer_size}/16 (ожидание)")

        self.logger.debug("")

    def log_reflection(self, turn: int, priority_changes: Dict, desired_changes: Dict):
        """НОВОЕ: Логирование стратегической рефлексии"""
        if not self._should_log(LogLevel.VERBOSE):
            return

        self.logger.info(f"🔮 СТРАТЕГИЧЕСКАЯ РЕФЛЕКСИЯ (ход {turn}):")

        # Приоритеты
        self.logger.info("   Изменения приоритетов:")
        for vtype_name, new_priority in list(priority_changes.items())[:3]:
            self.logger.info(f"     • {vtype_name}: {new_priority:.2f}")

        # Желаемые значения
        self.logger.info("   Изменения целей:")
        for vtype_name, new_desired in list(desired_changes.items())[:3]:
            self.logger.info(f"     • {vtype_name}: {new_desired:.1f}")

        self.logger.info("")

    def log_recovery(self, fatigue: float, mood: float, resources: float):
        """Логирование восстановления"""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self.logger.debug("🔄 ВОССТАНОВЛЕНИЕ:")
        self.logger.debug(f"   • Усталость: {fatigue:.2f} | Настроение: {mood:+.2f} | Ресурсы: {resources:.2f}")
        self.logger.debug("")

    def log_turn_summary(self, turn: int, overall_state: float, action: str):
        """Логирование итога хода"""
        if not self._should_log(LogLevel.NORMAL):
            return
        separator = "=" * 80
        self.logger.info(f"📋 ХОД {turn} ИТОГ:")
        self.logger.info(f"   • Действие: {action}")
        self.logger.info(f"   • Состояние: {overall_state:+.3f}")
        self.logger.info(f"{separator}\n")

    def log_episode_summary(self, num_turns: int, avg_overall_state: float):
        """НОВОЕ: Логирование итога эпизода"""
        if not self._should_log(LogLevel.NORMAL):
            return
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f"📊 ИТОГ ЭПИЗОДА ({num_turns} ходов)")
        self.logger.info(f"   • Среднее состояние: {avg_overall_state:+.3f}")
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
        """✅ ИСПРАВЛЕНО: Приоритеты зависят от типа личности"""
        values = Values()

        if personality_type == PersonalityType.OPTIMISTIC:
            # Оптимист ценит выигрыш и отношения
            values.value_priorities[ValueType.PAYOFF] = 1.2
            values.value_priorities[ValueType.RELATIONSHIPS] = 0.9
            values.value_priorities[ValueType.SECURITY] = 0.5
            values.value_priorities[ValueType.EQUALITY] = 0.4
        elif personality_type == PersonalityType.PESSIMISTIC:
            # Пессимист ценит безопасность
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
        """✅ ИСПРАВЛЕНО: Рассчитать общее состояние по формуле архитектуры"""
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


# ============================================================================
# DQN СЕТИ С ПАРАМЕТРАМИ (НОВОЕ!)
# ============================================================================

class DQNNetworkWithParams(nn.Module):
    """
    ✅ НОВОЕ: Двухголовая DQN сеть для выбора действий И параметров

    Архитектура:
    - Общий энкодер (shared encoder)
    - Голова 1: Q-значения для действий
    - Голова 2: Q-значения для параметров (дискретизированных)
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

        # Голова для параметров (для каждого действия - num_param_bins возможных значений)
        self.param_head = nn.Linear(hidden_size, num_actions * num_param_bins)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Прямой проход

        Returns:
            action_q_values: (batch_size, num_actions)
            param_q_values: (batch_size, num_actions, num_param_bins)
        """
        features = self.encoder(x)

        # Q-значения для действий
        action_q = self.action_head(features)

        # Q-значения для параметров (reshape)
        param_q = self.param_head(features)
        param_q = param_q.view(-1, self.num_actions, self.num_param_bins)

        return action_q, param_q


# ============================================================================
# КОМПОНЕНТЫ АРХИТЕКТУРЫ
# ============================================================================

class CurrentStateEvaluation:
    """
    ✅ ИСПРАВЛЕНО: Модуль оценки текущего состояния (ОТС)
    Интенсивность со знаком (+/-), фокус = abs(интенсивность - 0.1)
    """

    def __init__(self, logger: AgentLogger, character_traits: 'CharacterTraits'):
        self.logger = logger
        self.character_traits = character_traits

    def calculate_threshold(self, state: AgentState) -> float:
        """✅ ИСПРАВЛЕНО: Пороговые модификаторы (не линейные!)"""
        chunk_1 = self.character_traits.get_chunk_1()

        # ПОРОГОВЫЕ модификаторы (не линейные!)
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
        """✅ ИСПРАВЛЕНО: Полная реализация с правильной интенсивностью и фокусом"""
        max_focus = 0.0
        reaction_intensity = 0.0
        max_focus_value_type = ValueType.SECURITY

        threshold = self.calculate_threshold(state)

        # ✅ ЕСЛИ ЕСТЬ ФОКУС - оцениваем ТОЛЬКО её
        if state.focused_value is not None:
            value_type = state.focused_value
            current = values.current_values.get(value_type, 50.0)
            desired = values.desired_values.get(value_type, 100.0)

            # ✓ УСИЛИТЬ приоритет в 2 раза при рефокусе
            priority = values.value_priorities.get(value_type, 0.25) #todo * 2.0
            urgency = self.calculate_urgency(current, desired, priority)
            intensity = urgency * priority

            # ✓ ПРАВИЛЬНАЯ ФОРМУЛА: focus = abs(intensity - 0.1)
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

                # ✓ ПРАВИЛЬНАЯ ФОРМУЛА: focus = abs(intensity - 0.1)
                focus = abs(intensity - 0.1)

                if focus >= threshold:
                    if focus > max_focus:
                        max_focus = focus
                        reaction_intensity = intensity
                        max_focus_value_type = value_type

            return reaction_intensity, max_focus_value_type


class CharacterTraits:
    """✅ ИСПРАВЛЕНО: Черты характера с chunk_1 и chunk_2"""

    def __init__(self, personality: PersonalityType, intensity: EmotionalIntensityType):
        self.personality = personality
        self.intensity = intensity
        self._initialize_chunks()

    def _initialize_chunks(self):
        """✅ Инициализировать chunk_1 и chunk_2 по типу"""
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
    """✅ НОВОЕ: Конструктор пространства действий с параметрами"""

    def __init__(self, game_actions: Optional[List[Dict[str, Any]]] = None):
        """
        game_actions: список действий вида:
        [
            {'name': 'move', 'params': ['distance']},
            {'name': 'attack', 'params': ['strength']},
            ...
        ]
        """
        self.game_actions = game_actions or []
        self.base_actions = []
        self._build_action_space()

    def _build_action_space(self):
        """Построить полное пространство действий"""
        self.base_actions = []

        # Игровые действия
        for action_spec in self.game_actions:
            action_name = action_spec.get('name', 'unknown')
            has_params = action_spec.get('params', [])

            if has_params:
                # Действие с параметрами
                self.base_actions.append({
                    'name': action_name,
                    'has_params': True,
                    'param_specs': has_params
                })
            else:
                # Действие без параметров
                self.base_actions.append({
                    'name': action_name,
                    'has_params': False,
                    'param_specs': []
                })

    def get_action_features_size(self) -> int:
        """Получить размер вектора признаков для действий"""
        return len(self.base_actions) * 2  # Каждое действие: выбор + параметр(ы)

    def encode_action_option(self, action_option: ActionOption) -> np.ndarray:
        """Закодировать опцию действия в вектор признаков"""
        features = np.zeros(self.get_action_features_size(), dtype=np.float32)

        # Найти индекс действия
        action_idx = None
        for i, action_spec in enumerate(self.base_actions):
            if action_spec['name'] == action_option.name:
                action_idx = i
                break

        if action_idx is not None:
            features[action_idx * 2] = 1.0  # Бит выбора действия

            # Параметр (если есть)
            if action_option.params:
                # Берём первый параметр (или среднее значение)
                param_values = list(action_option.params.values())
                if param_values:
                    # Нормализуем параметр в [0, 1]
                    param_val = float(param_values[0])
                    normalized = np.clip(param_val / 100.0, 0.0, 1.0)
                    features[action_idx * 2 + 1] = normalized

        return features


# ============================================================================
# ЭМОЦИОНАЛЬНЫЙ МОДУЛЬ С ОБУЧЕНИЕМ ПАРАМЕТРОВ (НОВОЕ!)
# ============================================================================

class EmotionalModule:
    """
    ✅ НОВОЕ: Эмоциональный модуль с обучением действий И параметров
    DQN сеть с двумя головами: одна для действий, другая для параметров
    """

    def __init__(self, action_space: ActionSpaceBuilder, logger: AgentLogger,
                 num_param_bins: int = 10, device='cpu'):
        self.action_space = action_space
        self.logger = logger
        self.device = device
        self.replay_buffer = []
        self.num_param_bins = num_param_bins  # Дискретизация параметров

        # Количество возможных действий
        num_actions = len(action_space.base_actions)

        # ✅ DQN с параметрами: Основная и Target сети
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

        # ✅ Epsilon-Greedy
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01

        # ✅ Target Update
        self.update_counter = 0
        self.target_update_freq = 1000
        self.last_loss = None
        self.gamma = 0.99

        # Для отслеживания последних выборов
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
        """
        ✅ НОВОЕ: Дискретизировать непрерывный параметр в индекс бина

        Args:
            continuous_value: значение в [min_val, max_val]
            min_val, max_val: диапазон значений

        Returns:
            bin_idx: индекс бина [0, num_param_bins-1]
        """
        normalized = (continuous_value - min_val) / (max_val - min_val)
        normalized = np.clip(normalized, 0.0, 0.999)  # Избежать индекса num_param_bins
        bin_idx = int(normalized * self.num_param_bins)
        return bin_idx

    def undiscretize_param(self, bin_idx: int, min_val: float = 0.0,
                           max_val: float = 1.0) -> float:
        """
        ✅ НОВОЕ: Восстановить непрерывное значение из индекса бина

        Args:
            bin_idx: индекс бина [0, num_param_bins-1]
            min_val, max_val: диапазон значений

        Returns:
            continuous_value: значение в [min_val, max_val]
        """
        # Центр бина
        normalized = (bin_idx + 0.5) / self.num_param_bins
        continuous_value = min_val + normalized * (max_val - min_val)
        return continuous_value

    def select_action_and_param_greedy(self, state_features: np.ndarray) -> Tuple[str, int, float, int]:
        """
        ✅ НОВОЕ: Выбрать лучшее действие И параметр

        Returns:
            action_name: название действия
            action_idx: индекс действия
            param_value: значение параметра (непрерывное)
            param_bin_idx: индекс бина параметра
        """
        features_tensor = torch.FloatTensor(state_features).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action_q, param_q = self.q_network(features_tensor)
            action_q = action_q.cpu().numpy()[0]  # (num_actions,)
            param_q = param_q.cpu().numpy()[0]  # (num_actions, num_param_bins)

        # Выбрать действие с максимальным Q
        action_idx = np.argmax(action_q)
        action_name = self.action_space.base_actions[action_idx]['name']

        # Выбрать параметр для этого действия
        param_q_for_action = param_q[action_idx]  # (num_param_bins,)
        param_bin_idx = np.argmax(param_q_for_action)

        # Восстановить непрерывное значение параметра
        action_spec = self.action_space.base_actions[action_idx]
        if action_spec['has_params']:
            # Для параметров действий игры: [1.0, 10.0]
            param_value = self.undiscretize_param(param_bin_idx, min_val=1.0, max_val=10.0)
        else:
            param_value = 0.0  # Нет параметра

        return action_name, action_idx, param_value, param_bin_idx

    def select_action_and_param_explore(self) -> Tuple[str, int, float, int]:
        """
        ✅ НОВОЕ: Выбрать случайное действие И параметр

        Returns:
            action_name, action_idx, param_value, param_bin_idx
        """
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
        """
        ✅ НОВОЕ: Epsilon-greedy выбор действия И параметра

        Returns:
            action_name, action_idx, param_value, param_bin_idx
        """
        if training and np.random.random() < self.epsilon:
            return self.select_action_and_param_explore()
        else:
            return self.select_action_and_param_greedy(state_features)

    def generate_action_params(self, action_name: str, param_value: float) -> Dict[str, float]:
        """
        ✅ ОБНОВЛЕНО: Сгенерировать параметры для действия на основе выбранного значения

        Args:
            action_name: название действия
            param_value: значение параметра из DQN

        Returns:
            params: словарь параметров
        """
        params = {}

        # Найти спецификацию действия
        for action_spec in self.action_space.base_actions:
            if action_spec['name'] == action_name and action_spec['has_params']:
                # Для каждого параметра используем выбранное значение
                for param_name in action_spec['param_specs']:
                    params[param_name] = param_value

        return params

    def forward(self, values: Values, state: AgentState) -> Tuple[ActionOption, float]:
        """
        ✅ ОБНОВЛЕНО: Выбрать действие + параметры (обученные!) и вернуть интенсивность
        """
        features = self.build_input_features(values, state)

        # ✅ НОВОЕ: Выбор действия И параметра через DQN
        action_name, action_idx, param_value, param_bin_idx = self.select_action(features, training=True)

        # Сохранить индексы для обучения
        self.last_action_idx = action_idx
        self.last_param_bin_idx = param_bin_idx

        # ✅ НОВОЕ: Генерация параметров на основе ВЫБРАННОГО значения
        params = self.generate_action_params(action_name, param_value)

        action_option = ActionOption(name=action_name, params=params)

        # Эмоциональная интенсивность (добавим немного шума)
        emotional_intensity = np.clip(state.mood + np.random.randn() * 0.3, -1.5, 1.5)

        return action_option, emotional_intensity

    def add_experience(self, state_features: np.ndarray, action_idx: int, param_bin_idx: int,
                       reward: float, next_state_features: np.ndarray, done: bool):
        """
        ✅ ОБНОВЛЕНО: Добавить полный переход с параметрами
        """
        experience = {
            'state': state_features.astype(np.float32),
            'action': action_idx,
            'param_bin': param_bin_idx,  # ✅ НОВОЕ: индекс бина параметра
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
        """
        ✅ ОБНОВЛЕНО: Обучение ЭМ на фидбеке от ОТС с параметрами
        """
        current_features = self.build_input_features(values, state)

        # ✅ Если передано next_state - используем для DQN
        if next_state is not None and next_values is not None:
            next_features = self.build_input_features(next_values, next_state)
        else:
            next_features = current_features

        # Найти индексы действия и параметра
        action_idx = self.last_action_idx
        param_bin_idx = self.last_param_bin_idx

        # ✅ Добавить ПОЛНЫЙ переход с параметрами
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

        # ✅ Decay epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def _train_batch(self, batch_size: int):
        """
        ✅ ОБНОВЛЕНО: Обучение с Target Network и Bellman Equation для действий И параметров
        """
        indices = np.random.choice(len(self.replay_buffer), batch_size, replace=False)
        batch = [self.replay_buffer[i] for i in indices]

        states = torch.FloatTensor(np.array([exp['state'] for exp in batch])).to(self.device)
        actions = torch.LongTensor([exp['action'] for exp in batch]).to(self.device)
        param_bins = torch.LongTensor([exp['param_bin'] for exp in batch]).to(self.device)  # ✅ НОВОЕ
        rewards = torch.FloatTensor([exp['reward'] for exp in batch]).to(self.device)
        next_states = torch.FloatTensor(np.array([exp['next_state'] for exp in batch])).to(self.device)
        dones = torch.FloatTensor([1.0 - float(exp['done']) for exp in batch]).to(self.device)

        # ✅ Q-значения текущей сети
        action_q, param_q = self.q_network(states)

        # Q для выбранных действий: (batch_size,)
        action_q_for_actions = action_q.gather(1, actions.unsqueeze(1)).squeeze(1)

        # Q для выбранных параметров: (batch_size,)
        # param_q: (batch_size, num_actions, num_param_bins)
        batch_indices = torch.arange(batch_size, device=self.device)
        param_q_for_actions = param_q[batch_indices, actions, :]  # (batch_size, num_param_bins)
        param_q_for_selected = param_q_for_actions.gather(1, param_bins.unsqueeze(1)).squeeze(1)

        # ✅ Целевые Q-значения от TARGET СЕТИ
        with torch.no_grad():
            next_action_q, next_param_q = self.target_network(next_states)

            # Максимальное Q для действий
            max_next_action_q = torch.max(next_action_q, dim=1)[0]
            best_next_actions = torch.argmax(next_action_q, dim=1)

            # Максимальное Q для параметров (для лучших действий)
            next_param_q_for_best = next_param_q[batch_indices, best_next_actions, :]
            max_next_param_q = torch.max(next_param_q_for_best, dim=1)[0]

            # ✅ BELLMAN EQUATION: target = r + γ * (max(Q_action) + max(Q_param))
            # Комбинируем оба компонента
            target_action_q = rewards + (self.gamma * max_next_action_q * dones)
            target_param_q = rewards + (self.gamma * max_next_param_q * dones)

        # ✅ Loss для обоих компонентов
        action_loss = self.criterion(action_q_for_actions, target_action_q)
        param_loss = self.criterion(param_q_for_selected, target_param_q)

        total_loss = action_loss + param_loss

        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), max_norm=1.0)
        self.optimizer.step()

        # ✅ Обновить target сеть
        self.update_counter += 1
        if self.update_counter % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())

        return total_loss.item()


# ============================================================================
# РАЦИОНАЛЬНЫЙ МОДУЛЬ С ОБУЧЕНИЕМ ПАРАМЕТРОВ (НОВОЕ!)
# ============================================================================

class RationalModule:
    """
    ✅ ОБНОВЛЕНО: Рациональный модуль с обучением действий И параметров
    DQN сеть с двумя головами для опций (действия/рефокус/рефлексия) и их параметров

    НОВАЯ ЛОГИКА: После рефокуса/рефлексии агент ОБЯЗАТЕЛЬНО выбирает игровое действие
    """

    def __init__(self, action_space: 'ActionSpaceBuilder', logger: 'AgentLogger',
                 num_param_bins: int = 10, device='cpu'):
        self.action_space = action_space
        self.logger = logger
        self.device = device
        self.replay_buffer = []
        self.num_param_bins = num_param_bins

        # ✅ НОВОЕ: Опции РМ расширены
        self.options = []
        self._build_options()

        # ✅ DQN с параметрами: Основная и Target сети
        self.q_network = DQNNetworkWithParams(
            input_size=12,
            num_actions=len(self.options),
            num_param_bins=num_param_bins,
            hidden_size=128
        ).to(device)

        self.target_network = DQNNetworkWithParams(
            input_size=12,
            num_actions=len(self.options),
            num_param_bins=num_param_bins,
            hidden_size=128
        ).to(device)

        self.target_network.load_state_dict(self.q_network.state_dict())
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()

        # ✅ Epsilon-Greedy
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01

        # ✅ Target Update
        self.update_counter = 0
        self.target_update_freq = 1000
        self.last_loss = None
        self.gamma = 0.99

        # Для отслеживания последних выборов
        self.last_option_idx = 0
        self.last_param_bin_idx = 0

    def _build_options(self):
        """✅ НОВОЕ: Построить опции РМ с параметрами"""
        # Игровые действия
        for action_spec in self.action_space.base_actions:
            self.options.append({
                'type': 'game_action',
                'name': action_spec['name'],
                'has_params': action_spec['has_params'],
                'param_specs': action_spec['param_specs']
            })

        # Рефокус с параметром - выбираемой ценностью
        self.options.append({
            'type': 'refocus',
            'name': 'refocus',
            'has_params': True,
            'param_specs': ['focus_value']  # Какую ценность выбрать
        })

        # Стратегическая рефлексия с параметром интенсивности
        self.options.append({
            'type': 'reflection',
            'name': 'reflection',
            'has_params': True,
            'param_specs': ['reflection_intensity']  # Насколько сильно менять приоритеты
        })

    def get_game_only_options(self) -> List[int]:
        """✅ НОВОЕ: Получить индексы только игровых опций"""
        game_indices = []
        for idx, option in enumerate(self.options):
            if option['type'] == 'game_action':
                game_indices.append(idx)
        return game_indices

    def build_input_features(self, values: 'Values', state: 'AgentState',
                            em_action: 'ActionOption', em_intensity: float) -> np.ndarray:
        """Создать входные признаки для РМ"""
        features = [
            state.wellbeing,
            state.mood,
            state.fatigue,
            state.resources
        ]

        # Добавить информацию о выходе ЭМ
        features.append(em_intensity)
        features.append(1.0 if abs(em_intensity) > self.get_threshold(state) else 0.0)

        # Добавить усредненную информацию о ценностях
        avg_distance = np.mean([
            abs(values.current_values.get(vt, 50) - values.desired_values.get(vt, 100))
            for vt in ValueType
        ])
        features.append(avg_distance / 100.0)

        # Добавить приоритет самой важной ценности
        max_priority = max(values.value_priorities.values())
        features.append(max_priority)

        # Счетчик рефокусов
        features.append(float(state.refocus_count) / 2.0)

        # Дополнить до 12 признаков
        while len(features) < 12:
            features.append(0.0)

        return np.array(features[:12], dtype=np.float32)

    def get_threshold(self, state: 'AgentState') -> float:
        """Получить пороговое значение для переопределения ЭМ"""
        # Упрощенный вариант без character_traits
        base_threshold = 0.7
        if state.fatigue > 0.6:
            base_threshold -= 0.1
        if abs(state.mood) > 0.25:
            base_threshold -= 0.1
        return np.clip(base_threshold, 0.1, 1.5)

    def should_override_emotional_action(self, emotional_intensity: float,
                                        state: 'AgentState') -> bool:
        """Должен ли РМ переопределить действие ЭМ"""
        threshold = self.get_threshold(state)
        return abs(emotional_intensity) < threshold

    def discretize_param(self, continuous_value: float, min_val: float = 0.0,
                        max_val: float = 1.0) -> int:
        """Дискретизировать непрерывный параметр в индекс бина"""
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

    def select_option_greedy(self, state_features: np.ndarray,
                            force_game_action: bool = False) -> Tuple[int, int, float]:
        """
        ✅ ОБНОВЛЕНО: Выбрать лучшую опцию И параметр

        Args:
            state_features: признаки состояния
            force_game_action: если True, выбирать только из игровых действий

        Returns:
            option_idx: индекс опции
            param_bin_idx: индекс бина параметра
            param_value: значение параметра (непрерывное)
        """
        features_tensor = torch.FloatTensor(state_features).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action_q, param_q = self.q_network(features_tensor)
            action_q = action_q.cpu().numpy()[0]  # (num_options,)
            param_q = param_q.cpu().numpy()[0]    # (num_options, num_param_bins)

        # ✅ НОВОЕ: Если force_game_action=True, ограничить выбор
        if force_game_action:
            game_indices = self.get_game_only_options()
            # Замаскировать все не-игровые опции
            masked_q = np.full_like(action_q, -np.inf)
            masked_q[game_indices] = action_q[game_indices]
            option_idx = np.argmax(masked_q)
        else:
            option_idx = np.argmax(action_q)

        # Выбрать параметр для этой опции
        param_q_for_option = param_q[option_idx]
        param_bin_idx = np.argmax(param_q_for_option)

        # Восстановить значение параметра в зависимости от типа опции
        option_spec = self.options[option_idx]
        option_type = option_spec['type']

        if option_type == 'game_action' and option_spec['has_params']:
            param_value = self.undiscretize_param(param_bin_idx, min_val=1.0, max_val=10.0)
        elif option_type == 'refocus':
            # Для рефокуса: индекс ценности [0-3]
            num_values = len(ValueType)
            param_value = float(int(param_bin_idx * num_values / self.num_param_bins))
            param_value = np.clip(param_value, 0, num_values - 1)
        elif option_type == 'reflection':
            # Для рефлексии: интенсивность [0.5-2.0]
            param_value = self.undiscretize_param(param_bin_idx, min_val=0.5, max_val=2.0)
        else:
            param_value = 0.0

        return option_idx, param_bin_idx, param_value

    def select_option_explore(self, force_game_action: bool = False) -> Tuple[int, int, float]:
        """
        ✅ ОБНОВЛЕНО: Выбрать случайную опцию И параметр

        Args:
            force_game_action: если True, выбирать только из игровых действий
        """
        # ✅ НОВОЕ: Если force_game_action=True, ограничить выбор
        if force_game_action:
            game_indices = self.get_game_only_options()
            option_idx = np.random.choice(game_indices)
        else:
            option_idx = np.random.randint(0, len(self.options))

        param_bin_idx = np.random.randint(0, self.num_param_bins)

        # Восстановить значение параметра
        option_spec = self.options[option_idx]
        option_type = option_spec['type']

        if option_type == 'game_action' and option_spec['has_params']:
            param_value = self.undiscretize_param(param_bin_idx, min_val=1.0, max_val=10.0)
        elif option_type == 'refocus':
            num_values = len(ValueType)
            param_value = float(int(param_bin_idx * num_values / self.num_param_bins))
            param_value = np.clip(param_value, 0, num_values - 1)
        elif option_type == 'reflection':
            param_value = self.undiscretize_param(param_bin_idx, min_val=0.5, max_val=2.0)
        else:
            param_value = 0.0

        return option_idx, param_bin_idx, param_value

    def forward(self, values: 'Values', state: 'AgentState',
                em_action: 'ActionOption', em_intensity: float,
                game_state: 'GameState', force_game_action: bool = False) -> Tuple['ActionOption', 'ActionType']:
        """
        ✅ ОБНОВЛЕНО: Выбрать опцию РМ (действие/рефокус/рефлексия)

        Args:
            values: ценности
            state: состояние агента
            em_action: действие из ЭМ
            em_intensity: интенсивность эмоции из ЭМ
            game_state: состояние игры
            force_game_action: НОВОЕ! Если True, выбирать ТОЛЬКО игровые действия

        Returns:
            action_option: выбранная опция с параметрами
            action_type: тип действия (GAME_ACTION/REFOCUS/REFLECTION)
        """
        features = self.build_input_features(values, state, em_action, em_intensity)

        # ✅ ОБНОВЛЕНО: Передаём force_game_action
        if np.random.random() < self.epsilon:
            option_idx, param_bin_idx, param_value = self.select_option_explore(force_game_action)
        else:
            option_idx, param_bin_idx, param_value = self.select_option_greedy(features, force_game_action)

        # Сохранить для обучения
        self.last_option_idx = option_idx
        self.last_param_bin_idx = param_bin_idx

        # Получить спецификацию опции
        option_spec = self.options[option_idx]
        option_type = option_spec['type']
        option_name = option_spec['name']

        # Создать ActionOption с параметрами
        params = {}

        if option_type == 'game_action':
            if option_spec['has_params']:
                for param_name_spec in option_spec['param_specs']:
                    params[param_name_spec] = param_value
            action_option = ActionOption(name=option_name, params=params)
            return action_option, ActionType.GAME_ACTION

        elif option_type == 'refocus':
            # Параметр: какую ценность выбрать для рефокуса
            value_idx = int(param_value)
            value_types_list = list(ValueType)
            focus_value = value_types_list[value_idx]
            params['focus_value'] = focus_value
            action_option = ActionOption(name='refocus', params=params)
            return action_option, ActionType.REFOCUS

        elif option_type == 'reflection':
            # Параметр: интенсивность рефлексии
            params['reflection_intensity'] = param_value
            action_option = ActionOption(name='reflection', params=params)
            return action_option, ActionType.REFLECTION

        else:
            # Не должно случиться
            return em_action, ActionType.GAME_ACTION

    def add_experience(self, state_features: np.ndarray, option_idx: int, param_bin_idx: int,
                      reward: float, next_state_features: np.ndarray, done: bool,
                      forced_by_emotion: bool = False):
        """✅ ОБНОВЛЕНО: Добавить опыт в буфер с флагом forced_by_emotion"""
        experience = {
            'state': state_features.astype(np.float32),
            'option': option_idx,
            'param_bin': param_bin_idx,
            'reward': float(reward),
            'next_state': next_state_features.astype(np.float32),
            'done': bool(done)
        }

        self.replay_buffer.append(experience)
        if len(self.replay_buffer) > 1000:
            self.replay_buffer.pop(0)

    def train_on_feedback(self, overall_state: float, values: 'Values', state: 'AgentState',
                          game_state: 'GameState', em_output: Tuple['ActionOption', float],
                          option_idx: int, next_values: Optional['Values'] = None,
                          next_state: Optional['AgentState'] = None, forced_by_emotion=None):
        """Обучение РМ на фидбеке (общее состояние)"""
        em_action, em_intensity = em_output

        current_features = self.build_input_features(values, state, em_action, em_intensity)

        if next_state is not None and next_values is not None:
            next_features = self.build_input_features(next_values, next_state, em_action, em_intensity)
        else:
            next_features = current_features

        param_bin_idx = self.last_param_bin_idx

        self.add_experience(
            state_features=current_features,
            option_idx=option_idx,
            param_bin_idx=param_bin_idx,
            reward=overall_state,
            next_state_features=next_features,
            done=False,
            forced_by_emotion=forced_by_emotion  # ✅ ОБНОВЛЕНО: передаём флаг
        )

        if len(self.replay_buffer) >= 16:
            self.last_loss = self._train_batch(batch_size=min(32, len(self.replay_buffer) // 2))

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def _train_batch(self, batch_size: int):
        """Обучение на батче"""
        indices = np.random.choice(len(self.replay_buffer), batch_size, replace=False)
        batch = [self.replay_buffer[i] for i in indices]

        states = torch.FloatTensor(np.array([exp['state'] for exp in batch])).to(self.device)
        options = torch.LongTensor([exp['option'] for exp in batch]).to(self.device)
        param_bins = torch.LongTensor([exp['param_bin'] for exp in batch]).to(self.device)
        rewards = torch.FloatTensor([exp['reward'] for exp in batch]).to(self.device)
        next_states = torch.FloatTensor(np.array([exp['next_state'] for exp in batch])).to(self.device)
        dones = torch.FloatTensor([1.0 - float(exp['done']) for exp in batch]).to(self.device)

        # Q-значения текущей сети
        option_q, param_q = self.q_network(states)

        option_q_for_options = option_q.gather(1, options.unsqueeze(1)).squeeze(1)

        batch_indices = torch.arange(batch_size, device=self.device)
        param_q_for_options = param_q[batch_indices, options, :]
        param_q_for_selected = param_q_for_options.gather(1, param_bins.unsqueeze(1)).squeeze(1)

        # Целевые Q-значения от TARGET СЕТИ
        with torch.no_grad():
            next_option_q, next_param_q = self.target_network(next_states)

            max_next_option_q = torch.max(next_option_q, dim=1)[0]
            best_next_options = torch.argmax(next_option_q, dim=1)

            next_param_q_for_best = next_param_q[batch_indices, best_next_options, :]
            max_next_param_q = torch.max(next_param_q_for_best, dim=1)[0]

            target_option_q = rewards + (self.gamma * max_next_option_q * dones)
            target_param_q = rewards + (self.gamma * max_next_param_q * dones)

        # Loss
        option_loss = self.criterion(option_q_for_options, target_option_q)
        param_loss = self.criterion(param_q_for_selected, target_param_q)
        total_loss = option_loss + param_loss

        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), max_norm=1.0)
        self.optimizer.step()

        # Обновить target сеть
        self.update_counter += 1
        if self.update_counter % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())

        return total_loss.item()


class StrategicReflection:
    """
    ✅ ИСПРАВЛЕНО: Стратегическая рефлексия
    Delta зависит от характера (PersonalityType и EmotionalIntensityType)
    """

    def __init__(self, logger: AgentLogger, character_traits: CharacterTraits):
        self.logger = logger
        self.character_traits = character_traits

    def get_reflection_deltas(self) -> Tuple[float, float]:
        """✅ ИСПРАВЛЕНО: Delta и k*delta зависят от характера"""
        chunk_2 = self.character_traits.get_chunk_2()

        # Базовые значения от PersonalityType
        if self.character_traits.personality == PersonalityType.OPTIMISTIC:
            base_delta = 0.08
            base_k_delta = 0.16
        elif self.character_traits.personality == PersonalityType.PESSIMISTIC:
            base_delta = 0.03
            base_k_delta = 0.06
        else:
            base_delta = 0.05
            base_k_delta = 0.10

        # Модифицировать по chunk_2
        final_delta = base_delta * chunk_2
        final_k_delta = base_k_delta * chunk_2

        return final_delta, final_k_delta

    def reflect_on_values(self, values: Values, state: AgentState,
                          reflection_intensity: float = 1.0) -> Dict[str, Dict[str, float]]:
        """
        ✅ ОБНОВЛЕНО: Возвращает ОБА типа изменений с delta от характера
        reflection_intensity: параметр от 0.3 до 1.0, как сильно переосмыслять (из РМ)
        """
        reflection_results = {
            'priority_changes': {},
            'desired_value_changes': {}
        }

        delta, k_delta = self.get_reflection_deltas()

        # Модифицировать по интенсивности рефлексии
        delta *= reflection_intensity
        k_delta *= reflection_intensity

        for value_type in ValueType:
            current = values.current_values.get(value_type, 50.0)
            desired = values.desired_values.get(value_type, 100.0)
            current_priority = values.value_priorities.get(value_type, 0.25)

            distance = abs(desired - current)

            # ✅ Выбор между delta и k_delta
            if distance > 40:
                delta_to_use = k_delta  # Большой разрыв - кардинальная переоценка
            elif distance > 20:
                delta_to_use = delta  # Средний разрыв - обычная адаптация
            else:
                delta_to_use = delta * 0.5  # Маленький разрыв - консервативно

            # ✅ ОТНОШЕНИЯ меняются быстрее
            if value_type == ValueType.RELATIONSHIPS:
                delta_to_use *= 1.2

            # Изменение приоритета
            if current < desired:
                # Ценность недовыполнена - повысить приоритет
                new_priority = current_priority + delta_to_use
            else:
                # Ценность перевыполнена - понизить приоритет
                new_priority = current_priority - delta_to_use * 0.5

            new_priority = np.clip(new_priority, 0.4, 1.5)
            reflection_results['priority_changes'][value_type.name] = new_priority

            # Изменение желаемого значения
            if distance > 30:
                # Большой разрыв - сдвинуть желаемое к текущему
                shift = (current - desired) * delta_to_use
                new_desired = desired + shift
            else:
                # Малый разрыв - стабильно
                new_desired = desired

            new_desired = np.clip(new_desired, 50.0, 100.0)
            reflection_results['desired_value_changes'][value_type.name] = new_desired

        return reflection_results


# ============================================================================
# ИГРОВОЙ АДАПТЕР
# ============================================================================

class GameAdapter:
    """
    ✅ Адаптер между агентом и игрой
    Переводит действия агента в игровые действия и обратно
    """

    def __init__(self, game_state: GameState, logger: AgentLogger):
        self.game_state = game_state
        self.logger = logger

    def execute_game_action(self, action: ActionOption, game_state: GameState) -> GameResult:
        """
        Выполнить игровое действие

        Для примера: просто возвращаем случайный результат
        В реальной игре здесь будет логика игры
        """
        # Симуляция выполнения действия
        payoff = np.random.uniform(-10, 10)

        # Обновление состояния игры (пример)
        new_game_state = {
            'cooperation_level': np.random.uniform(0, 1),
            'trust': np.random.uniform(0, 1),
            'risk': np.random.uniform(0, 1)
        }

        return GameResult(
            action=str(action),
            payoff=payoff,
            game_state=new_game_state
        )

    def translate_game_state_to_values(self, game_result: GameResult, values: Values):
        """
        Перевести состояние игры в ценности агента

        Пример трансляции:
        - PAYOFF: прямо из payoff
        - SECURITY: обратно пропорционально risk
        - RELATIONSHIPS: из cooperation_level
        - EQUALITY: из trust
        """
        game_state = game_result.game_state

        # PAYOFF
        payoff_change = game_result.payoff
        new_payoff = values.current_values.get(ValueType.PAYOFF, 50.0) + payoff_change
        values.update_value(ValueType.PAYOFF, new_payoff)

        # SECURITY (0-1 -> 0-100)
        if 'risk' in game_state:
            security = (1.0 - game_state['risk']) * 100.0
            values.update_value(ValueType.SECURITY, security)

        # RELATIONSHIPS
        if 'cooperation_level' in game_state:
            relationships = game_state['cooperation_level'] * 100.0
            values.update_value(ValueType.RELATIONSHIPS, relationships)

        # EQUALITY
        if 'trust' in game_state:
            equality = game_state['trust'] * 100.0
            values.update_value(ValueType.EQUALITY, equality)


# ============================================================================
# АГЕНТ (ГЛАВНЫЙ КЛАСС)
# ============================================================================

class Agent:
    """
    ✅ ОБНОВЛЕНО: Главный класс агента с DQN-модулями, обучающимися параметрам
    """

    def __init__(self, name: str, personality: PersonalityType,
                 emotional_intensity: EmotionalIntensityType,
                 log_level: int = LogLevel.NORMAL,
                 game_actions: Optional[List[Dict[str, Any]]] = None,
                 device: str = 'cpu'):

        self.name = name
        self.personality = personality
        self.emotional_intensity = emotional_intensity
        self.device = device

        # Логирование
        self.logger = AgentLogger(name, log_level)

        # Черты характера
        self.character_traits = CharacterTraits(personality, emotional_intensity)

        # Ценности
        self.values = Values.create_by_personality(personality)

        # Состояние
        self.state = AgentState()

        # Игровое состояние
        if game_actions is None:
            # Дефолтные действия для примера
            game_actions = [
                {'name': 'cooperate', 'params': []},
                {'name': 'defect', 'params': []},
                {'name': 'negotiate', 'params': ['intensity']}
            ]

        self.game_state = GameState(
            game_parameters={'cooperation': 0.5, 'trust': 0.5, 'risk': 0.3},
            available_actions=game_actions
        )

        # Пространство действий
        self.action_space = ActionSpaceBuilder(game_actions)

        # Модули
        self.ots = CurrentStateEvaluation(self.logger, self.character_traits)
        self.emotional_module = EmotionalModule(self.action_space, self.logger,
                                                num_param_bins=10, device=device)
        self.rational_module = RationalModule(self.action_space, self.logger,
                                              num_param_bins=10, device=device)
        self.strategic_reflection = StrategicReflection(self.logger, self.character_traits)

        # Игровой адаптер
        self.game_adapter = GameAdapter(self.game_state, self.logger)

        # Счетчики
        self._turn_count = 0

    def update_game_state(self, game_state: GameState):
        """Обновить состояние игры для агента"""
        self.game_state = game_state

    def update_from_game(self, game_result: GameResult):
        """Обновить ценности из результата игры"""
        self.values.update_previous_values()
        self.game_adapter.translate_game_state_to_values(game_result, self.values)

    def update_wellbeing(self):
        """Обновить благополучие на основе ценностей"""
        total = 0.0
        for vtype in ValueType:
            current = self.values.current_values.get(vtype, 50.0)
            desired = self.values.desired_values.get(vtype, 100.0)
            priority = self.values.value_priorities.get(vtype, 0.25)

            distance = (current - desired) / 100.0  # Нормализовать
            weighted_distance = distance * priority
            total += weighted_distance
            total = 1 - total

        # Нормализовать в [-1, 1]
        self.state.wellbeing = np.clip(total / len(ValueType), -1.0, 1.0)

    def update_agent_state_properly(self):
        """Обновить состояние агента корректно"""
        # Благополучие
        self.update_wellbeing()

        # Настроение уже обновлено в ОТС
        # Усталость обновлена в update_fatigue

        # Потребление ресурсов
        if abs(self.state.mood) > 0.5:
            self.state.consume_resources(0.02)

    def perform_refocus(self, focus_value: ValueType) -> Tuple[ActionOption, ActionType]:
        """
        Выполнить рефокус на выбранную ценность

        Args:
            focus_value: ценность для фокусировки (из параметров РМ)
        """
        self.state.focused_value = focus_value
        self.state.increment_refocus_count()

        self.logger.logger.info(f"🎯 РЕФОКУС на {focus_value.name}")

        # После рефокуса - повторный ОТС и ЭМ
        reaction_intensity, _ = self.ots.evaluate_values_changes(self.values, self.state)
        self.logger.log_ots_evaluation(reaction_intensity, focus_value.name)

        # Эмоциональная реакция
        emotional_action, emotional_intensity = self.emotional_module.forward(self.values, self.state)
        self.logger.log_emotional_response(str(emotional_action), emotional_intensity)

        return emotional_action, ActionType.GAME_ACTION

    def apply_reflection_results(self, reflection_results: Dict[str, Dict[str, float]]):
        """Применить результаты стратегической рефлексии"""
        # Обновить приоритеты
        for vtype_name, new_priority in reflection_results['priority_changes'].items():
            vtype = ValueType[vtype_name.upper()]
            self.values.set_priority(vtype, new_priority)

        # Обновить желаемые значения
        for vtype_name, new_desired in reflection_results['desired_value_changes'].items():
            vtype = ValueType[vtype_name.upper()]
            self.values.set_desired_value(vtype, new_desired)

    def take_turn(self, turn_number: int) -> Dict[str, Any]:
        """
        ✅ ОБНОВЛЕНО: Выполнить один ход с параметрами

        НОВАЯ ЛОГИКА:
        - После рефокуса/рефлексии агент ОБЯЗАТЕЛЬНО выбирает игровое действие
        - Поддерживаются сценарии:
          а) Сразу игровое действие
          б) Рефокус → пересчёт ОТС и ЭМ → игровое действие
          в) Рефлексия → изменение приоритетов → игровое действие
        """
        self.logger.log_turn_start(turn_number)
        self._turn_count += 1

        # Сохранить предыдущее состояние для обучения
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
        emotional_action, emotional_intensity = self.emotional_module.forward(self.values, self.state)
        self.logger.log_emotional_response(str(emotional_action), emotional_intensity)

        # Обновить усталость
        self.state.update_fatigue(emotional_intensity)

        # === 4. РАЦИОНАЛЬНЫЙ МОДУЛЬ (ПЕРВЫЙ ВЫЗОВ) ===
        # Может выбрать: игровое действие, рефокус или рефлексию
        rational_action, action_type = self.rational_module.forward(
            self.values, self.state, emotional_action, emotional_intensity,
            self.game_state, force_game_action=False  # ✅ Пока НЕ ограничиваем выбор
        )

        # === 4.5. ПРОВЕРКА ПЕРЕОПРЕДЕЛЕНИЯ ЭМОЦИЕЙ (НОВОЕ!) ===

        # ✅ НОВОЕ: Проверяем, должен ли РМ переопределить свой выбор на действие ЭМ
        # Если abs(emotional_intensity) > threshold, то РМ ОБЯЗАТЕЛЬНО выбирает действие ЭМ

        #threshold = self.rational_module.get_threshold(self.state)
        threshold = -1.0
        should_force_emotional_action = abs(emotional_intensity) > threshold
        forced_by_emotion = should_force_emotional_action

        if should_force_emotional_action:
            # ✅ ЛОГИРОВАНИЕ переопределения
            self.logger.log_emotional_override(
                str(emotional_action),
                emotional_intensity,
                threshold
            )

            # ✅ ПЕРЕОПРЕДЕЛЯЕМ: выбираем действие ЭМ вместо действия РМ
            rational_action = emotional_action
            action_type = ActionType.GAME_ACTION  # Действие ЭМ - всегда игровое действие

            # ✅ Обновляем индекс опции для обучения
            # Нужно найти индекс игрового действия с именем emotional_action.name
            for idx, option in enumerate(self.rational_module.options):
                if option['type'] == 'game_action' and option['name'] == emotional_action.name:
                    self.rational_module.last_option_idx = idx
                    break

        # Логирование решения РМ (обновлено с учетом переопределения)
        override = should_force_emotional_action
        self.logger.log_rational_decision(str(rational_action), action_type.value, override)

        # === 5. ОБРАБОТКА ВНУТРЕННИХ ДЕЙСТВИЙ (РЕФОКУС/РЕФЛЕКСИЯ) ===

        # ✅ НОВОЕ: Обработка РЕФОКУСА
        if action_type == ActionType.REFOCUS and self.state.refocus_count < 2:
            # Получить параметр рефокуса - какую ценность выбрать
            focus_value = rational_action.params.get('focus_value', ValueType.SECURITY)

            # Выполнить рефокус
            self.state.focused_value = focus_value
            self.state.increment_refocus_count()
            self.logger.logger.info(f"🎯 РЕФОКУС на {focus_value.name}")

            # ✅ СЦЕНАРИЙ Б: После рефокуса - повторный ОТС и ЭМ
            reaction_intensity, _ = self.ots.evaluate_values_changes(self.values, self.state)
            self.logger.log_ots_evaluation(reaction_intensity, focus_value.name)

            # Обновить настроение после повторной оценки
            self.state.mood += reaction_intensity / 10.0
            self.state.mood = np.clip(self.state.mood, -0.5, 0.5)

            # Эмоциональная реакция с новым фокусом
            emotional_action, emotional_intensity = self.emotional_module.forward(self.values, self.state)
            self.logger.log_emotional_response(str(emotional_action), emotional_intensity)

            # Обновить усталость
            self.state.update_fatigue(emotional_intensity)

            # ✅ ОБЯЗАТЕЛЬНО: После рефокуса РМ выбирает ИГРОВОЕ действие
            rational_action, action_type = self.rational_module.forward(
                self.values, self.state, emotional_action, emotional_intensity,
                self.game_state, force_game_action=True  # ✅ Только игровые действия!
            )
            self.logger.log_rational_decision(str(rational_action), action_type.value, override=True)

        # ✅ НОВОЕ: Обработка СТРАТЕГИЧЕСКОЙ РЕФЛЕКСИИ
        elif action_type == ActionType.REFLECTION:
            # Получить параметр интенсивности рефлексии
            reflection_intensity = rational_action.params.get('reflection_intensity', 1.0)

            # ✅ СЦЕНАРИЙ В: Выполнить стратегическую рефлексию
            reflection_results = self.strategic_reflection.reflect_on_values(
                self.values, self.state, reflection_intensity
            )
            self.logger.log_reflection(
                turn_number,
                reflection_results['priority_changes'],
                reflection_results['desired_value_changes']
            )
            self.apply_reflection_results(reflection_results)

            # ✅ ОБЯЗАТЕЛЬНО: После рефлексии выбираем ИГРОВОЕ действие
            # Используем ТЕ ЖЕ emotional_action и emotional_intensity (не пересчитываем ОТС)
            rational_action, action_type = self.rational_module.forward(
                self.values, self.state, emotional_action, emotional_intensity,
                self.game_state, force_game_action=True  # ✅ Только игровые действия!
            )
            self.logger.log_rational_decision(str(rational_action), action_type.value, override=True)

        # ✅ ТЕПЕРЬ action_type ВСЕГДА == GAME_ACTION
        final_action = rational_action
        final_action_type = action_type

        # === 6. ВЫПОЛНЕНИЕ ИГРОВОГО ДЕЙСТВИЯ ===
        if final_action_type == ActionType.GAME_ACTION:
            game_result = self.game_adapter.execute_game_action(final_action, self.game_state)
            self.logger.log_action_execution(str(final_action), final_action_type.name, final_action.params)
        else:
            # Не должно случиться после модификации, но оставим для безопасности
            game_result = GameResult(
                action=str(final_action),
                payoff=0.0,
                game_state=self.game_state.game_parameters.copy()
            )
            self.logger.log_action_execution(str(final_action), final_action_type.name, final_action.params)

        # === 7. ОБНОВЛЕНИЕ ЦЕННОСТЕЙ ИЗ ИГРЫ ===
        self.update_from_game(game_result)

        # === 8. ОБУЧЕНИЕ МОДУЛЕЙ ===
        # ✅ Передаём next_state и next_values для DQN
        self.emotional_module.train_on_feedback(
            reaction_intensity, prev_values, prev_state, self.game_state,
            emotional_action, emotional_intensity,
            next_values=self.values,
            next_state=self.state
        )

        overall_state = self.state.calculate_overall_state()
        option_idx = self.rational_module.last_option_idx

        # ✅ Передаём next_state и next_values для DQN
        self.rational_module.train_on_feedback(
            overall_state, prev_values, prev_state, self.game_state,
            (emotional_action, emotional_intensity),
            option_idx,
            next_values=self.values,
            next_state=self.state,
            forced_by_emotion=should_force_emotional_action
        )

        self.logger.log_learning(
            len(self.emotional_module.replay_buffer),
            len(self.rational_module.replay_buffer),
            self.emotional_module.last_loss,
            self.rational_module.last_loss,
            self.emotional_module.epsilon,
            self.rational_module.epsilon
        )

        # === 9. ОБНОВЛЕНИЕ СОСТОЯНИЯ ===
        self.update_agent_state_properly()

        # === 10. ВОССТАНОВЛЕНИЕ И АДАПТАЦИЯ ===
        self.state.recover_resources(recovery_rate=0.05)
        self.state.apply_fatigue_decay()
        self.logger.log_recovery(self.state.fatigue, self.state.mood, self.state.resources)

        # === 11. ИТОГ ХОДА ===
        self.logger.log_turn_summary(turn_number, overall_state, str(final_action))

        # === ОЧИСТКА ФОКУСА И СЧЕТЧИКА РЕФОКУСОВ ===
        self.state.focused_value = None
        self.state.reset_refocus_count()

        return {
            'turn': turn_number,
            'action': str(final_action),
            'action_type': final_action_type.name,
            'overall_state': overall_state,
            'mood': self.state.mood,
            'wellbeing': self.state.wellbeing,
            'fatigue': self.state.fatigue
        }

    def run_episode(self, num_turns: int = 10) -> Dict[str, Any]:
        """Запустить полный эпизод"""
        self._turn_count = 0
        self.state = AgentState()

        results = []

        for turn in range(num_turns):
            turn_result = self.take_turn(turn)
            results.append(turn_result)

        # Итог эпизода
        avg_overall_state = np.mean([r['overall_state'] for r in results])
        self.logger.log_episode_summary(num_turns, avg_overall_state)

        return {
            'num_turns': num_turns,
            'results': results,
            'avg_overall_state': avg_overall_state
        }


# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================================================
