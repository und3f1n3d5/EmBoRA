# EmBoRA pre-rent executable preparation v1.0

Parent: d7672956730b5693c1eec3cfd297952c8c065cda, tree
ab4825081be1f7812701e1e2fa645a05aba3e95d. The delivery's external source receipt
identifies the exact executable successor, inventory, runtime and actual tests.
No permission, new trajectory, rental, U2, freeze, merge or release follows.

## Adopted readout and compatibility

Author disposition 2026-11-08 adopts fixed alternative divisor 4. Protocol binding:
ALT_READOUT4_v1.0.json. Canonical PAP bytes/hash remain unchanged. New interface
EMBORA-ADMITTED-ALTERNATIVES-C6-v1.1 and ALTERNATIVES_C6_v1.1.json wrap the unchanged
admitted analysis export. They require actual strict native validation, exact
analysis/runtime/admission/PAP pins and whole-group selection before extraction.
Generation and validation identities remain separate. The validator checkout
remains deea6aa72e003da646887e2a41029fbf2ef9c506; do not rebind generation to this
analysis successor. Rebind only the downstream admission's analysis_source and
its external raw digest after reviewing that integration binding.

All 27 lambda and 3 signed component readouts use full-minus-comparison raw Q /4,
mean post-round t=1..T and cutoff 1e-9 with equality tied. Primary Q/4, physical
delta_S, payoff divisors 5/3/8, five categories, windows, other registered axes
and scientific inventory are unchanged. Components are Wtilde, m and -f. No
natural-range scaling, configurable divisor or feedback into policy. Production
eligibility is only primary T200/N/confirmatory_frame single-switch contrasts;
bounded structural controls are separately labelled SYNTHETIC_TEST_ONLY.
Kind and other-scope contrast IDs are explicitly excluded. Missing/invalid full
invalidates all dependent alternatives; all-cell denominators are preserved.

Old ANALYSIS_C6_v1.0 exports remain byte/schema compatible, including their null
alternative fields. New normalized outputs are in the versioned wrapper rows
and cells. Cells report all expected members, D and all five category fractions;
incomplete cells have unavailable aggregates. This delta does not introduce a
new persistence estimand or complete all other PAP sensitivity summaries.

## Installation and read-only export

Use the exact successor SHA and native SHA from the delivery source receipt.
Never use a moving branch as the source identity. Example shell setup:

```sh
git clone https://github.com/und3f1n3d5/EmBoRA.git EmBoRA
git -C EmBoRA checkout --detach "$SOURCE_COMMIT"
git -C EmBoRA status --porcelain=v1
git -C EmBoRA worktree add --detach ../native deea6aa72e003da646887e2a41029fbf2ef9c506
python3.12 -m venv reference_env
reference_env/bin/python -m pip install --require-hashes -r EmBoRA/code/journal_reference_v1/requirements-hashed.lock
reference_env/bin/python -m pip check
export PYTHONPATH="$PWD/EmBoRA/code" PYTHONDONTWRITEBYTECODE=1
```

An installation alone does not qualify a future host. Record actual runtime_hash
and the normal runtime qualification; do not substitute an old runtime string.
Saved native inputs require their actual compatible runtime. The delivery records
how the existing 2.39 reference libc was isolated from the current 2.41 host for
synthetic saved-content replay; it does not silently relabel native metadata.

```sh
"$PY" -m journal_reference_v1.alternative_export export \
  --admission "$ADMISSION" --admission-sha256 "$TRUSTED_ADMISSION_SHA256" \
  --protocol "$PAP" --validator-source "$NATIVE_CHECKOUT" --python "$NATIVE_PY" \
  --output "$ALTERNATIVE_EXPORT"
"$PY" -m journal_reference_v1.alternative_export verify \
  --admission "$ADMISSION" --admission-sha256 "$TRUSTED_ADMISSION_SHA256" \
  --protocol "$PAP" --validator-source "$NATIVE_CHECKOUT" --python "$NATIVE_PY" \
  --output "$ALTERNATIVE_EXPORT"
```

All variables must be supplied from reviewed bindings; this does not create an
admission or authority. Exit 0 means complete admitted export; rejection or
incomplete export is 2. This wrapper does not accept native UNVERIFIED identity.
Native validator 0/2/3 behavior is untouched. Export files are write-once and
outside native inputs; verify recomputes native checks and the entire wrapper.

## Operations annex — DRAFT for Coordinator adoption

One sequential batch at a time; reuse the existing 258 allocations and all
scientific pairing/order. No scheduler. This tool preserves ordinary file names,
contents and directory composition, including empty directories and failure
evidence; it is not a POSIX metadata/ACL backup. It rejects symlinks/special files.
Do not mutate immutable native files to fit an archive layout.

Order: quiescent completed/stopped batch -> mandatory native validation with
saved stdout/stderr/exits -> DEFLATE level-6 lossless archive -> exact restoration
and readback -> retained external/laptop copy verified there -> explicit trusted
confirmation -> cleanup of redundant copies. Failed/partial data follow the
same retention path but remain failed and halt dispatch. Nothing here resumes or
repairs a queue, creates permission, or converts an archive PASS into native PASS.

For the existing reconcile_native checkpoint, native.zip must contain exactly
the queue's native/admin relative file set. The helper emits only file members;
empty directories are recorded in its external manifest. Archive the companion
external validation/accounting logs separately as evidence.zip with a separate
manifest. Treat these as one batch archive set without another large outer ZIP.
Verify/confirm BOTH before cleaning either; retain their small manifests,
validation/checkpoint/ledger/confirmation/cleanup receipts independently. Reuse
the unchanged actual native reconcile_native/audit path before any next
reservation. Failed/unresolved/late-failure checkpoints remain blocked.

All destinations/receipts are new paths. Keep an explicit reserve on each volume;
the example 1 GiB is a proposed operating reserve, not an approved native cap.
Measure actual free bytes/inodes first. No guaranteed compression ratio is used.

```sh
"$PY" -m journal_reference_v1.archive_ops space --path "$BATCH_VOLUME" \
  --needed-bytes "$BATCH_WORKING_BOUND" --reserve-bytes 1073741824
"$PY" -m journal_reference_v1.archive_ops pack \
  --source "$QUEUE" --archive "$ARCHIVE" --manifest "$MANIFEST" \
  --batch-id "$BATCH_ID" --reserve-bytes 1073741824
"$PY" -m journal_reference_v1.archive_ops restore \
  --archive "$ARCHIVE" --manifest "$MANIFEST" --destination "$RESTORE" \
  --receipt "$RESTORE_RECEIPT" --reserve-bytes 1073741824
```

Copy archive and manifest to the laptop (and repeat for evidence.zip), then run
there with locally verified code/interpreter. The copy directory must be outside
all server cleanup roots. This is an explicit operator trust boundary, not a
remote attestation service. A copied empty receipt/template or transfer exit 0
does not confirm retention. Archive verification checks archive SHA256/size,
unique exact file-set, per-file size/SHA256, method and CRC.

```sh
"$LAPTOP_PY" -m journal_reference_v1.archive_ops restore \
  --archive "$LAPTOP_ARCHIVE" --manifest "$LAPTOP_MANIFEST" \
  --destination "$LAPTOP_READBACK" --receipt "$LAPTOP_RESTORE_RECEIPT" \
  --reserve-bytes 1073741824
"$LAPTOP_PY" -m journal_reference_v1.archive_ops confirm \
  --archive "$LAPTOP_ARCHIVE" --manifest "$LAPTOP_MANIFEST" \
  --restored "$LAPTOP_READBACK" --receipt "$LAPTOP_CONFIRMATION" \
  --copy-id "$RETAINED_COPY_ID" --acknowledge-retained
sha256sum "$LAPTOP_CONFIRMATION"
```

Bring back the confirmation and independently obtained SHA256. Quiesce the batch
and explicitly identify only its redundant server copies. The tool is not a
writer/process detector: the cleanup acknowledgement includes operator assurance
that the batch is inactive and both archive-set members are retained. The helper
rehashes source, restored and local archive bytes; stale/missing/wrong confirmation
or changed files reject before deletion. Locally reachable retained copies are
checked again and cannot be hardlinks or overlap deletion roots. Remote retention
rests on the independently pinned operator confirmation. Preserve that boundary.

```sh
"$PY" -m journal_reference_v1.archive_ops cleanup \
  --source "$QUEUE" --archive "$ARCHIVE" --manifest "$MANIFEST" \
  --restored "$RESTORE" --restore-receipt "$RESTORE_RECEIPT" \
  --confirmation "$COPIED_LAPTOP_CONFIRMATION" \
  --confirmation-sha256 "$INDEPENDENT_CONFIRMATION_SHA256" \
  --receipt "$CLEANUP_RECEIPT" --acknowledge-cleanup --remove-archive
```

Only the bound source/restored directories and optionally local archive are
removed. Manifest/confirmation/restoration/cleanup/intent records remain outside
those roots. An intent record survives partial deletion errors; STOP and inspect,
no automatic cleanup retry. A partial archive/restore on I/O or capacity failure
also remains for diagnosis; no original is deleted. Never clean an only retained
copy or trim mandatory logs to fit a disk. The acknowledged laptop copy is final
retention; future analysis restores it, checks hashes/CRC/native provenance, then
uses the admitted exporter without replacing generation identity or failed data.

## Disk arithmetic without compression credit

For largest proposed raw cap B=44 GiB=47,244,640,256 bytes and an illustrative
planning envelope of at most 4096 files with UTF-8 relative names <=1024 bytes:

    Z = B + (B>>12) + (B>>14) + (B>>25)
        + 4096*(13 + 256 + 2*1024) + 256
      = 47,268,550,272 bytes

This conservatively covers per-file deflate expansion and ZIP64 headers, not a
forecast of compression. The actual tool computes its bound from actual input
file lengths/names, checks available capacity before output and during streaming,
and preserves originals/partial outputs on shortage. Exceeding the illustrative
inventory/evidence envelope requires recalculation, not omission of files.

Raw + archive + full restore = 2B+Z =141,757,830,784 bytes. Add a DRAFT 64 MiB
metadata/companion-evidence/filesystem allowance and 8 GiB OS/source/runtime
envelope: 150,414,874,240 usable bytes. Add any separately chosen free reserve
(e.g. 1 GiB ->151,488,616,064 bytes). Measure companion evidence and allocation
overhead; 64 MiB is a planning allowance, not a proved bound on failed evidence.

Nominal 150 decimal GB falls short by 414,874,240 bytes even before the additional
free reserve under these assumptions. Arithmetic whole-GB minimum is 151 GB
without that extra reserve, or 152 GB with 1 GiB reserve; neither is a guaranteed
provider filesystem capacity. Candidate recommendation: 160 GB, actual available
bytes/inodes checked. Before a batch require at least 141,824,939,648 free bytes
plus chosen reserve, plus any excess companion evidence/metadata. Do not subtract
OS already occupied from df free twice. A 150 GiB offer differs from 150 GB.

4 vCPU/8 GB, one worker, no GPU/RAID/paid backup remains a candidate, not a measured
host guarantee. Native RSS proposals do not qualify the OS. Serialize validation,
archive and restoration. The laptop must have measured free space for cumulative
retained archives and restoration; nominal 1 TB does not establish sufficient
worst-case retention of all batches. STOP before capacity exhaustion. No historic
compression ratio, five-day throughput or new-host cost guarantee is assumed.
