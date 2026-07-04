# Changelog — усиление текущего кода и experiment runner

## 2026-05-11

### Совместимость
- Добавлен однозначный `rational_new.py` на основе исправленного рационального baseline, чтобы `main.py` стабильно импортировал рационального агента без ручного переименования `rational_new_corrected.py`.
- Проверены точки входа `main.create_agent()` и `experiment_utils.create_agent()` для всех четырёх типов агентов: `emotional_rational`, `rational`, `emotional`, `fixed_strategy`.
- Сохранена backward compatibility: основной запуск остаётся `python experiment_runner.py`, CLI-запуск остаётся `python experiment_runner.py --scenario ...`.

### Рациональный baseline
- РМ принимает решения только по `game_state`.
- РМ обучается только на `payoff`.
- Эмоциональный модуль считается, логируется и обучается, но не влияет на действие рационального baseline.
- `mood`, `wellbeing`, `fatigue`, `resources`, `overall_state` обновляются и доступны для сравнительных графиков.

### Experiment runner / метрики
- Сценарии S0–S4 сохранены и проверены в quick-режиме.
- В `round_level.csv` добавлены пост-хок диагностические поля `q_material`, `q_fairness`, `q_relationship`, `q_safety`, `valence`, `emotional_load`, `attention_focus` для каждого агента. Эти поля не влияют на поведение агентов.
- Сохранены обязательные файлы: `config.json`, `round_level.csv`, `episode_level.csv`, `summary_by_condition.csv`, `summary_for_paper.csv`, `adaptation_summary.csv`, `collapse_diagnostics.csv`, `README.txt`, `run_log.txt`.
- Метрики PD / BoS / Ultimatum Game и first-vs-last-third adaptation сохраняются в CSV.

### Графики
- Генерация графиков сделана scenario-aware, чтобы S1 не создавал сотни тяжёлых time-series файлов.
- SVG-сохранение отключено по умолчанию ради скорости; включается флагом `--save-svg`.
- `--rebuild-plots` пересобирает графики из уже сохранённых CSV без повторного запуска агентов.

### Проверенные команды
- `python experiment_runner.py --scenario S0 --profile quick --episodes 1 --rounds 5 --games "Prisoners Dilemma" --yes`
- `python experiment_runner.py --scenario S1 --profile quick --episodes 1 --rounds 2 --games "Prisoners Dilemma" --yes`
- `python experiment_runner.py --scenario S2 --profile quick --episodes 1 --rounds 2 --games all --yes`
- `python experiment_runner.py --scenario S3 --profile quick --episodes 1 --rounds 2 --games "Prisoners Dilemma" --yes`
- `python experiment_runner.py --scenario S4 --profile quick --episodes 1 --rounds 2 --games all --yes`

Во всех проверках `errors_count = 0`.
