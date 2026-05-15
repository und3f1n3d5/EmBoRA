#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ГЛАВНЫЙ МОДУЛЬ ИНТЕРАКТИВНОЙ СИМУЛЯЦИИ АГЕНТОВ
===============================================

📋 ОПИСАНИЕ:
Интерактивная система для запуска симуляций различных типов агентов
в игровых сценариях. Поддерживает выбор игры, типа агента, параметров
личности и стратегий.

🎮 ПОДДЕРЖИВАЕМЫЕ ИГРЫ:
1. Prisoners Dilemma - Итеративная дилемма заключенных (100+ ходов)
2. Battle of the Sexes - Игра координации (100+ ходов)
3. Ultimatum Game - Игра справедливости (100+ раундов)

🤖 ТИПЫ АГЕНТОВ:
1. Эмоционально-рациональный (agent_fixed.py)
   - Использует два DQN модуля (ЭМ и РМ)
   - Поддерживает переопределение действий при высокой эмоциональности

2. Чисто эмоциональный (emotional_agent.py)
   - Только эмоциональный модуль DQN
   - Реагирует на изменения ценностей

3. Чисто рациональный (rational_new.py)
   - Только рациональный модуль DQN
   - Максимизирует выигрыш игры

4. С фиксированной стратегией (fixed_strategy_agent.py)
   - Фиксированная стратегия + эмоциональный модуль
   - 3 стратегии: Always Cooperate, Always Defect, Tit-for-Tat

🎭 ПАРАМЕТРЫ ЛИЧНОСТИ:
- Personality: OPTIMISTIC, PESSIMISTIC, NEUTRAL
- Emotional Intensity: HIGH, LOW, NEUTRAL

📊 ВОЗМОЖНОСТИ:
✓ Интерактивный выбор всех параметров
✓ Логирование полной симуляции
✓ Итоговая статистика
✓ Поддержка всех типов агентов
✓ Гибкая система создания агентов

✅ ПРОЦЕСС ЗАПУСКА:
1. Выбрать игру
2. Выбрать количество раундов
3. Сконфигурировать Агента 1
   - Тип агента
   - Имя
   - Параметры (если применимо)
4. Сконфигурировать Агента 2
   - Тип агента
   - Имя
   - Параметры (если применимо)
5. Запустить симуляцию

🔍 СОПОСТАВЛЕНИЕ ФУНКЦИЙ И ПЕРЕМЕННЫХ:
Все функции и переменные между файлами согласованы:
✓ GameState - одинаковая структура во всех модулях
✓ GameResult - используется для передачи результатов
✓ LogLevel - единые уровни логирования
✓ ValueType, PersonalityType, EmotionalIntensityType - согласованные enum'ы
✓ Agent.take_turn() - единый интерфейс для всех типов агентов
✓ Agent.update_from_game() - передача результатов игры

Автор: AI Assistant
Дата: 2026-02-21
Версия: 1.0
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import importlib
import importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


# ════════════════════════════════════════════════════════════════════════════════
# ИМПОРТ МОДУЛЕЙ АГЕНТОВ (ДИНАМИЧЕСКИЙ)
# ════════════════════════════════════════════════════════════════════════════════

_MODULE_CACHE: Dict[str, Any] = {}


def import_agent_module(module_name: str):
    """Динамический импорт модуля агента с поддержкой файлов вида name.py и name (n).py"""
    if module_name in _MODULE_CACHE:
        return _MODULE_CACHE[module_name]

    try:
        module = importlib.import_module(module_name)
        _MODULE_CACHE[module_name] = module
        return module
    except ImportError:
        pass

    base_dir = Path(__file__).resolve().parent
    candidate_paths = [base_dir / f"{module_name}.py"]
    candidate_paths.extend(sorted(base_dir.glob(f"{module_name} (*.py")))

    for candidate in candidate_paths:
        if not candidate.exists():
            continue
        try:
            safe_module_name = f"{module_name}__dynamic"
            spec = importlib.util.spec_from_file_location(safe_module_name, candidate)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[safe_module_name] = module
            spec.loader.exec_module(module)
            _MODULE_CACHE[module_name] = module
            return module
        except Exception as e:
            print(f"❌ Ошибка импорта модуля {module_name} из файла {candidate.name}: {e}")

    print(f"❌ Не удалось найти модуль {module_name} рядом с main.py")
    return None


# Попытаемся импортировать базовые классы из доступных модулей
_base_module = import_agent_module('agent_fixed') or import_agent_module('emotional_agent')

if _base_module is not None:
    GameState = _base_module.GameState
    GameResult = _base_module.GameResult
    ActionOption = _base_module.ActionOption
    LogLevel = _base_module.LogLevel
    ValueType = _base_module.ValueType
    PersonalityType = _base_module.PersonalityType
    EmotionalIntensityType = _base_module.EmotionalIntensityType
else:
    print("⚠️ Используем локальные определения базовых классов")

    class LogLevel:
        """Уровни логирования"""
        SILENT = 50
        MINIMAL = 40
        NORMAL = 30
        VERBOSE = 20
        DEBUG = 10

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
    class GameResult:
        """Результат игрового действия"""
        action: str
        payoff: float
        game_state: Dict[str, float]

        def to_dict(self) -> Dict[str, Any]:
            return {
                'action': self.action,
                'payoff': self.payoff,
                'game_state': self.game_state,
            }

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


# ════════════════════════════════════════════════════════════════════════════════
# ИГРОВЫЕ КЛАССЫ
# ════════════════════════════════════════════════════════════════════════════════

class BaseGame:
    """Базовый класс для всех игр"""

    def __init__(self, game_name: str):
        self.game_name = game_name
        self.round = 0
        self.history = []
        self.payoffs = [0.0, 0.0]
        self.current_state = {}

    def parse_action(self, action_str: str) -> Tuple[str, Dict]:
        """
        Парсит строку действия вида 'action_name(param1=value1, param2=value2)'
        Возвращает (action_name, params_dict)
        """
        if '(' not in action_str:
            return action_str, {}

        action_name = action_str.split('(')[0].strip()
        params_str = action_str.split('(')[1].rstrip(')')
        params = {}

        if params_str:
            for param in params_str.split(','):
                if '=' in param:
                    key, value = param.split('=')
                    key = key.strip()
                    value_str = value.strip()
                    try:
                        if '.' in value_str:
                            params[key] = float(value_str)
                        else:
                            params[key] = int(value_str)
                    except (ValueError, TypeError):
                        params[key] = value_str

        return action_name, params

    def get_game_state(self, agent_id: int) -> GameState:
        """Получить состояние игры для агента"""
        raise NotImplementedError

    def execute_round(self, action1: str, action2: str) -> Tuple[float, float]:
        """Выполнить раунд игры. Возвращает выигрыши (payoff1, payoff2)"""
        raise NotImplementedError

    def get_summary(self) -> Dict:
        """Получить итоговую статистику игры"""
        raise NotImplementedError


class PrisonersDilemmaGame(BaseGame):
    """Итеративная дилемма заключенных (IPD)"""

    PAYOFFS = {
        ('cooperate', 'cooperate'): (3, 3),
        ('cooperate', 'defect'): (0, 5),
        ('defect', 'cooperate'): (5, 0),
        ('defect', 'defect'): (1, 1),
    }

    def __init__(self):
        super().__init__("Prisoners Dilemma")
        self.current_state = {
            'cooperation_level': 50.0,
            'current_payoff': 2.0,
            'equality_level': 50.0,
            'security_level': 50.0,
        }

    def get_game_state(self, agent_id: int) -> GameState:
        """Получить состояние игры для агента"""
        return GameState(game_parameters=self.current_state.copy())

    def execute_round(self, action1: str, action2: str) -> Tuple[float, float]:
        """Выполнить раунд игры"""
        act1_name, act1_params = self.parse_action(action1)
        act2_name, act2_params = self.parse_action(action2)

        action1_normalized = 'cooperate' if 'cooperate' in act1_name.lower() else 'defect'
        action2_normalized = 'cooperate' if 'cooperate' in act2_name.lower() else 'defect'

        payoff1, payoff2 = self.PAYOFFS[(action1_normalized, action2_normalized)]

        self.payoffs[0] += payoff1
        self.payoffs[1] += payoff2

        cooperation_count = sum(1 for h in self.history if h[0] == 'cooperate' or h[1] == 'cooperate')
        cooperation_count += (1 if action1_normalized == 'cooperate' else 0) + (1 if action2_normalized == 'cooperate' else 0)

        self.current_state['cooperation_level'] = min(100.0, (cooperation_count / (self.round * 2 + 2)) * 100)
        self.current_state['current_payoff'] = (self.payoffs[0] + self.payoffs[1]) / 2
        self.current_state['equality_level'] = 100.0 - min(abs(self.payoffs[0] - self.payoffs[1]), 100.0)
        self.current_state['security_level'] = 50.0 + min(min(self.payoffs[0], self.payoffs[1]) / 5, 50.0)

        self.history.append((action1_normalized, action2_normalized, payoff1, payoff2))
        self.round += 1

        return float(payoff1), float(payoff2)

    def get_summary(self) -> Dict:
        """Получить итоговую статистику игры"""
        return {
            'total_rounds': self.round,
            'agent1_total_payoff': self.payoffs[0],
            'agent2_total_payoff': self.payoffs[1],
            'agent1_avg_payoff': self.payoffs[0] / max(1, self.round),
            'agent2_avg_payoff': self.payoffs[1] / max(1, self.round),
            'cooperation_rate_agent1': sum(1 for h in self.history if h[0] == 'cooperate') / max(1, self.round),
            'cooperation_rate_agent2': sum(1 for h in self.history if h[1] == 'cooperate') / max(1, self.round),
        }


class BattleOfSexesGame(BaseGame):
    """Battle of the Sexes - игра координации"""

    PAYOFFS = {
        ('opera', 'opera'): (3, 2),
        ('opera', 'fight'): (0, 0),
        ('fight', 'opera'): (0, 0),
        ('fight', 'fight'): (2, 3),
    }

    def __init__(self):
        super().__init__("Battle of Sexes")
        self.current_state = {
            'agreement_level': 50.0,
            'current_payoff': 1.25,
            'preference_difference': 50.0,
            'mutual_satisfaction': 50.0,
        }

    def get_game_state(self, agent_id: int) -> GameState:
        """Получить состояние игры для агента"""
        return GameState(game_parameters=self.current_state.copy())

    def execute_round(self, action1: str, action2: str) -> Tuple[float, float]:
        """Выполнить раунд игры"""
        act1_name, act1_params = self.parse_action(action1)
        act2_name, act2_params = self.parse_action(action2)

        action1_normalized = 'opera' if 'opera' in act1_name.lower() else 'fight'
        action2_normalized = 'opera' if 'opera' in act2_name.lower() else 'fight'

        payoff1, payoff2 = self.PAYOFFS[(action1_normalized, action2_normalized)]

        self.payoffs[0] += payoff1
        self.payoffs[1] += payoff2

        agreements = sum(1 for h in self.history if h[0] == h[1])
        agreements += (1 if action1_normalized == action2_normalized else 0)

        self.current_state['agreement_level'] = (agreements / (self.round + 1)) * 100
        self.current_state['current_payoff'] = (self.payoffs[0] + self.payoffs[1]) / 2
        self.current_state['preference_difference'] = 100.0 - min(abs(self.payoffs[0] - self.payoffs[1]) * 10, 100.0)
        self.current_state['mutual_satisfaction'] = min((self.payoffs[0] + self.payoffs[1]) / 3 * 10, 100.0)

        self.history.append((action1_normalized, action2_normalized, payoff1, payoff2))
        self.round += 1

        return float(payoff1), float(payoff2)

    def get_summary(self) -> Dict:
        """Получить итоговую статистику игры"""
        return {
            'total_rounds': self.round,
            'agent1_total_payoff': self.payoffs[0],
            'agent2_total_payoff': self.payoffs[1],
            'agent1_avg_payoff': self.payoffs[0] / max(1, self.round),
            'agent2_avg_payoff': self.payoffs[1] / max(1, self.round),
            'agreement_rate': sum(1 for h in self.history if h[0] == h[1]) / max(1, self.round),
            'agent1_preference_opera': sum(1 for h in self.history if h[0] == 'opera') / max(1, self.round),
            'agent2_preference_fight': sum(1 for h in self.history if h[1] == 'fight') / max(1, self.round),
        }


class UltimatumGame(BaseGame):
    """Ultimatum Game - игра справедливости"""

    def __init__(self):
        super().__init__("Ultimatum Game")
        self.initial_endowment = 10.0
        self.current_state = {
            'fairness_level': 50.0,
            'current_payoff': 5.0,
            'trust_level': 50.0,
            'inequality_aversion': 50.0,
        }

    def get_game_state(self, agent_id: int) -> GameState:
        """Получить состояние игры для агента"""
        return GameState(game_parameters=self.current_state.copy())

    def execute_round(self, action1: str, action2: str) -> Tuple[float, float]:
        """Выполнить раунд игры"""
        act1_name, act1_params = self.parse_action(action1)
        act2_name, act2_params = self.parse_action(action2)

        offer = act1_params.get('offer', self.initial_endowment / 2)
        offer = max(0, min(self.initial_endowment, float(offer)))

        accept = 'accept' in act2_name.lower()

        if accept:
            payoff1 = self.initial_endowment - offer
            payoff2 = offer
        else:
            payoff1 = 0
            payoff2 = 0

        self.payoffs[0] += payoff1
        self.payoffs[1] += payoff2

        accepted_count = sum(1 for h in self.history if h[3] == 1)
        accepted_count += (1 if accept else 0)

        fair_offers = sum(1 for h in self.history if abs(h[2] - (self.initial_endowment / 2)) < 1.0)
        fair_offers += (1 if abs(offer - (self.initial_endowment / 2)) < 1.0 else 0)

        self.current_state['fairness_level'] = (fair_offers / (self.round + 1)) * 100
        self.current_state['current_payoff'] = (self.payoffs[0] + self.payoffs[1]) / 2
        self.current_state['trust_level'] = (accepted_count / (self.round + 1)) * 100
        self.current_state['inequality_aversion'] = 100.0 - min(abs(self.payoffs[0] - self.payoffs[1]) * 2, 100.0)

        self.history.append((act1_name, act2_name, offer, 1 if accept else 0))
        self.round += 1

        return float(payoff1), float(payoff2)

    def get_summary(self) -> Dict:
        """Получить итоговую статистику игры"""
        return {
            'total_rounds': self.round,
            'agent1_total_payoff': self.payoffs[0],
            'agent2_total_payoff': self.payoffs[1],
            'agent1_avg_payoff': self.payoffs[0] / max(1, self.round),
            'agent2_avg_payoff': self.payoffs[1] / max(1, self.round),
            'acceptance_rate': sum(1 for h in self.history if h[3] == 1) / max(1, self.round),
            'avg_offer': sum(h[2] for h in self.history) / max(1, self.round),
            'fair_offer_rate': sum(1 for h in self.history if abs(h[2] - (self.initial_endowment / 2)) < 1.0) / max(1, self.round),
        }


# ════════════════════════════════════════════════════════════════════════════════
# ЛОГИРОВАНИЕ
# ════════════════════════════════════════════════════════════════════════════════

class SimulationLogger:
    """Логирование симуляции"""

    @staticmethod
    def log_simulation_start(game: BaseGame, agent1_name: str, agent2_name: str, total_rounds: int):
        """Логирование начала симуляции"""
        print("\n" + "=" * 100)
        print(f"🎮 НАЧАЛО СИМУЛЯЦИИ: {game.game_name.upper()}")
        print("=" * 100)
        print(f"\n👥 АГЕНТЫ:")
        print(f" 1️⃣ {agent1_name}")
        print(f" 2️⃣ {agent2_name}")
        print(f"\n⏱️ ПАРАМЕТРЫ:")
        print(f" • Всего ходов: {total_rounds}")
        print(f" • Игра: {game.game_name}")
        print("\n" + "-" * 100 + "\n")

    @staticmethod
    def log_round(round_num: int, agent1_name: str, agent2_name: str,
                  action1: str, action2: str, payoff1: float, payoff2: float,
                  total1: float, total2: float):
        """Логировать раунд"""
        action1_short = action1[:25] if len(action1) > 25 else action1
        action2_short = action2[:25] if len(action2) > 25 else action2

        print(f"ХОД {round_num:3d}: {agent1_name:15} → {action1_short:25} | "
              f"Выигрыш: {payoff1:+5.1f} (всего: {total1:6.1f}) || "
              f"{agent2_name:15} → {action2_short:25} | "
              f"Выигрыш: {payoff2:+5.1f} (всего: {total2:6.1f})")

    @staticmethod
    def log_simulation_end(game: BaseGame, game_summary: Dict):
        """Логирование конца симуляции"""
        print("\n" + "=" * 100)
        print("🏁 КОНЕЦ СИМУЛЯЦИИ")
        print("=" * 100)
        print(f"\n📊 ИГРОВЫЕ РЕЗУЛЬТАТЫ:")
        print(f" • Всего раундов: {game_summary['total_rounds']}")
        print(f" • Агент 1 - Всего выигрышей: {game_summary['agent1_total_payoff']:.1f} "
              f"(среднее за ход: {game_summary['agent1_avg_payoff']:.2f})")
        print(f" • Агент 2 - Всего выигрышей: {game_summary['agent2_total_payoff']:.1f} "
              f"(среднее за ход: {game_summary['agent2_avg_payoff']:.2f})")

    @staticmethod
    def log_agent_final_state(agent_name: str, agent: Any, game_payoff: float):
        """Логировать итоговое состояние агента"""
        print(f"\n{'=' * 100}")
        print(f"🧠 ИТОГОВОЕ СОСТОЯНИЕ: {agent_name}")
        print(f"{'=' * 100}")
        print(f"\n🎮 ИГРОВЫЕ МЕТРИКИ:")
        print(f" • Выигрыш в игре: {game_payoff:.1f}")

        state = get_agent_state_container(agent)
        if state is not None:
            print(f"\n💭 ВНУТРЕННЕЕ СОСТОЯНИЕ:")
            print(f" • Благополучие: {float(getattr(state, 'wellbeing', 0.0)):.3f}")
            print(f" • Настроение: {float(getattr(state, 'mood', 0.0)):+.3f}")
            print(f" • Усталость: {float(getattr(state, 'fatigue', 0.0)):.3f}")
            print(f" • Ресурсы: {float(getattr(state, 'resources', 0.0)):.3f}")
            if hasattr(state, 'calculate_overall_state'):
                print(f" • Общее состояние: {float(state.calculate_overall_state()):.3f}")
            elif hasattr(agent, 'calculate_overall_state'):
                print(f" • Общее состояние: {float(agent.calculate_overall_state()):.3f}")

        if hasattr(agent, 'character_traits') and agent.character_traits:
            print(f"\n🎭 ЧЕРТЫ ЛИЧНОСТИ:")
            personality = getattr(agent.character_traits, 'personality', None)
            intensity = getattr(agent.character_traits, 'intensity', None)
            if personality is not None:
                print(f" • Тип личности: {personality.name if hasattr(personality, 'name') else personality}")
            if intensity is not None:
                print(f" • Интенсивность эмоций: {intensity.name if hasattr(intensity, 'name') else intensity}")

        em_buffer_size = 0
        rm_buffer_size = 0

        if hasattr(agent, 'emotional_module') and agent.emotional_module and hasattr(agent.emotional_module, 'replay_buffer'):
            em_buffer_size = len(agent.emotional_module.replay_buffer)
        if hasattr(agent, 'rational_module') and agent.rational_module and hasattr(agent.rational_module, 'replay_buffer'):
            rm_buffer_size = len(agent.rational_module.replay_buffer)
        if hasattr(agent, 'dqn_module') and agent.dqn_module and hasattr(agent.dqn_module, 'replay_buffer'):
            rm_buffer_size = len(agent.dqn_module.replay_buffer)

        print(f"\n📚 СТАТИСТИКА ОБУЧЕНИЯ:")
        print(f" • Буфер памяти ЭМ (DQN): {em_buffer_size} событий")
        print(f" • Буфер памяти РМ (DQN): {rm_buffer_size} событий")
# ════════════════════════════════════════════════════════════════════════════════
# ИНТЕРАКТИВНОЕ МЕНЮ
# ════════════════════════════════════════════════════════════════════════════════

class InteractiveMenu:
    """Интерактивное меню для выбора параметров"""

    @staticmethod
    def choose_game() -> Tuple[BaseGame, str]:
        """Выбор игры"""
        print("\n" + "=" * 100)
        print("🎮 ВЫБОР ИГРЫ")
        print("=" * 100)
        print("\n1. Prisoners Dilemma (Дилемма заключенных)")
        print("2. Battle of Sexes (Битва полов)")
        print("3. Ultimatum Game (Ультиматум)")

        while True:
            choice = input("\nВыберите игру (1-3): ").strip()
            if choice == "1":
                return PrisonersDilemmaGame(), "Prisoners Dilemma"
            elif choice == "2":
                return BattleOfSexesGame(), "Battle of Sexes"
            elif choice == "3":
                return UltimatumGame(), "Ultimatum Game"
            else:
                print("❌ Неверный выбор. Пожалуйста, выберите 1, 2 или 3.")

    @staticmethod
    def choose_agent_type() -> str:
        """Выбор типа агента"""
        print("\n1. Эмоционально-рациональный (agent_fixed)")
        print("2. Чисто эмоциональный (emotional_agent)")
        print("3. Чисто рациональный (rational_new)")
        print("4. С фиксированной стратегией (fixed_strategy_agent)")

        while True:
            choice = input("\nВыберите тип агента (1-4): ").strip()
            if choice == "1":
                return "emotional_rational"
            elif choice == "2":
                return "emotional"
            elif choice == "3":
                return "rational"
            elif choice == "4":
                return "fixed_strategy"
            else:
                print("❌ Неверный выбор. Пожалуйста, выберите 1-4.")

    @staticmethod
    def choose_personality() -> str:
        """Выбор типа личности"""
        print("\n1. Оптимистичный (OPTIMISTIC)")
        print("2. Пессимистичный (PESSIMISTIC)")
        print("3. Нейтральный (NEUTRAL)")

        while True:
            choice = input("\nВыберите тип личности (1-3): ").strip()
            if choice == "1":
                return "optimistic"
            elif choice == "2":
                return "pessimistic"
            elif choice == "3":
                return "neutral"
            else:
                print("❌ Неверный выбор.")

    @staticmethod
    def choose_intensity() -> str:
        """Выбор интенсивности эмоций"""
        print("\n1. Высокая (HIGH)")
        print("2. Низкая (LOW)")
        print("3. Нейтральная (NEUTRAL)")

        while True:
            choice = input("\nВыберите интенсивность (1-3): ").strip()
            if choice == "1":
                return "high"
            elif choice == "2":
                return "low"
            elif choice == "3":
                return "neutral"
            else:
                print("❌ Неверный выбор.")

    @staticmethod
    def choose_fixed_strategy() -> str:
        """Выбор фиксированной стратегии"""
        print("\n1. Всегда сотрудничать (ALWAYS_COOPERATE)")
        print("2. Всегда предавать (ALWAYS_DEFECT)")
        print("3. Ответное действие (TIT_FOR_TAT)")

        while True:
            choice = input("\nВыберите стратегию (1-3): ").strip()
            if choice == "1":
                return "always_cooperate"
            elif choice == "2":
                return "always_defect"
            elif choice == "3":
                return "tit_for_tat"
            else:
                print("❌ Неверный выбор.")

    @staticmethod
    def choose_rounds() -> int:
        """Выбор количества раундов"""
        while True:
            try:
                rounds = int(input("\nВведите количество раундов (по умолчанию 100): ").strip() or "100")
                if rounds > 0:
                    return rounds
                else:
                    print("❌ Количество раундов должно быть положительным.")
            except ValueError:
                print("❌ Пожалуйста, введите целое число.")


# ════════════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ СОВМЕСТИМОСТИ АГЕНТОВ И ГРАФИКОВ
# ════════════════════════════════════════════════════════════════════════════════


def get_agent_state_container(agent: Any) -> Optional[Any]:
    """Получить объект внутреннего состояния агента вне зависимости от реализации"""
    state = getattr(agent, 'state', None)
    if state is not None:
        return state

    state = getattr(agent, 'agent_state', None)
    if state is not None:
        return state

    return None


def get_agent_name(agent: Any, fallback: str) -> str:
    """Получить отображаемое имя агента"""
    return getattr(agent, 'name', fallback)


def prepare_agent_for_simulation(agent: Any, name: str) -> Any:
    """Привести интерфейс агента к общему виду, не изменяя код модулей агентов"""
    if agent is None:
        return None

    if not hasattr(agent, 'name'):
        agent.name = name

    state = get_agent_state_container(agent)
    if state is not None and not hasattr(agent, 'state'):
        agent.state = state

    if hasattr(agent, 'logger') and agent.logger is not None:
        if not hasattr(agent.logger, 'log_action_execution'):
            agent.logger.log_action_execution = lambda *args, **kwargs: None
        if getattr(agent.logger, 'log_level', None) == LogLevel.SILENT and hasattr(agent.logger, 'logger'):
            agent.logger.logger.disabled = True

    if hasattr(agent, 'emotional_module') and hasattr(agent.emotional_module, 'forward') and not getattr(agent, '_emotion_tracking_installed', False):
        original_forward = agent.emotional_module.forward

        def tracked_forward(*args, **kwargs):
            result = original_forward(*args, **kwargs)
            try:
                if isinstance(result, tuple) and len(result) >= 2:
                    agent._last_emotion_value = float(result[1])
                    agent._last_emotion_action = str(result[0])
            except Exception:
                pass
            return result

        agent.emotional_module.forward = tracked_forward
        agent._emotion_tracking_installed = True

    if not hasattr(agent, '_last_emotion_value'):
        agent._last_emotion_value = 0.0

    return agent


def update_agent_game_state(agent: Any, game_state: GameState):
    """Обновить игровое состояние агента с учетом разных интерфейсов"""
    if hasattr(agent, 'update_game_state'):
        agent.update_game_state(game_state)
    elif hasattr(agent, 'game_state'):
        agent.game_state = game_state


def extract_action_from_turn_result(turn_result: Any) -> str:
    """Извлечь строковое представление действия из результата хода"""
    if isinstance(turn_result, dict):
        return str(turn_result.get('action', 'cooperate'))

    if isinstance(turn_result, tuple) and len(turn_result) >= 1:
        return str(turn_result[0])

    return str(turn_result)


def execute_agent_turn(agent: Any, turn_number: int, game_state: GameState) -> Tuple[str, Dict[str, Any]]:
    """Выполнить ход агента и привести результат к единому словарному формату"""
    if hasattr(agent, 'take_turn'):
        turn_result = agent.take_turn(turn_number)
        action = extract_action_from_turn_result(turn_result)
        if isinstance(turn_result, dict):
            result_dict = dict(turn_result)
        else:
            result_dict = {'turn': turn_number, 'action': action}
        result_dict.setdefault('action', action)
        result_dict.setdefault('turn', turn_number)
        return action, result_dict

    if hasattr(agent, 'make_action'):
        action_obj, action_type, info = agent.make_action(game_state)
        action = str(action_obj)
        result_dict = {'turn': turn_number, 'action': action, 'action_type': str(action_type)}
        if isinstance(info, dict):
            result_dict.update(info)
        result_dict.setdefault('action', action)
        result_dict.setdefault('turn', turn_number)
        return action, result_dict

    return 'cooperate', {'turn': turn_number, 'action': 'cooperate'}


def collect_agent_metrics(agent: Any, turn_result: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """Собрать метрики состояния агента для построения графиков"""
    state = get_agent_state_container(agent)

    wellbeing = float(getattr(state, 'wellbeing', 0.0)) if state is not None else 0.0
    mood = float(getattr(state, 'mood', 0.0)) if state is not None else 0.0
    fatigue = float(getattr(state, 'fatigue', 0.0)) if state is not None else 0.0

    if turn_result:
        wellbeing = float(turn_result.get('wellbeing', wellbeing))
        mood = float(turn_result.get('mood', mood))
        fatigue = float(turn_result.get('fatigue', fatigue))

    if state is not None and hasattr(state, 'calculate_overall_state'):
        overall_state = float(state.calculate_overall_state())
    elif hasattr(agent, 'calculate_overall_state'):
        overall_state = float(agent.calculate_overall_state())
    else:
        overall_state = float(wellbeing + mood - fatigue)

    if turn_result and 'overall_state' in turn_result:
        overall_state = float(turn_result['overall_state'])

    emotion = float(getattr(agent, '_last_emotion_value', 0.0))
    if turn_result:
        if 'emotional_intensity' in turn_result:
            emotion = float(turn_result['emotional_intensity'])
        elif 'em_intensity' in turn_result:
            emotion = float(turn_result['em_intensity'])

    return {
        'emotion': emotion,
        'mood': mood,
        'fatigue': fatigue,
        'wellbeing': wellbeing,
        'overall_state': overall_state,
    }


def plot_agent_metrics(ax, turns: List[int], metrics_history: List[Dict[str, float]], agent_name: str):
    """Построить график метрик одного агента"""
    ax.plot(turns, [m['emotion'] for m in metrics_history], label='Эмоции')
    ax.plot(turns, [m['mood'] for m in metrics_history], label='Настроение')
    ax.plot(turns, [m['fatigue'] for m in metrics_history], label='Усталость')
    ax.plot(turns, [m['wellbeing'] for m in metrics_history], label='Благополучие')
    ax.plot(turns, [m['overall_state'] for m in metrics_history], label='Общее состояние')
    ax.set_title(f'Динамика состояния агента: {agent_name}')
    ax.set_xlabel('Номер хода')
    ax.set_ylabel('Значение')
    ax.grid(True, alpha=0.3)
    ax.legend()


def plot_simulation_results(agent1_name: str, agent2_name: str,
                            agent1_metrics_history: List[Dict[str, float]],
                            agent2_metrics_history: List[Dict[str, float]],
                            cumulative_payoffs_history: List[Tuple[float, float]]):
    """Построить итоговые графики симуляции"""
    if not agent1_metrics_history or not agent2_metrics_history or not cumulative_payoffs_history:
        print("⚠️ Недостаточно данных для построения графиков.")
        return

    turns = list(range(1, len(cumulative_payoffs_history) + 1))

    fig, axes = plt.subplots(3, 1, figsize=(14, 18), sharex=False)

    plot_agent_metrics(axes[0], turns, agent1_metrics_history, agent1_name)
    plot_agent_metrics(axes[1], turns, agent2_metrics_history, agent2_name)

    axes[2].plot(turns, [p[0] for p in cumulative_payoffs_history], label=agent1_name)
    axes[2].plot(turns, [p[1] for p in cumulative_payoffs_history], label=agent2_name)
    axes[2].set_title('Изменение суммарного выигрыша агентов')
    axes[2].set_xlabel('Номер хода')
    axes[2].set_ylabel('Суммарный выигрыш')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    plt.tight_layout()
    plt.show()


def get_game_actions_for_game(game: BaseGame) -> List[Dict[str, Any]]:
    """Получить базовое пространство игровых действий для выбранной игры"""
    if isinstance(game, PrisonersDilemmaGame):
        return [
            {'name': 'cooperate', 'params': []},
            {'name': 'defect', 'params': []},
        ]

    if isinstance(game, BattleOfSexesGame):
        return [
            {'name': 'opera', 'params': []},
            {'name': 'fight', 'params': []},
        ]

    if isinstance(game, UltimatumGame):
        return [
            {'name': 'offer', 'params': ['offer']},
            {'name': 'accept', 'params': []},
            {'name': 'reject', 'params': []},
        ]

    return [
        {'name': 'cooperate', 'params': []},
        {'name': 'defect', 'params': []},
    ]


# ════════════════════════════════════════════════════════════════════════════════
# СОЗДАНИЕ АГЕНТОВ
# ════════════════════════════════════════════════════════════════════════════════

def create_agent(agent_type: str, name: str, personality: Optional[str] = None,
                 intensity: Optional[str] = None, strategy: Optional[str] = None,
                 log_level: int = LogLevel.SILENT,
                 game_actions: Optional[List[Dict[str, Any]]] = None) -> Optional[Any]:
    """Создать агента на основе типа"""

    if agent_type == "emotional_rational":
        try:
            module = import_agent_module('agent_fixed')
            if not module:
                return None

            personality_map = {
                'optimistic': module.PersonalityType.OPTIMISTIC,
                'pessimistic': module.PersonalityType.PESSIMISTIC,
                'neutral': module.PersonalityType.NEUTRAL,
            }

            intensity_map = {
                'high': module.EmotionalIntensityType.HIGH,
                'low': module.EmotionalIntensityType.LOW,
                'neutral': module.EmotionalIntensityType.NEUTRAL,
            }

            personality_enum = personality_map.get(personality, module.PersonalityType.NEUTRAL)
            intensity_enum = intensity_map.get(intensity, module.EmotionalIntensityType.NEUTRAL)

            agent = module.Agent(
                name=name,
                personality=personality_enum,
                emotional_intensity=intensity_enum,
                log_level=log_level,
                game_actions=game_actions
            )
            return prepare_agent_for_simulation(agent, name)
        except Exception as e:
            print(f"❌ Ошибка при создании эмоционально-рационального агента: {e}")
            return None

    elif agent_type == "emotional":
        try:
            module = import_agent_module('emotional_agent')
            if not module:
                return None

            personality_map = {
                'optimistic': module.PersonalityType.OPTIMISTIC,
                'pessimistic': module.PersonalityType.PESSIMISTIC,
                'neutral': module.PersonalityType.NEUTRAL,
            }

            intensity_map = {
                'high': module.EmotionalIntensityType.HIGH,
                'low': module.EmotionalIntensityType.LOW,
                'neutral': module.EmotionalIntensityType.NEUTRAL,
            }

            personality_enum = personality_map.get(personality, module.PersonalityType.NEUTRAL)
            intensity_enum = intensity_map.get(intensity, module.EmotionalIntensityType.NEUTRAL)

            agent = module.Agent(
                name=name,
                personality=personality_enum,
                emotional_intensity=intensity_enum,
                log_level=log_level,
                game_actions=game_actions
            )
            return prepare_agent_for_simulation(agent, name)
        except Exception as e:
            print(f"❌ Ошибка при создании эмоционального агента: {e}")
            return None

    elif agent_type == "rational":
        try:
            module = import_agent_module('rational_new')
            if not module:
                return None

            personality_enum = getattr(module.PersonalityType, 'NEUTRAL', None)
            intensity_enum = getattr(module.EmotionalIntensityType, 'NEUTRAL', None)
            agent_class = getattr(module, 'Agent', None) or getattr(module, 'EmotionalRationalAgent', None)
            if agent_class is None:
                raise AttributeError("В модуле rational_new не найден класс Agent или EmotionalRationalAgent")

            agent = agent_class(
                personality=personality_enum,
                intensity=intensity_enum,
                game_actions=game_actions,
                log_level=log_level
            )
            return prepare_agent_for_simulation(agent, name)
        except Exception as e:
            print(f"❌ Ошибка при создании рационального агента: {e}")
            return None

    elif agent_type == "fixed_strategy":
        try:
            module = import_agent_module('fixed_strategy_agent')
            if not module:
                return None

            personality_map = {
                'optimistic': module.PersonalityType.OPTIMISTIC,
                'pessimistic': module.PersonalityType.PESSIMISTIC,
                'neutral': module.PersonalityType.NEUTRAL,
            }

            intensity_map = {
                'high': module.EmotionalIntensityType.HIGH,
                'low': module.EmotionalIntensityType.LOW,
                'neutral': module.EmotionalIntensityType.NEUTRAL,
            }

            strategy_map = {
                'always_cooperate': module.FixedStrategy.ALWAYS_COOPERATE,
                'always_defect': module.FixedStrategy.ALWAYS_DEFECT,
                'tit_for_tat': module.FixedStrategy.TIT_FOR_TAT,
            }

            personality_enum = personality_map.get(personality, module.PersonalityType.NEUTRAL)
            intensity_enum = intensity_map.get(intensity, module.EmotionalIntensityType.NEUTRAL)
            strategy_enum = strategy_map.get(strategy, module.FixedStrategy.ALWAYS_COOPERATE)

            action_names = [action['name'] if isinstance(action, dict) else str(action) for action in (game_actions or [])]
            agent = module.Agent(
                name=name,
                personality=personality_enum,
                emotional_intensity=intensity_enum,
                strategy=strategy_enum,
                log_level=log_level,
                game_actions=action_names or None
            )
            return prepare_agent_for_simulation(agent, name)
        except Exception as e:
            print(f"❌ Ошибка при создании агента с фиксированной стратегией: {e}")
            return None

    return None


# ════════════════════════════════════════════════════════════════════════════════
# СИМУЛЯЦИЯ
# ════════════════════════════════════════════════════════════════════════════════

def run_simulation(game: BaseGame, agent1: Any, agent2: Any, total_rounds: int):
    """Запустить симуляцию"""

    agent1_name = get_agent_name(agent1, 'Agent 1')
    agent2_name = get_agent_name(agent2, 'Agent 2')

    agent1_metrics_history: List[Dict[str, float]] = []
    agent2_metrics_history: List[Dict[str, float]] = []
    cumulative_payoffs_history: List[Tuple[float, float]] = []

    last_action1: Optional[str] = None
    last_action2: Optional[str] = None

    SimulationLogger.log_simulation_start(game, agent1_name, agent2_name, total_rounds)

    for round_num in range(1, total_rounds + 1):
        # Получаем состояние игры
        game_state1 = game.get_game_state(0)
        game_state2 = game.get_game_state(1)

        # Передаем последнюю известную реакцию оппонента, если агент ее поддерживает
        try:
            setattr(game_state1, 'opponent_last_action', last_action2)
        except Exception:
            pass
        try:
            setattr(game_state2, 'opponent_last_action', last_action1)
        except Exception:
            pass

        # Обновляем состояние игры в агентах
        update_agent_game_state(agent1, game_state1)
        update_agent_game_state(agent2, game_state2)

        # Получаем действия от агентов
        try:
            action1, action1_result = execute_agent_turn(agent1, round_num, game_state1)
        except Exception as e:
            print(f"⚠️ Ошибка при получении действия от {agent1_name}: {e}")
            action1 = 'cooperate'
            action1_result = {'turn': round_num, 'action': action1}

        try:
            action2, action2_result = execute_agent_turn(agent2, round_num, game_state2)
        except Exception as e:
            print(f"⚠️ Ошибка при получении действия от {agent2_name}: {e}")
            action2 = 'cooperate'
            action2_result = {'turn': round_num, 'action': action2}

        # Выполняем раунд игры
        payoff1, payoff2 = game.execute_round(action1, action2)

        # Обновляем агентов с результатами
        if hasattr(agent1, 'update_from_game'):
            game_result1 = GameResult(action=action1, payoff=payoff1, game_state=game.current_state.copy())
            agent1.update_from_game(game_result1)

        if hasattr(agent2, 'update_from_game'):
            game_result2 = GameResult(action=action2, payoff=payoff2, game_state=game.current_state.copy())
            agent2.update_from_game(game_result2)

        # Сохраняем данные для графиков
        agent1_metrics_history.append(collect_agent_metrics(agent1, action1_result))
        agent2_metrics_history.append(collect_agent_metrics(agent2, action2_result))
        cumulative_payoffs_history.append((float(game.payoffs[0]), float(game.payoffs[1])))

        last_action1 = action1
        last_action2 = action2

        # Логирование раунда
        SimulationLogger.log_round(
            round_num, agent1_name, agent2_name,
            str(action1), str(action2), payoff1, payoff2,
            game.payoffs[0], game.payoffs[1]
        )

    # Итоги игры
    game_summary = game.get_summary()
    SimulationLogger.log_simulation_end(game, game_summary)

    # Итоговое состояние агентов
    SimulationLogger.log_agent_final_state(agent1_name, agent1, game.payoffs[0])
    SimulationLogger.log_agent_final_state(agent2_name, agent2, game.payoffs[1])

    # Построение графиков
    plot_simulation_results(
        agent1_name,
        agent2_name,
        agent1_metrics_history,
        agent2_metrics_history,
        cumulative_payoffs_history
    )


# ════════════════════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ПРОГРАММА
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Главная функция"""

    print("\n" + "=" * 100)
    print("🤖 СИСТЕМА СИМУЛЯЦИИ ИНТЕЛЛЕКТУАЛЬНЫХ АГЕНТОВ")
    print("=" * 100)
    print("\nДобро пожаловать в систему симуляции агентов!")
    print("Доступные типы агентов: Эмоциональный, Рациональный, Комбинированный, Фиксированная стратегия")

    # Выбор игры
    game, game_name = InteractiveMenu.choose_game()
    print(f"\n✅ Выбрана игра: {game_name}")

    # Выбор количества раундов
    total_rounds = InteractiveMenu.choose_rounds()
    print(f"✅ Количество раундов: {total_rounds}")

    game_actions = get_game_actions_for_game(game)

    # ─── ПЕРВЫЙ АГЕНТ ─────────────────────────────────────────────────────────
    print("\n" + "-" * 100)
    print("⚙️ КОНФИГУРАЦИЯ АГЕНТА 1")
    print("-" * 100)

    agent1_type = InteractiveMenu.choose_agent_type()
    agent1_name = input("\nВведите имя для Агента 1 (по умолчанию 'Agent 1'): ").strip() or "Agent 1"

    agent1_personality = None
    agent1_intensity = None
    agent1_strategy = None

    if agent1_type in ["emotional_rational", "emotional", "fixed_strategy"]:
        print("\n⚙️ Выбор параметров личности:")
        agent1_personality = InteractiveMenu.choose_personality()
        agent1_intensity = InteractiveMenu.choose_intensity()

    if agent1_type == "fixed_strategy":
        print("\n⚙️ Выбор стратегии:")
        agent1_strategy = InteractiveMenu.choose_fixed_strategy()

    agent1 = create_agent(
        agent1_type, agent1_name,
        personality=agent1_personality,
        intensity=agent1_intensity,
        strategy=agent1_strategy,
        log_level=LogLevel.SILENT,
        game_actions=game_actions
    )

    if not agent1:
        print(f"❌ Не удалось создать Агента 1. Выход.")
        return

    print(f"✅ Агент 1 создан: {agent1_name} ({agent1_type})")

    # ─── ВТОРОЙ АГЕНТ ─────────────────────────────────────────────────────────
    print("\n" + "-" * 100)
    print("⚙️ КОНФИГУРАЦИЯ АГЕНТА 2")
    print("-" * 100)

    agent2_type = InteractiveMenu.choose_agent_type()
    agent2_name = input("\nВведите имя для Агента 2 (по умолчанию 'Agent 2'): ").strip() or "Agent 2"

    agent2_personality = None
    agent2_intensity = None
    agent2_strategy = None

    if agent2_type in ["emotional_rational", "emotional", "fixed_strategy"]:
        print("\n⚙️ Выбор параметров личности:")
        agent2_personality = InteractiveMenu.choose_personality()
        agent2_intensity = InteractiveMenu.choose_intensity()

    if agent2_type == "fixed_strategy":
        print("\n⚙️ Выбор стратегии:")
        agent2_strategy = InteractiveMenu.choose_fixed_strategy()

    agent2 = create_agent(
        agent2_type, agent2_name,
        personality=agent2_personality,
        intensity=agent2_intensity,
        strategy=agent2_strategy,
        log_level=LogLevel.SILENT,
        game_actions=game_actions
    )

    if not agent2:
        print(f"❌ Не удалось создать Агента 2. Выход.")
        return

    print(f"✅ Агент 2 создан: {agent2_name} ({agent2_type})")

    # ─── ЗАПУСК СИМУЛЯЦИИ ─────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("🚀 ПОДГОТОВКА К ЗАПУСКУ...")
    print("=" * 100)
    print(f"\n📋 ПАРАМЕТРЫ СИМУЛЯЦИИ:")
    print(f" • Игра: {game_name}")
    print(f" • Агент 1: {agent1_name} ({agent1_type})")
    print(f" • Агент 2: {agent2_name} ({agent2_type})")
    print(f" • Раундов: {total_rounds}")

    input("\nНажмите Enter для запуска симуляции...")

    # Запуск симуляции
    try:
        run_simulation(game, agent1, agent2, total_rounds)
        print("\n✅ Симуляция успешно завершена!")
    except Exception as e:
        print(f"\n❌ Ошибка во время симуляции: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
