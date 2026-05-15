# Обработка комментариев научного руководителя к версии v6/v7

## 1. Уже учтено в v7

**Комментарий 5: ссылки на рисунки и интерпретации.** В v7 уже появились ссылки на Fig. 1--5 и базовые интерпретации в тексте Results/Model. Тем не менее в v8 эти ссылки были дополнительно усилены: рядом с Fig. 1 уточнен статус behavior-driving/diagnostic/future; в S1--S4 добавлены явные пояснения, как читать графики и таблицы.

**Комментарий 14: RQ1--RQ4 в разделе результатов/выводах.** В v7 уже был блок ответов на RQ в Discussion. В v8 он дополнительно перенесен ближе к результатам: в конце Results добавлено компактное резюме по RQ1--RQ4.

## 2. Не было достаточно учтено в v7, и стоило учесть

**Комментарий 1: Fig. 1, смешанные стрелки.** Принято. В v8 архитектурная схема полностью перерисована: Panel A теперь показывает более чистый conceptual loop, Panel B -- implementation status. Стрелки разведены по смыслу: solid = behavior-driving, dashed = diagnostic, dotted/grey = future.

**Комментарий 2: Related Work без подзаголовков.** Принято. В v8 Related Work переписан как связный текст про три направления работ: bounded rationality/social preferences, affective agent architectures, MARL/social dilemmas. Подзаголовки-параграфы убраны.

**Комментарий 3: формализация в 3.1.** Принято. Исправлены обозначения: \(\mathcal{A}=(\mathcal{A}_i)\), \(R=(R_i)\), \(\Omega\) теперь outcome space, adapter записан как \(q_i=(q_i^{mat},q_i^{fair},q_i^{rel},q_i^{safe})\).

**Комментарий 4: неясность post-hoc diagnostic.** Принято. В v8 пояснено, что diagnostic variables -- это производные величины, вычисляемые из логов после исхода для интерпретации paper-runs. Они не являются mood/fatigue/well-being и не меняют policy в этих экспериментах. Behavior-driving переменные явно отделены от diagnostic variables в тексте и Table 2.

**Комментарий 6: рубленый стиль Discussion/Threats.** Принято. В v8 Discussion и Threats переписаны в связное повествование. Телеграфные paragraph-заголовки типа “Statistical status” удалены; угрозы сначала кратко перечислены, затем обсуждены в прозе.

**Комментарий 7: Table 2, не упоминать strategic reflection/belief update как строки таблицы.** Принято частично. Эти элементы удалены из Table 2, чтобы не создавать впечатление реализованных механизмов. Они оставлены только как future validation steps в Conclusion/Threats, поскольку полностью исключать их из рукописи не стоит: они полезны как граница текущего вклада.

**Комментарий 8: общее описание модели перед подразделами.** Принято. После заголовка “Model Specification” добавлен вводный абзац, который описывает модель как closed affective-cognitive loop и заранее объясняет структуру подразделов.

**Комментарий 9: пояснить DQN-like.** Принято. Добавлен абзац с механикой DQN-like модулей: численный state vector, epsilon-greedy policy по Q-values, replay buffer, minibatch Bellman-style targets, target network; также уточнено, что 200-round traces не являются fully converged deep-RL policies.

**Комментарий 10: Table 3, непонятный заголовок.** Принято. Заголовок и подпись таблицы изменены: теперь это “Main paper-profile experimental scenarios”, где conditions трактуются как agent-pair/game settings, а plots -- как автоматически генерируемые diagnostics.

**Комментарий 11: Table 4, mutual cooperation и Pair state.** Принято. В текст перед Table 4 добавлены определения: mutual cooperation -- fraction of PD rounds in which both agents cooperate; Pair state -- mean of the two agents' mean overall-state scores.

**Комментарий 12: episode и DQN.** Принято. В Experimental Protocol добавлено определение episode и round; DQN-like mechanics пояснены в разделе Dual-System Control.

**Комментарий 13: Table 6, почему A1 neg почти 1.** Принято. В S4 добавлено объяснение: A1 neg -- share of rounds with \(S_1<0\); значения около 1 указывают на chronic negative-state regime из-за текущей калибровки targets/mood/fatigue, а не на полный внешний провал поведения.

## 3. Не учтено и не стоит учитывать

Полностью отвергнутых комментариев нет. Один пункт учтен не буквально: из Table 2 удалены strategic reflection и belief update, но они не исчезли из статьи полностью, а перенесены в Conclusion/Threats как future validation agenda. Это сделано потому, что полное удаление будущих компонентов ослабило бы ясность границ текущей работы и план дальнейшей проверки модели.

## Перечень внесенных доработок v8

1. Перерисована Figure 1 и обновлена подпись к ней.
2. Related Work переписан без подзаголовков как связное описание трех направлений.
3. Исправлена формализация внешней игры и adapter notation в разделе 3.1.
4. Уточнен смысл diagnostic variables и их отличие от behavior-driving variables.
5. Из Table 2 удалены strategic reflection и belief update как текущие компоненты; они перенесены в future agenda.
6. Добавлено вводное описание модели после заголовка Model Specification.
7. Добавлено краткое описание DQN-like механики.
8. Переименована и пояснена таблица paper-profile runs.
9. Добавлены определения episode, round, condition, mutual cooperation, pair state и A1 negative-state share.
10. Discussion и Threats переписаны в более связном, менее телеграфном стиле.
11. В Results добавлено явное резюме ответов на RQ1--RQ4.
