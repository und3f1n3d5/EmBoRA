# Записка для статьи

## Как использовать результаты

- `reported_runs_compat` — paper-compatible режим. Его можно использовать как воспроизводимый кодовый снимок, согласованный со статусной матрицей статьи v11: behavior-driving vs diagnostic/explanatory layer.
- `integrated_model` — новая архитектурная версия. Ее результаты сильнее соответствуют концепции статьи, потому что game-to-values adapter и appraisal реально входят в update loop.

## Главная интерпретация

После исправлений хроническая отрицательность состояния больше не выглядит универсальным артефактом формулы mood/appraisal. В благоприятных PD-условиях, например mutual cooperation / TFT sanity check, состояние положительное. При этом в части BoS/UG и асимметричных условий state degradation сохраняется, что дает содержательный материал для разделов Threats, Discussion и Future Work.

## Формулировка для Results/Discussion

The corrected architecture improves internal-state calibration without making the agents artificially happy. Positive value deltas can now produce positive appraisal and stable internal state in favorable repeated-game regimes, while negative regimes remain visible in asymmetric or poorly coordinated interactions. The results should therefore be interpreted as a diagnostic calibration layer rather than as evidence of universal superiority of any agent class.
