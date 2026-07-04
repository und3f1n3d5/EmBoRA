# Experiment Runner v3

Интерактивная и CLI-обёртка для запуска экспериментов с эмоционально-ограниченно-рациональными агентами.

## Что делает

- Не изменяет текущие файлы агентов и игр.
- Импортирует существующий `main.py` и использует его публичные функции создания агентов и игровые классы.
- Поддерживает сценарии S0–S4 из ТЗ v3:
  - S0 — smoke / sanity check;
  - S1 — cross-type matchup matrix по играм;
  - S2 — адаптация к fixed strategies;
  - S3 — personality × emotional intensity sweep;
  - S4 — internal state dynamics / collapse diagnostics.
- Сохраняет `config.json`, `round_level.csv`, `episode_level.csv`, `summary_by_condition.csv`, `summary_for_paper.csv`, `adaptation_summary.csv`, `collapse_diagnostics.csv`, `plots/`, `README.txt`, `run_log.txt`.
- Поддерживает профили `quick`, `standard`, `paper`.
- Умеет пересобирать графики из уже сохранённых CSV.

## Установка

Положите файлы рядом с текущими:

```text
main.py
agent_fixed.py
emotional_agent.py
rational_new.py
fixed_strategy_agent.py
experiment_runner.py
experiment_config.py
experiment_utils.py
experiment_metrics.py
experiment_plots.py
```

## Интерактивный запуск

```bash
python experiment_runner.py
```

## Быстрый smoke-test

```bash
python experiment_runner.py --scenario S0 --profile quick --episodes 1 --rounds 20 --games "Prisoners Dilemma" --yes
```

## Paper-ready пример

```bash
python experiment_runner.py --scenario S1 --profile paper --games all --yes
```

Осторожно: `paper` может запускаться долго, потому что создаёт много условий и минимум 20 эпизодов на условие.

## Пересборка графиков из CSV

```bash
python experiment_runner.py --rebuild-plots experiments_output/<run_folder>
```

## Интерпретационные ограничения

`summary_for_paper.csv` — это компактная таблица для статьи, но она не должна использоваться как автоматическое доказательство полного превосходства гибридных агентов или подтверждение human-like behavior. Для H2 runner только экспортирует поведенческие трейсы для будущего сравнения с человеческими данными.
# Исправленный код агентов и experiment runner

## Быстрый старт

Распакуйте архив и перейдите в папку с кодом:

```bash
cd fixed_agent_experiment_code
```

Проверьте smoke-run:

```bash
python experiment_runner.py --scenario S0 --profile quick --episodes 1 --rounds 20 --games "Prisoners Dilemma" --yes
```

## Основные сценарии

```bash
# S1: matchup matrix
python experiment_runner.py --scenario S1 --profile standard --games all --yes

# S2: adaptation to fixed strategies
python experiment_runner.py --scenario S2 --profile standard --games all --yes

# S3: personality × intensity sweep
python experiment_runner.py --scenario S3 --profile standard --games "Prisoners Dilemma" --yes

# S4: internal-state dynamics / collapse diagnostics
python experiment_runner.py --scenario S4 --profile standard --games all --yes
```

Для публикационных SVG-графиков добавьте:

```bash
python experiment_runner.py --scenario S4 --profile standard --games all --yes --save-svg
```

## Пересборка графиков из CSV

```bash
python experiment_runner.py --rebuild-plots experiments_output/<run_dir>
```

## Выходные артефакты

Каждый запуск создаёт отдельную папку `experiments_output/<timestamp>_<profile>_<scenario>/` с файлами:

- `config.json` — полная конфигурация запуска и seeds;
- `round_level.csv` — строка на каждый ход;
- `episode_level.csv` — строка на каждый эпизод;
- `summary_by_condition.csv` — агрегаты по условию;
- `summary_for_paper.csv` — компактная таблица для статьи;
- `adaptation_summary.csv` — first-vs-last-third метрики;
- `collapse_diagnostics.csv` — диагностика внутренних траекторий;
- `plots/` — графики;
- `README.txt` и `run_log.txt` — описание запуска.

## Важно про границы исправлений

Код не реализует новую будущую ветку `white-box bounded-rational agent` и `belief update`. Это сознательно оставлено вне текущего пакета, чтобы не смешивать доработки текущей статьи со следующей экспериментальной программой.

Добавленный `diagnostic_adapter.py` работает только как post-hoc слой логирования: он не меняет поведение агентов.
