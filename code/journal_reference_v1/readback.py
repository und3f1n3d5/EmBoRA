"""Explicit, read-only compatibility for the consumed initial01 generation.

Generation bytes and validation bytes have distinct, verified identities.
This policy grants no execution/recovery authority and changes no artifact.
"""
from dataclasses import dataclass
from pathlib import Path
from .identity import ROOT, capture_source_identity, worktree_inventory, digest, git, verify_source_identity
from .evidence import runtime_hash
from .schema import IdentityError

POLICY = 'EMBORA-P3-HISTORICAL-READBACK-v1.0'
GENERATION = dict(commit='b9bbaaddc2fddb4e92bbdca24952f3566d93e470',
                  tree='325ef04e416edcd3b6fa18f059bffb242b90c87d',
                  inventory_sha256='14862b94e481d29a244d7afcaea90b30db2ae9fa1d21f82b653a4343899084d6',
                  runtime_sha256='e340a5b64c3f46d2e490264db11a3d49cc82eb12818ead960ea92dce8f50b908')
PLAN_SHA256 = '29fafc48ddce8ec12a2bc6f2891423a3f764a0f77d84a894e0f254d5aaee0afc'
PREFIX = 'code/journal_reference_v1/'
ALLOWED_DELTA = {PREFIX+p for p in ('cli.py','accounting.py','execution.py','readback.py',
    'schemas/PRIVATE_ROUND_SCHEMA_P3_v1.1.json','tests/test_pilot_readback_v13.py',
    'tests/fixtures/initial01_round81.json','PILOT_READBACK_P3_v1.3.md')}


def source(path):
    path = Path(path).resolve()
    identity = capture_source_identity(path)
    if git(path,'status','--porcelain=v1').strip() or not identity['tracked_content_matches_commit']:
        raise IdentityError('Historical readback requires clean exact source checkouts')
    return dict(commit=git(path,'rev-parse','HEAD').decode().strip(),tree=identity['code_tree'],
                inventory_sha256=identity['tracked_inventory_sha256'],runtime_sha256=runtime_hash())


@dataclass(frozen=True)
class Readback:
    generation_path: Path
    generation: dict
    validator: dict
    changed_paths: list

    def verify_manifest(self, manifest):
        if manifest.get('code_commit') != self.generation['commit']:
            raise IdentityError('Historical readback generation commit mismatch')
        return verify_source_identity(manifest, self.generation_path)

    def receipt(self):
        if source(self.generation_path) != self.generation or source(ROOT) != self.validator:
            raise IdentityError('Source changed during historical content readback')
        return dict(policy_id=POLICY,generation_source=self.generation,validation_source=self.validator,
                    unchanged_replay_dependencies=True,changed_paths=self.changed_paths,
                    execution_authorized=False,accepted_code_binding_authorized=False)


def prepare(plan, generation_path):
    if plan['source'] != GENERATION or digest(plan) != PLAN_SHA256 or plan['parent_queue'] is not None:
        raise IdentityError('Historical readback policy is limited to exact original initial01 plan')
    path = Path(generation_path).resolve()
    generation = source(path); validator = source(ROOT)
    if generation != GENERATION:
        raise IdentityError('Historical generation checkout does not match accepted source/runtime')
    if validator['runtime_sha256'] != GENERATION['runtime_sha256']:
        raise IdentityError('Historical readback runtime mismatch')
    before = worktree_inventory(path); after = worktree_inventory(ROOT)
    changed = sorted(p for p in set(before)|set(after) if before.get(p) != after.get(p))
    if not set(changed) <= ALLOWED_DELTA:
        raise IdentityError('Historical readback changed a replay dependency outside the declared validator delta')
    return Readback(path,generation,validator,changed)
