# journal_reference_v1 — adopted C6 v1.1 implementation candidate

Authority: EMBORA-U1-ADDENDUM-2026-10-04-C6-v1.1-v1.0, https://drive.google.com/file/d/1emil4YNPsMFkthkvXQY0mT8hdaT8_lA6/view. Scientific specification EMBORA-MSJ1-2026-10-04-R1C6-v1.1; parameter schema EMBORA-PARAMS-2026-10-04-R1C6-v1.1; numeric policy EMBORA-NUMERIC-2026-10-04-C6-v1.1. Frozen CANDIDATE/NOT_ADOPTED source labels describe release history; external author decision governs this continuation.

Code candidate only. Independent code/spec audit is pending; NOT_FROZEN. No pilot, full frame, ablation census, sensitivity trajectories, effect search or journal claims are authorized. A legal scientific config enum does not authorize execution.

From repository root, on qualified CPython **3.12.14 Linux x86_64**:

```bash
python3.12 -m venv ../reference_env
../reference_env/bin/python -m pip install --require-hashes -r code/journal_reference_v1/requirements-hashed.lock
../reference_env/bin/python -m pip check
PYTHONDONTWRITEBYTECODE=1 ../reference_env/bin/python -m pytest -q -p no:cacheprovider code/journal_reference_v1/tests --junitxml=../owner_junit.xml --conformance-receipt=../owner_results.json
```

For offline restoration add `--no-index --find-links ../wheelhouse` to the install command. Exact six wheels accompany the P2 review archive. No NumPy/PyTorch dependency is imported by the reference path. Legacy regression uses its separate `legacy-requirements.lock` and environment, from `code/fixed_agent_experiment_code` as cwd.

All CLI commands below use repository root as cwd, `PYTHONPATH=code`, and the isolated reference Python. `--help` is available. Exit 0 is a successful validation/conformance action; exit 2 is an input, schema, administrative-scope, numeric or I/O failure. Errors are typed JSON on stderr. No numeric strings, unknown keys, adapter aliases, implicit adapter or run purpose are accepted. The preparation layer resolves only YAML-declared defaults; the constructor requires the complete effective object.

```bash
PYTHONPATH=code ../reference_env/bin/python -m journal_reference_v1 validate-config code/journal_reference_v1/examples/UG_STRUCTURAL_C6_v1.0.json --receipt ../config_receipt.json
PYTHONPATH=code ../reference_env/bin/python -m journal_reference_v1 run-conformance code/journal_reference_v1/examples/UG_STRUCTURAL_C6_v1.0.json --authority EMBORA-U1-ADDENDUM-2026-10-04-C6-v1.1-v1.0 --acceptance-id AT-UG-CHOICE --episode-id C6-bounded-2-rounds --output ../bounded_artifact
PYTHONPATH=code ../reference_env/bin/python -m journal_reference_v1 validate-artifact ../bounded_artifact --receipt ../artifact_receipt.json
```

`validate-config` executes **zero rounds**, preserves original JSON numeric tokens/text hash, emits complete effective config/hash and runtime lock, and explicitly reports no administrative execution authorization. Confirmatory/sensitivity configs may be validated without constructing a runner. `run-conformance` permits only named S12 fixtures, normative N, structural_fixture and at most eight necessary rounds; A/B sensitivity mapping fixtures are pure helper tests, never runner trajectories. It refuses existing output directories. `validate-artifact` checks exact file set/bytes, current source inventory, config/schema/runtime bindings, complete horizon, pure observation/policy/update replay, exact event counters and trajectory hash; it executes no external game or episode. Failed/incomplete artifacts cannot pass. Dynamic runner failure preserves evidence and cannot resume.

The CLI is a per-config preparation/validation interface for later PAP binding. The acceptance of this code/environment and any future execution scope must come from Coordinator and independent audit; this owner candidate does not create accepted bindings.

`history/` preserves exact C5 near-epsilon failing test/report bytes. `contract/` remains C5; `contract_c6/` contains immutable adopted C6 input copies plus exact ZIP/manifest anchors. Active tests explicitly distinguish scientific I ±7/40 from R/B/O; O−B still uses abs/rel 1e-12. No output of the native implementation becomes an expected oracle.
