# Reproduce bounded C6 P2 v1.4 audit repair

Use the exact delivery commit/tree, never a moving branch without verifying its
identity. The source recovery bundle retains the reviewed published history
and original local history. Use CPython 3.12.14 on compatible Linux x86_64;
runtime/FP qualification is required and must not be bypassed.

Create the reference environment separately, using the six reference wheels:

```bash
python3.12 -m venv ../reference_env
../reference_env/bin/python -m pip install --no-index --find-links ../reference_wheelhouse --require-hashes -r code/journal_reference_v1/requirements-hashed.lock
../reference_env/bin/python -m pip check
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../reference_env/bin/python -m pytest -q -p no:cacheprovider code/journal_reference_v1/tests --junitxml=../reference.xml --conformance-receipt=../reference_counts.json
```

Extract the complete legacy dependency archive into a sibling delivery
directory. Its wheel manifest records all exact artifacts, original observed
download origins, compatible tags, dependency closure and SHA-256 values.
Create a fresh legacy environment; do not reuse the reference environment:

```bash
python3.12 -m venv ../legacy_env
../legacy_env/bin/python -m pip install --no-index --find-links ../legacy_delivery/wheelhouse --require-hashes -r code/journal_reference_v1/legacy-requirements-hashed.lock
../legacy_env/bin/python -m pip check
cd code/fixed_agent_experiment_code
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../../../legacy_env/bin/python -m pytest -q -p no:cacheprovider tests --junitxml=../../../legacy.xml
```

The original unhashed legacy lock is retained; its pinned versions must match
the hash-pinned companion and installed receipt. Standard venv bootstrap pip
is recorded separately. No replacement versions, stubs or test skips are
permitted. Full legacy replay remains mandatory for the independent Reviewer.

From repository root, existing bounded CLI authority is unchanged:

```bash
PYTHONPATH=code ../reference_env/bin/python -m journal_reference_v1 validate-config code/journal_reference_v1/examples/UG_STRUCTURAL_C6_v1.0.json --receipt ../config.json
PYTHONPATH=code ../reference_env/bin/python -m journal_reference_v1 run-conformance code/journal_reference_v1/examples/UG_STRUCTURAL_C6_v1.0.json --authority EMBORA-U1-ADDENDUM-2026-10-04-C6-v1.1-v1.0 --acceptance-id AT-UG-CHOICE --episode-id targeted-recheck --output ../new-bounded-artifact
PYTHONPATH=code ../reference_env/bin/python -m journal_reference_v1 validate-artifact ../new-bounded-artifact --receipt ../artifact.json
```

Never reuse write-once output paths. Strict validation exits 2 for invalid or
unverified required identity. Explicit `--identity-requirement report` permits
compatible content replay with unverified identity but exits 3 and never
authorizes binding. Read API_SCHEMA_C6_P2_v1.4.md for schemas/hash domains.
These commands execute only named conformance fixtures, not paper runs.
