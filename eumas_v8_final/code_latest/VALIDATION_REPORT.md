# Validation report

Дата проверки: 2026-05-11

## Синтаксис

Проверено:

```bash
python -m py_compile *.py
```

Результат: без ошибок.

## Smoke / quick checks

Проверены следующие команды в рабочей среде:

```bash
python experiment_runner.py --scenario S0 --profile quick --episodes 1 --rounds 5 --games "Prisoners Dilemma" --yes
python experiment_runner.py --scenario S1 --profile quick --episodes 1 --rounds 1 --games all --yes
python experiment_runner.py --scenario S2 --profile quick --episodes 1 --rounds 2 --games all --yes
python experiment_runner.py --scenario S3 --profile quick --episodes 1 --rounds 2 --games "Prisoners Dilemma" --yes
python experiment_runner.py --scenario S4 --profile quick --episodes 1 --rounds 2 --games all --yes
```

Результат: все команды завершились без ошибок в episode-level logs (`errors_count = 0`).

## Проверка выходных файлов

Для сценариев сформированы:

- `config.json`
- `round_level.csv`
- `episode_level.csv`
- `summary_by_condition.csv`
- `summary_for_paper.csv`
- `adaptation_summary.csv`
- `collapse_diagnostics.csv`
- `plots/`
- `README.txt`
- `run_log.txt`

## Ограничение проверки

Полные `standard` и `paper` прогоны не запускались в этой среде, чтобы не тратить значительное время на десятки/сотни условий. Кодовые пути и сценарии проверены на quick-конфигурациях, включая S1 по всем трём играм.
