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
