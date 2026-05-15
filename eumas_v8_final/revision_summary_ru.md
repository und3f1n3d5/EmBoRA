# Сводка доработки v8

Версия v8 подготовлена после комментариев научного руководителя к v6 и проверки v7.

Главный принцип: сохранить статью как diagnostic calibration study, не превращая ее в следующую работу и не заявляя future-компоненты как реализованные результаты.

Основные изменения:
- переработана Figure 1: стрелки разведены, добавлено понятное разделение conceptual pipeline / implementation status;
- Related Work переписан без подзаголовков;
- исправлена формализация внешней игры и adapter notation;
- уточнено, что diagnostic variables являются производными логируемыми величинами и не влияют на action selection в paper-profile runs;
- Table 2 очищена от Strategic reflection и Belief update как текущих компонентов;
- добавлено общее описание модели перед подразделами;
- добавлено краткое объяснение DQN-like механики;
- уточнены episode, round, condition, mutual cooperation, pair state и A1 negative-state share;
- Discussion и Threats переписаны в более связный стиль;
- в Results добавлено резюме по RQ1--RQ4.

PDF пересобран и визуально проверен по rendered PNG contact sheet.
