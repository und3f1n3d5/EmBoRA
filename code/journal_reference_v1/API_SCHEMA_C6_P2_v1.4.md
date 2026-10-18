# C6 P2 v1.4 implementation interface changes

This is an implementation/reproducibility repair under adopted C6 v1.1, not
a scientific or numerical revision. Frozen scientific sources and existing
implementation schemas remain unchanged. New manifests use
`EMBORA-MANIFEST-C6-P2-v1.4`, `MANIFEST_SCHEMA_C6_v1.4.json` and
`EMBORA-SOURCE-IDENTITY-C6-P2-v1.4`.

JSON `-0` alone is preserved as a negative binary64 zero; other integer-shaped
tokens remain Python integers. Real fields retain the sign through conversion
and serialization. Integer fields still require exact Python int: Boolean,
float, and the special negative real zero are rejected without coercion.
Original text/token lineage and canonical effective-config hashes remain
separate. Config-validator interface is `EMBORA-CONFIG-VALIDATOR-C6-v1.1`.

New `source_identity` records the full Git tree, SHA-256 inventory of all
tracked path bytes/sizes (sorted compact JSON), its explicit domain, the narrow
logged-source domain, and whether actual tracked bytes match the recorded
commit. The full inventory is independent of the suffix-filtered `source_hashes`
and `code_hash`. The latter covers .py/.yaml/.md/.csv/.json/.lock beneath
code/journal_reference_v1, excluding __pycache__. Tree hashes include Git modes;
the separately named SHA-256 inventory includes path/bytes/SHA-256 entries.

Artifact-validator interface `EMBORA-ARTIFACT-VALIDATOR-C6-v1.1` separates full
content replay from recorded Git identity. It rejects malformed commits and
available commits inconsistent with logged content, full inventory or tree.
Available recorded objects are checked locally, without network fetches.
Immutable objects may be cached; mutable worktree bytes are never cached.
Historical branch/dirty labels are descriptive, not compared with today's
checkout labels. Different commits with equivalent trees are explicitly
identified. Actual tracked bytes and active logged-domain files must match the
recorded tree/inventory for strict binding. A valid historical Git object whose
source differs from the actual verifier files is reported as UNVERIFIED until
its exact/equivalent source is checked out. Mutable source is checked anew on
every verification, even when immutable Git objects are cached.

`validate-artifact` defaults to `--identity-requirement required`: missing or
unverified identity is a typed failure, exit 2. Explicit `report` mode permits
content replay of a missing commit or legacy v1.0 manifest, reports
`CONTENT_VALID_IDENTITY_UNVERIFIED` and exits 3, never ordinary PASS/exit 0.
Available inconsistent or malformed identity still fails in report mode.
Legacy manifests lack full tracked-inventory binding; verifying their available
commit and narrow logged source is reported separately and cannot satisfy the
new strict identity requirement. Current engine emission always uses v1.4.

Verified identity plus successful content replay returns PASS/exit 0, with
explicit `strict_identity_satisfied`. Every receipt keeps
`accepted_code_binding_authorized=false`: neither a content PASS nor an identity
PASS grants Coordinator acceptance, PAP binding, code freeze or run authority.
Validation executes no external game rounds. Scientific config enums and
conformance scope remain unchanged.
