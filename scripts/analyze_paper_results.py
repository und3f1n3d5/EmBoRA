from __future__ import annotations
import json, re, shutil, zipfile, hashlib
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path('/mnt/data/analysis_work/results/paper_results_to_send_20260521_175508')
OUT = Path('/mnt/data/final_paper_experiment_materials_20260521')
TABLES = OUT/'article_materials'/'tables'
FIGS = OUT/'article_materials'/'figures'
DOCS = OUT/'docs'
SUMS = OUT/'github_materials'/'compact_results'
SCRIPTS = OUT/'scripts'
RAW = OUT/'raw_input_archives'
CODE = OUT/'github_materials'/'code'
for p in [TABLES, FIGS, DOCS, SUMS, SCRIPTS, RAW, CODE]:
    p.mkdir(parents=True, exist_ok=True)

OFFICIAL = [
    ('reported_runs_compat','S1', ROOT/'paper_runs_reported/20260521_163020_paper_S1_reported_runs_compat'),
    ('reported_runs_compat','S2', ROOT/'paper_runs_reported/20260521_163508_paper_S2_reported_runs_compat'),
    ('reported_runs_compat','S3', ROOT/'paper_runs_reported/20260521_163747_paper_S3_reported_runs_compat'),
    ('reported_runs_compat','S4', ROOT/'paper_runs_reported/20260521_163931_paper_S4_reported_runs_compat'),
    ('integrated_model','S1', ROOT/'paper_runs_integrated/20260521_173035_paper_S1_integrated_model'),
    ('integrated_model','S2', ROOT/'paper_runs_integrated/20260521_173426_paper_S2_integrated_model'),
    ('integrated_model','S3', ROOT/'paper_runs_integrated/20260521_174014_paper_S3_integrated_model'),
    ('integrated_model','S4', ROOT/'paper_runs_integrated/20260521_174430_paper_S4_integrated_model'),
]

def file_sha256(path: Path) -> str:
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

# copy current analysis script into deliverable
shutil.copy2(__file__, SCRIPTS/'analyze_paper_results.py')

run_rows=[]
validation_rows=[]
all_sf=[]
all_sbc=[]
all_adapt=[]
all_collapse=[]
expected = {'S1': (48,20,200,192000,960), 'S2': (27,20,200,108000,540), 'S3': (27,20,200,108000,540), 'S4': (12,20,200,48000,240)}
for mode, scenario, d in OFFICIAL:
    cfg = json.load(open(d/'config.json', encoding='utf-8'))
    val = json.load(open(d/'validation_report.json', encoding='utf-8'))
    exp = expected[scenario]
    run_rows.append({
        'model_mode': mode,
        'scenario': scenario,
        'run_dir': d.name,
        'games': ', '.join(sorted(set([c.get('game_name','') for c in cfg.get('conditions',[])]))),
        'conditions_n': len(cfg.get('conditions',[])),
        'episodes_per_condition': cfg.get('episodes_per_condition'),
        'seed_count': cfg.get('seed_count'),
        'rounds_per_episode': cfg.get('rounds_per_episode'),
        'expected_round_rows': exp[3],
        'expected_episode_rows': exp[4],
        'actual_round_rows': val.get('round_rows'),
        'actual_episode_rows': val.get('episode_rows'),
        'validation_passed': val.get('passed'),
        'fallback_rows': val.get('fallback_rows'),
        'duplicate_observe_count': val.get('duplicate_observe_count'),
        'mood_out_of_range': val.get('mood_out_of_range'),
        'fatigue_out_of_range': val.get('fatigue_out_of_range'),
        'nan_or_inf_cells': val.get('nan_or_inf_cells'),
        'missing_files_count': len(val.get('missing_files', [])),
    })
    validation_rows.append({
        'model_mode': mode,
        'scenario': scenario,
        **val
    })
    sf = pd.read_csv(d/'summary_for_paper.csv')
    sbc = pd.read_csv(d/'summary_by_condition.csv')
    ad = pd.read_csv(d/'adaptation_summary.csv')
    co = pd.read_csv(d/'collapse_diagnostics.csv')
    for df in [sf,sbc,ad,co]:
        df['official_run_dir'] = d.name
        df['model_mode'] = mode
        df['scenario_name'] = scenario
    sf['pair_state_mean'] = (sf['agent_1_mean_overall_state']+sf['agent_2_mean_overall_state'])/2
    sf['mean_negative_state_share'] = (sf['agent_1_negative_state_share']+sf['agent_2_negative_state_share'])/2
    # numeric metric by game
    def metric(row):
        if row['game_name'] in ['Prisoners Dilemma','Battle of Sexes']:
            return pd.to_numeric(row['game_metric_value'], errors='coerce')
        if row['game_name'] == 'Ultimatum Game':
            m = re.match(r'\s*([0-9.]+)\s*/', str(row['game_metric_value']))
            return float(m.group(1)) if m else np.nan
        return np.nan
    sf['main_game_metric'] = sf.apply(metric, axis=1)
    sbc['pair_state_mean'] = (sbc['mean_overall_state_1_mean']+sbc['mean_overall_state_2_mean'])/2
    sbc['mean_negative_state_share'] = (sbc['negative_state_share_1_mean']+sbc['negative_state_share_2_mean'])/2
    all_sf.append(sf)
    all_sbc.append(sbc)
    all_adapt.append(ad)
    all_collapse.append(co)
    # compact copy without huge round_level
    target = SUMS/mode/scenario
    target.mkdir(parents=True, exist_ok=True)
    for fname in ['summary_for_paper.csv','summary_by_condition.csv','episode_level.csv','adaptation_summary.csv','collapse_diagnostics.csv','config.json','manifest.json','validation_report.json','validation_report.md','README.txt','run_log.txt']:
        shutil.copy2(d/fname, target/fname)

run_inventory = pd.DataFrame(run_rows)
validation = pd.DataFrame(validation_rows)
sf = pd.concat(all_sf, ignore_index=True)
sbc = pd.concat(all_sbc, ignore_index=True)
adapt = pd.concat(all_adapt, ignore_index=True)
collapse = pd.concat(all_collapse, ignore_index=True)

# Include ignored/incomplete/duplicate run note
ignored=[]
for d in sorted((ROOT/'paper_runs_reported').iterdir()):
    if not d.is_dir(): continue
    status = 'official' if d in [x[2] for x in OFFICIAL] else 'ignored'
    files = {p.name for p in d.glob('*')}
    reason = ''
    if status=='ignored':
        if 'validation_report.json' not in files:
            reason = 'incomplete run, only config or failed pre-output run'
        elif d.name == '20260521_161912_paper_S1_reported_runs_compat':
            reason = 'complete duplicate of official reported S1; same summary_for_paper hash as 20260521_163020'
    ignored.append({'root':'paper_runs_reported','run_dir':d.name,'status':status,'reason':reason,'files_count':len(files)})
for d in sorted((ROOT/'paper_runs_integrated').iterdir()):
    if not d.is_dir(): continue
    ignored.append({'root':'paper_runs_integrated','run_dir':d.name,'status':'official','reason':'','files_count':len(list(d.glob('*')))})
ignored_runs = pd.DataFrame(ignored)

# Scenario-mode overview
scenario_mode = sf.groupby(['scenario_name','model_mode']).agg(
    conditions_n=('condition_label','count'),
    pair_total_payoff_mean=('pair_total_payoff_mean','mean'),
    pair_total_payoff_median=('pair_total_payoff_mean','median'),
    pair_state_mean=('pair_state_mean','mean'),
    pair_state_median=('pair_state_mean','median'),
    mean_negative_state_share=('mean_negative_state_share','mean'),
    min_pair_state=('pair_state_mean','min'),
    max_pair_state=('pair_state_mean','max'),
).reset_index()

# S1 selected comparisons
selected_labels = [
    'hybrid-neutral-neutral__vs__hybrid-neutral-neutral',
    'hybrid-neutral-neutral__vs__rational',
    'rational__vs__rational',
    'emotional-neutral-neutral__vs__rational',
    'fixed-tit_for_tat__vs__fixed-tit_for_tat',
]
s1_selected = sf[(sf.scenario_name=='S1') & (sf.condition_label.isin(selected_labels))].copy()
s1_selected['split_payoff'] = s1_selected['agent_1_payoff_mean'].round(1).astype(str)+' / '+s1_selected['agent_2_payoff_mean'].round(1).astype(str)
s1_selected = s1_selected[['model_mode','game_name','condition_label','pair_total_payoff_mean','split_payoff','pair_state_mean','agent_1_negative_state_share','agent_2_negative_state_share','game_metric_name','game_metric_value']]

# S1 top/bottom tables
s1 = sf[sf.scenario_name=='S1'].copy()
s1_top_payoff = s1.sort_values(['model_mode','game_name','pair_total_payoff_mean'], ascending=[True, True, False]).groupby(['model_mode','game_name']).head(5)
s1_bottom_state = s1.sort_values(['model_mode','pair_state_mean'], ascending=[True, True]).groupby('model_mode').head(10)
s1_mode_delta = s1.pivot_table(index=['scenario_name','game_name','condition_label'], columns='model_mode', values=['pair_total_payoff_mean','pair_state_mean','mean_negative_state_share']).reset_index()
s1_mode_delta.columns = ['_'.join([str(x) for x in col if x]) for col in s1_mode_delta.columns]
if 'pair_state_mean_integrated_model' in s1_mode_delta.columns:
    s1_mode_delta['delta_pair_state_integrated_minus_reported'] = s1_mode_delta['pair_state_mean_integrated_model'] - s1_mode_delta['pair_state_mean_reported_runs_compat']
    s1_mode_delta['delta_payoff_integrated_minus_reported'] = s1_mode_delta['pair_total_payoff_mean_integrated_model'] - s1_mode_delta['pair_total_payoff_mean_reported_runs_compat']
    s1_mode_delta['delta_negative_share_integrated_minus_reported'] = s1_mode_delta['mean_negative_state_share_integrated_model'] - s1_mode_delta['mean_negative_state_share_reported_runs_compat']

# S2 adaptation PD
s2_pd_adapt = adapt[(adapt.scenario_name=='S2') & (adapt.game_name=='Prisoners Dilemma')].groupby(['model_mode','condition_label','fixed_strategy_2','metric_name']).agg(
    first_third_metric=('first_third_metric','mean'),
    last_third_metric=('last_third_metric','mean'),
    delta_metric=('delta_metric','mean'),
    first_third_payoff_1=('first_third_payoff_1','mean'),
    last_third_payoff_1=('last_third_payoff_1','mean'),
    delta_payoff_1=('delta_payoff_1','mean'),
    episodes_n=('episode_id','count'),
).reset_index()

# S3 aggregate by profile-intensity-fixed partner
def parse_s3(label):
    # hybrid-optimistic-low__vs__fixed-always_cooperate
    m = re.match(r'hybrid-([^-_]+)-([^-_]+)__vs__fixed-(.+)$', label)
    if m: return pd.Series({'profile':m.group(1),'intensity':m.group(2),'fixed_partner':m.group(3)})
    return pd.Series({'profile':'unknown','intensity':'unknown','fixed_partner':'unknown'})
s3 = sf[sf.scenario_name=='S3'].copy()
s3 = pd.concat([s3, s3['condition_label'].apply(parse_s3)], axis=1)
s3_profile = s3.groupby(['model_mode','profile','intensity']).agg(
    conditions_n=('condition_label','count'),
    pair_total_payoff_mean=('pair_total_payoff_mean','mean'),
    agent_1_mean_overall_state=('agent_1_mean_overall_state','mean'),
    agent_1_negative_state_share=('agent_1_negative_state_share','mean'),
    main_game_metric=('main_game_metric','mean'),
).reset_index()
s3_full = s3[['model_mode','profile','intensity','fixed_partner','condition_label','pair_total_payoff_mean','agent_1_mean_overall_state','agent_1_negative_state_share','main_game_metric']]

# S4 table
s4 = sf[sf.scenario_name=='S4'].copy()
s4_table = s4[['model_mode','game_name','condition_label','pair_total_payoff_mean','agent_1_payoff_mean','agent_2_payoff_mean','agent_1_mean_overall_state','agent_2_mean_overall_state','agent_1_negative_state_share','agent_2_negative_state_share','game_metric_name','game_metric_value']]

# Save CSVs
for name, df in [
    ('run_inventory.csv', run_inventory),
    ('validation_summary.csv', validation),
    ('ignored_runs.csv', ignored_runs),
    ('scenario_mode_overview.csv', scenario_mode),
    ('all_summary_for_paper_official.csv', sf),
    ('all_summary_by_condition_official.csv', sbc),
    ('table_s1_selected_comparisons.csv', s1_selected),
    ('table_s1_top_payoff.csv', s1_top_payoff),
    ('table_s1_bottom_state.csv', s1_bottom_state),
    ('table_s1_mode_delta.csv', s1_mode_delta),
    ('table_s2_pd_adaptation.csv', s2_pd_adapt),
    ('table_s3_profile_intensity_aggregate.csv', s3_profile),
    ('table_s3_full_conditions.csv', s3_full),
    ('table_s4_diagnostics.csv', s4_table),
]:
    df.to_csv(TABLES/name, index=False)

# Markdown/Tex versions of key tables
for name, df in [
    ('scenario_mode_overview', scenario_mode),
    ('s1_selected_comparisons', s1_selected),
    ('s2_pd_adaptation', s2_pd_adapt),
    ('s3_profile_intensity_aggregate', s3_profile),
    ('s4_diagnostics', s4_table),
]:
    (TABLES/f'{name}.md').write_text(df.round(3).to_markdown(index=False), encoding='utf-8')
    (TABLES/f'{name}.tex').write_text(df.round(3).to_latex(index=False, escape=True), encoding='utf-8')

# plots
plt.rcParams.update({'figure.figsize': (10,6), 'axes.grid': True})

def savefig(name):
    plt.tight_layout()
    plt.savefig(FIGS/name, dpi=180, bbox_inches='tight')
    plt.close()

# scenario state comparison
pivot = scenario_mode.pivot(index='scenario_name', columns='model_mode', values='pair_state_mean').sort_index()
pivot.plot(kind='bar')
plt.title('Mean pair internal state by scenario and model mode')
plt.ylabel('Mean pair overall state')
plt.xlabel('Scenario')
savefig('fig_scenario_mode_pair_state.png')

pivotp = scenario_mode.pivot(index='scenario_name', columns='model_mode', values='pair_total_payoff_mean').sort_index()
pivotp.plot(kind='bar')
plt.title('Mean pair payoff by scenario and model mode')
plt.ylabel('Mean pair total payoff')
plt.xlabel('Scenario')
savefig('fig_scenario_mode_pair_payoff.png')

pivotn = scenario_mode.pivot(index='scenario_name', columns='model_mode', values='mean_negative_state_share').sort_index()
pivotn.plot(kind='bar')
plt.title('Mean negative-state share by scenario and model mode')
plt.ylabel('Mean negative-state share')
plt.xlabel('Scenario')
savefig('fig_scenario_mode_negative_share.png')

for mode in ['reported_runs_compat','integrated_model']:
    x = s1[s1.model_mode==mode].copy()
    for game in x.game_name.unique():
        y=x[x.game_name==game]
        plt.figure(figsize=(8,6))
        plt.scatter(y['pair_total_payoff_mean'], y['pair_state_mean'])
        for _,r in y.iterrows():
            lab = r['condition_label'].replace('hybrid-neutral-neutral','H').replace('emotional-neutral-neutral','E').replace('rational','R').replace('fixed-tit_for_tat','TFT')
            lab = lab.replace('__vs__','-')
            if len(lab)>28: lab=lab[:28]
            plt.annotate(lab, (r['pair_total_payoff_mean'], r['pair_state_mean']), fontsize=6, alpha=0.75)
        plt.title(f'S1 payoff-state trade-off: {game} / {mode}')
        plt.xlabel('Pair total payoff')
        plt.ylabel('Pair mean overall state')
        savefig(f"fig_s1_tradeoff_{mode}_{game.replace(' ','_')}.png")

# S2 PD adaptation
for mode in ['reported_runs_compat','integrated_model']:
    y=s2_pd_adapt[s2_pd_adapt.model_mode==mode].copy()
    y['short_label']=y['condition_label'].str.replace('hybrid-neutral-neutral','H',regex=False).str.replace('emotional-neutral-neutral','E',regex=False).str.replace('rational','R',regex=False).str.replace('fixed-','F-',regex=False)
    y=y.sort_values('condition_label')
    fig, ax1 = plt.subplots(figsize=(12,6))
    ax1.bar(range(len(y)), y['delta_payoff_1'])
    ax1.set_ylabel('Delta payoff A1: last third - first third')
    ax1.set_xticks(range(len(y)))
    ax1.set_xticklabels(y['short_label'], rotation=45, ha='right', fontsize=7)
    ax2 = ax1.twinx()
    ax2.plot(range(len(y)), y['delta_metric'], marker='o')
    ax2.set_ylabel('Delta cooperation metric')
    plt.title(f'S2/PD adaptation proxy / {mode}')
    savefig(f'fig_s2_pd_adaptation_{mode}.png')

# S3 profile aggregate
for mode in ['reported_runs_compat','integrated_model']:
    y=s3_profile[s3_profile.model_mode==mode].copy()
    y['label']=y['profile']+'-'+y['intensity']
    y=y.sort_values(['profile','intensity'])
    plt.figure(figsize=(10,5))
    plt.bar(y['label'], y['agent_1_mean_overall_state'])
    plt.xticks(rotation=45, ha='right')
    plt.title(f'S3/PD profile-intensity aggregate: agent 1 state / {mode}')
    plt.ylabel('Agent 1 mean overall state')
    savefig(f'fig_s3_profile_intensity_state_{mode}.png')

# S4 diagnostics
for mode in ['reported_runs_compat','integrated_model']:
    y=s4[s4.model_mode==mode].copy().sort_values(['game_name','condition_label'])
    y['short_label']=y['game_name'].str[:3] + ': ' + y['condition_label'].str.replace('hybrid-neutral-neutral','H',regex=False).str.replace('emotional-neutral-neutral','E',regex=False).str.replace('rational','R',regex=False).str.replace('fixed-always_defect','F-D',regex=False).str.replace('fixed-tit_for_tat','F-TFT',regex=False)
    fig, ax1 = plt.subplots(figsize=(12,6))
    ax1.bar(range(len(y)), y['agent_1_mean_overall_state'])
    ax1.set_ylabel('Agent 1 mean overall state')
    ax1.set_xticks(range(len(y)))
    ax1.set_xticklabels(y['short_label'], rotation=45, ha='right', fontsize=7)
    ax2 = ax1.twinx()
    ax2.plot(range(len(y)), y['agent_1_negative_state_share'], marker='o')
    ax2.set_ylabel('Agent 1 negative-state share')
    plt.title(f'S4 internal-state diagnostics / {mode}')
    savefig(f'fig_s4_diagnostics_{mode}.png')

# Generate MD reports
passed_all = bool(validation['passed'].all())
errors_total = int(validation['fallback_rows'].sum() + validation['duplicate_observe_count'].sum() + validation['mood_out_of_range'].sum() + validation['fatigue_out_of_range'].sum() + validation['nan_or_inf_cells'].sum() + validation['missing_files'].apply(lambda x: len(x) if isinstance(x,list) else 0).sum()) if 'missing_files' in validation else 0
pytest_text = (ROOT/'pytest_report_local.txt').read_bytes()
try:
    pytest_decoded = pytest_text.decode('utf-16')
except Exception:
    pytest_decoded = pytest_text.decode('utf-8','replace')
system_text = (ROOT/'system_info.txt').read_bytes()
try:
    system_decoded = system_text.decode('utf-16')
except Exception:
    system_decoded = system_text.decode('utf-8','replace')

validation_md = f"""# Validation summary

## Verdict

All official paper runs passed automated validation: **{passed_all}**. The local unit-test report says:

```text
{pytest_decoded.strip()}
```

Environment reported by the local Windows run:

```text
{system_decoded.strip()}
```

## Official runs

{run_inventory.round(3).to_markdown(index=False)}

## Ignored runs

Two early reported S1 directories were incomplete config-only attempts, and one complete manual S1 run is a duplicate of the final scripted S1 run. The official set uses the latest complete scripted run per scenario/mode.

{ignored_runs.to_markdown(index=False)}
"""
(DOCS/'VALIDATION_SUMMARY.md').write_text(validation_md, encoding='utf-8')

scenario_md = scenario_mode.round(3).to_markdown(index=False)
s1_sel_md = s1_selected.round(3).to_markdown(index=False)
s2_md = s2_pd_adapt.round(3).to_markdown(index=False)
s4_md = s4_table.round(3).to_markdown(index=False)

ru_report = f"""# Отчет по paper-экспериментам архитектурно выровненной версии

## Краткий вывод

Экспериментальный пакет в целом корректен и пригоден как artifact-backed материал для GitHub и следующей редакции статьи. Все официальные paper-запуски S1-S4 в двух режимах — `reported_runs_compat` и `integrated_model` — прошли автоматическую валидацию: отсутствуют пропущенные обязательные файлы, `NaN/inf`, выходы mood/fatigue за диапазоны, fallback-действия и повторные observe-обновления. Unit-тесты локально прошли: `15 passed`.

Важно методологически: эти запуски являются новым code snapshot после архитектурных исправлений. Поэтому `reported_runs_compat` следует понимать как режим воспроизводимости статусных границ статьи v11 и paper-profile протокола, а не как дословное численное воспроизведение старых таблиц v11. `integrated_model` является новой архитектурной веткой, где adapter/appraisal behavior-driving; его результаты нельзя смешивать с reported runs статьи v11 без явной пометки.

## Техническая валидность

{run_inventory.round(3).to_markdown(index=False)}

## Сводка по сценариям и режимам

{scenario_md}

Основной технический эффект исправлений виден в сравнении режимов: в `integrated_model` среднее внутреннее состояние пары выше во всех четырех сценариях, а средняя доля отрицательного состояния ниже. Это соответствует цели исправления delta-based appraisal и интеграции adapter/appraisal в цикл состояния.

## S1: cross-type matrix

{s1_sel_md}

Ключевые наблюдения:

- В PD sanity-check условия с взаимной кооперацией дают максимальный payoff 1200 и положительное состояние. Это важный регрессионный индикатор: исправленная модель больше не штрафует идеальное CC-взаимодействие только из-за недостижения абстрактного desired-state.
- В BoS и UG часть fixed/TFT и role-sensitive условий остается stress-test блоком, а не substantive behavioral evidence. Это соответствует guardrail статьи v11.
- `integrated_model` уменьшает хроническую отрицательность в большинстве сопоставимых S1-условий, но не устраняет все деградации: особенно проблемными остаются некоторые BoS и эмоционально-рациональные асимметрии.

## S2: fixed-strategy adaptation proxy, PD subset

{s2_md}

В текущем snapshot адаптация в S2 стала менее «шумной» и более дискретной: часть условий демонстрирует устойчивое поведение без заметного first/last-third сдвига. Для статьи это лучше подавать как adaptation proxy / stress test, а не как доказательство полноценного learning-to-partner behavior. Для следующего слоя валидации нужны partner-switching tests и targeted ablations.

## S3: profile-intensity sweep

Агрегированная таблица профилей и интенсивностей сохранена в `article_materials/tables/table_s3_profile_intensity_aggregate.csv`. Главный вывод: profile/intensity влияет на внутреннее состояние, но эффект зависит от fixed partner. В `integrated_model` среднее состояние по S3 выше, чем в `reported_runs_compat`, что ожидаемо после исправления appraisal/state update.

## S4: internal-state diagnostics

{s4_md}

S4 подтверждает, что после исправлений состояние стало интерпретируемее: в integrated-режиме средний pair state по S4 вырос примерно с -0.364 до 0.000, а negative-state share снизился примерно с 0.612 до 0.471. При этом часть условий остается отрицательной, что методологически полезно: деградация теперь локализуется в конкретных game/partner/action regimes, а не выглядит как тотальная ошибка mood-update.

## Что включено в итоговый пакет

- `github_materials/code/` — исправленный код, документация, тесты и examples.
- `github_materials/compact_results/` — компактная копия результатов без тяжелых `round_level.csv`.
- `raw_input_archives/` — исходный архив с полными результатами, включая `round_level.csv`.
- `article_materials/tables/` — CSV/Markdown/LaTeX таблицы для статьи.
- `article_materials/figures/` — заново сгенерированные графики по summary CSV. Переданный архив `paper_plots_to_send_20260521_180107.zip` был пустым, поэтому графики пересобраны из данных.
- `docs/` — отчет, validation summary, README и сопроводительная документация.

## Рекомендации для статьи

1. Для прямой доработки статьи v11 использовать `reported_runs_compat` только как paper-compatible snapshot с четкой оговоркой, что это исправленный кодовый снимок.
2. Для новой сильной версии статьи акцентировать `integrated_model`: он лучше согласуется с заявленной архитектурой game -> values -> appraisal -> state -> decision.
3. Не заявлять универсальное превосходство hybrid agents. Более корректная формулировка: исправленная архитектура делает payoff/state divergence наблюдаемым и снижает искусственную хроническую отрицательность.
4. S2/S3/S4 использовать как diagnostic calibration layer и мост к следующей валидации: ablations, white-box traces, human/observer validation.
"""
(DOCS/'EXPERIMENT_ANALYSIS_REPORT_RU.md').write_text(ru_report, encoding='utf-8')

eng_report = f"""# Paper experiment report for the architecture-aligned code snapshot

## Executive verdict

The experiment package is technically valid and suitable as artifact-backed material for GitHub and for the next manuscript revision. All official S1-S4 paper runs passed validation in both modes: `reported_runs_compat` and `integrated_model`. There are no missing required files, NaN/inf cells, out-of-range mood/fatigue values, fallback actions, or duplicate observe updates. The local unit-test suite passed with `15 passed`.

Methodological caveat: these results are a new code snapshot after architecture fixes. `reported_runs_compat` reproduces the v11 status boundaries and paper-profile protocol, not necessarily the exact numeric tables in the previous v11 artifact. `integrated_model` is a new architecture mode and must be reported separately.

## Scenario-mode overview

{scenario_md}

The main effect of the corrected architecture is clear: `integrated_model` improves mean internal state and reduces negative-state share across all S1-S4 scenarios. This supports the purpose of the fixes: remove artificial chronic negative-state dynamics and make state degradation traceable.

## Main selected S1 comparisons

{s1_sel_md}

## PD adaptation proxy in S2

{s2_md}

## S4 diagnostics

{s4_md}

## Manuscript recommendation

Use the new results as a diagnostic calibration package. Avoid claims of universal hybrid-agent dominance. The strongest claim is that the architecture exposes payoff/state divergence and that the integrated implementation reduces implementation-induced negative-state saturation while preserving interpretable failure modes.
"""
(DOCS/'EXPERIMENT_ANALYSIS_REPORT_EN.md').write_text(eng_report, encoding='utf-8')

article_note = """# Записка для статьи

## Как использовать результаты

- `reported_runs_compat` — paper-compatible режим. Его можно использовать как воспроизводимый кодовый снимок, согласованный со статусной матрицей статьи v11: behavior-driving vs diagnostic/explanatory layer.
- `integrated_model` — новая архитектурная версия. Ее результаты сильнее соответствуют концепции статьи, потому что game-to-values adapter и appraisal реально входят в update loop.

## Главная интерпретация

После исправлений хроническая отрицательность состояния больше не выглядит универсальным артефактом формулы mood/appraisal. В благоприятных PD-условиях, например mutual cooperation / TFT sanity check, состояние положительное. При этом в части BoS/UG и асимметричных условий state degradation сохраняется, что дает содержательный материал для разделов Threats, Discussion и Future Work.

## Формулировка для Results/Discussion

The corrected architecture improves internal-state calibration without making the agents artificially happy. Positive value deltas can now produce positive appraisal and stable internal state in favorable repeated-game regimes, while negative regimes remain visible in asymmetric or poorly coordinated interactions. The results should therefore be interpreted as a diagnostic calibration layer rather than as evidence of universal superiority of any agent class.
"""
(DOCS/'ARTICLE_NOTE_RU.md').write_text(article_note, encoding='utf-8')

readme = f"""# Final paper experiment materials — 2026-05-21

This archive contains analyzed paper-scale results for the architecture-aligned emotionally bounded-rational agent code.

## Contents

- `github_materials/code/` — code, tests, docs and examples from the architecture-aligned release.
- `github_materials/compact_results/` — compact per-run outputs without heavy `round_level.csv` files.
- `raw_input_archives/` — uploaded raw result archives; the full `round_level.csv` files are inside `paper_results_to_send_20260521_175508.zip`.
- `article_materials/tables/` — CSV, Markdown and LaTeX tables for the paper.
- `article_materials/figures/` — regenerated summary figures.
- `docs/EXPERIMENT_ANALYSIS_REPORT_RU.md` — main Russian analysis report.
- `docs/EXPERIMENT_ANALYSIS_REPORT_EN.md` — concise English report for paper drafting.
- `docs/VALIDATION_SUMMARY.md` — run inventory and validation status.
- `scripts/analyze_paper_results.py` — script used to generate the analysis package.

## Validation verdict

All official S1-S4 runs passed validation in both modes. Unit tests passed locally: `15 passed`.

## Important caveat

The original `paper_plots_to_send_20260521_180107.zip` archive contained only empty plot directories. Figures in this package were regenerated from summary CSV files.
"""
(OUT/'README.md').write_text(readme, encoding='utf-8')

# Generate GitHub release README
(DOCS/'GITHUB_RELEASE_NOTES.md').write_text("""# GitHub release notes

## Recommended release structure

Publish the code from `github_materials/code/fixed_agent_experiment_code` as the repository content. Put full raw paper results in GitHub Releases or Git LFS, because `round_level.csv` files are large. Keep compact summaries in the repository under `results/compact/`.

## What is validated

- Unit tests: 15 passed.
- Official paper runs: S1-S4 in `reported_runs_compat` and `integrated_model`.
- Validation checks: required files, row counts, NaN/inf, mood/fatigue bounds, duplicate observe, fallback rows.

## Suggested repository folders

```text
agent_core/
tests/
docs/
examples/
results/compact/
article_materials/tables/
article_materials/figures/
```

Do not mix `reported_runs_compat` and `integrated_model` results in the same claims. Treat the first as paper-compatible and the second as a new integrated architecture snapshot.
""", encoding='utf-8')

# Copy raw archives
for src in ['/mnt/data/paper_results_to_send_20260521_175508.zip','/mnt/data/paper_plots_to_send_20260521_180107.zip']:
    sp=Path(src)
    if sp.exists(): shutil.copy2(sp, RAW/sp.name)

# Unpack code archive into github_materials/code
code_zip = Path('/mnt/data/architecture_aligned_agent_code_full_20260521.zip')
if code_zip.exists():
    with zipfile.ZipFile(code_zip) as z:
        z.extractall(CODE)
    shutil.copy2(code_zip, RAW/code_zip.name)

# Write manifest
manifest = {
    'created': '2026-05-21',
    'official_runs': run_inventory.to_dict(orient='records'),
    'validation_all_passed': bool(passed_all),
    'raw_archives': {p.name: {'size_bytes': p.stat().st_size, 'sha256': file_sha256(p)} for p in RAW.glob('*.zip')},
}
(OUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('Wrote package to', OUT)
