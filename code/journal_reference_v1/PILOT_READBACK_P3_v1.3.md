# P3 v1.3: initial01 schema remedy and explicit historical readback

Scientific C5/C6v1.1, numeric graph, tolerance, policies, adapters, enums,
Engine, generation artifacts and execution permission are unchanged.

The versioned PRIVATE_ROUND_SCHEMA_P3_v1.1 inventory describes both existing
operation-graph node shapes: identity=true has exactly9fields; identity=false
has exactly13fields, including left/right/total/ratio. Both objects are closed,
branch tags are Boolean constants, and native exact content replay remains
mandatory. Old schema bytes and record schema IDs remain immutable.

The ordinary validator retains strict actual-source identity semantics:
historical bytes under a changed checkout are not automatically verified.
Explicit validate --generation-source CLEAN_PARENT is read-only policy
EMBORA-P3-HISTORICAL-READBACK-v1.0. It is limited to exact initial01 plan
29fafc48ddce8ec12a2bc6f2891423a3f764a0f77d84a894e0f254d5aaee0afc,
the recorded b9bbaadd generation commit/tree/inventory and qualified runtime.
Both source checkouts must be clean and match their Git objects. Every native
manifest is strictly verified against the actual preserved generation checkout.
The current replay dependencies must be byte-identical outside the enumerated
validator/schema/test/documentation delta. They are checked again before PASS.
The receipt reports generation_source and validation_source separately.

This policy changes no artifact, manifest hash, permission, generation identity
or scientific config. It grants no new execution/recovery authority and never
sets accepted_code_binding_authorized=true. It does not cover parent/recovery
queues or other historical plans. Missing/mismatched/dirty sources fail closed.
Ordinary strict/report exits remain0success,2failure,3explicitUNVERIFIED.
Owner content/readback PASS is not independent acceptance or full R1/freeze.
