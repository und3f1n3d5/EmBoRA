"""Versioned Git/source identity evidence, separate from content replay.

No network fetches. Git labels are historical metadata; immutable objects,
full tracked-byte inventory and the narrower logged-source domain are checked.
"""
from functools import lru_cache
from pathlib import Path
import hashlib
import re
import subprocess
from .schema import canonical, IdentityError, keys

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'code/journal_reference_v1/'
SUFFIXES = ('.py', '.yaml', '.md', '.csv', '.json', '.lock')
IDENTITY_ID = 'EMBORA-SOURCE-IDENTITY-C6-P2-v1.4'
INVENTORY_DOMAIN = 'all_git_tracked_paths_sha256_bytes_sorted_compact_json_v1'
LOGGED_DOMAIN = 'journal_reference_v1_suffix_filtered_sha256_sorted_compact_json_v1'


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def git(repo, *args, optional=False):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    if result.returncode:
        if optional: return None
        raise IdentityError('Git identity inspection failed: ' + args[0])
    return result.stdout


def logged_path(name):
    return name.startswith(PREFIX) and Path(name).suffix in SUFFIXES and '__pycache__' not in Path(name).parts


def worktree_inventory(repo=ROOT):
    names = git(repo, 'ls-files', '-z').split(b'\0')
    inventory = {}
    for raw in names:
        if not raw: continue
        name = raw.decode('utf-8')
        try: data = (Path(repo) / name).read_bytes()
        except OSError as exc: raise IdentityError('Tracked source file unavailable: ' + name) from exc
        inventory[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return inventory


@lru_cache(maxsize=32)
def commit_inventory(repo, commit):
    """Cache immutable Git objects only; never cache mutable worktree bytes."""
    entries = git(repo, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0')
    inventory = {}
    for entry in entries:
        if not entry: continue
        meta, raw_name = entry.split(b'\t', 1)
        mode, kind, oid = meta.split()
        if kind != b'blob' or mode not in (b'100644', b'100755'):
            raise IdentityError('Unsupported tracked source entry')
        name = raw_name.decode('utf-8')
        data = git(repo, 'cat-file', 'blob', oid.decode())
        inventory[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return inventory


def capture_source_identity(repo=ROOT):
    repo = Path(repo).resolve()
    commit = git(repo, 'rev-parse', 'HEAD').decode().strip()
    tree = git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip()
    actual = worktree_inventory(repo)
    committed = commit_inventory(str(repo), commit)
    return {'schema_id': IDENTITY_ID, 'code_tree': tree,
            'tracked_inventory_sha256': digest(actual),
            'tracked_inventory_domain': INVENTORY_DOMAIN,
            'logged_source_domain': LOGGED_DOMAIN,
            'tracked_content_matches_commit': actual == committed}


def verify_source_identity(manifest, repo=ROOT):
    """Verify the recorded identity, not equality of historical branch labels."""
    commit = manifest.get('code_commit')
    if type(commit) is not str or re.fullmatch('[0-9a-f]{40}', commit) is None:
        raise IdentityError('Malformed recorded Git commit: full lowercase SHA-1 required')
    source_hashes = manifest.get('source_hashes')
    if type(source_hashes) is not dict or digest(source_hashes) != manifest.get('code_hash'):
        raise IdentityError('Logged source hash domain is inconsistent')
    claimed = manifest.get('source_identity')
    if claimed is not None:
        keys(claimed, ('schema_id', 'code_tree', 'tracked_inventory_sha256',
                       'tracked_inventory_domain', 'logged_source_domain',
                       'tracked_content_matches_commit'), IdentityError)
        if claimed['schema_id'] != IDENTITY_ID or claimed['tracked_inventory_domain'] != INVENTORY_DOMAIN or claimed['logged_source_domain'] != LOGGED_DOMAIN:
            raise IdentityError('Unknown source identity schema/hash domain')
        if type(claimed['tracked_content_matches_commit']) is not bool:
            raise IdentityError('Tracked source match must be Boolean')
        for key, width in [('code_tree', 40), ('tracked_inventory_sha256', 64)]:
            if type(claimed[key]) is not str or re.fullmatch('[0-9a-f]{'+str(width)+'}', claimed[key]) is None:
                raise IdentityError('Malformed source identity digest')
    repo = Path(repo).resolve()
    resolved = git(repo, 'rev-parse', '--verify', commit+'^{commit}', optional=True)
    if resolved is None:
        return {'status': 'UNVERIFIED', 'recorded_commit': commit,
                'reason': 'recorded_commit_unavailable_locally',
                'strict_identity_satisfied': False}
    if resolved.decode().strip() != commit: raise IdentityError('Recorded commit resolves inconsistently')
    tree = git(repo, 'rev-parse', commit+'^{tree}').decode().strip()
    inventory = commit_inventory(str(repo), commit)
    committed_hashes = {name: row['sha256'] for name,row in inventory.items() if logged_path(name)}
    if source_hashes != committed_hashes:
        raise IdentityError('Recorded commit does not match logged source content')
    if claimed is None:
        return {'status': 'UNVERIFIED', 'recorded_commit': commit, 'recorded_tree': tree,
                'logged_source_verified': True,
                'reason': 'legacy_manifest_has_no_full_tracked_inventory_binding',
                'strict_identity_satisfied': False}
    if claimed['code_tree'] != tree or claimed['tracked_inventory_sha256'] != digest(inventory):
        raise IdentityError('Recorded commit/tree/full source inventory mismatch')
    if not claimed['tracked_content_matches_commit']:
        raise IdentityError('Recorded execution source did not match its commit')
    current = git(repo, 'rev-parse', 'HEAD', optional=True)
    current_tree = git(repo, 'rev-parse', 'HEAD^{tree}', optional=True)
    current = None if current is None else current.decode().strip()
    current_tree = None if current_tree is None else current_tree.decode().strip()
    relation = ('EXACT_COMMIT' if commit == current else
                'EQUIVALENT_TREE' if tree == current_tree else 'VERIFIED_HISTORICAL_TREE')
    # A real Git object is not by itself a binding to the files being checked.
    # Keep mutable source checks fresh, including files outside the logged
    # suffix domain. Historical labels are still not compared with HEAD labels.
    actual = worktree_inventory(repo)
    active_hashes = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((repo/PREFIX).rglob('*'))
                     if p.is_file() and logged_path(str(p.relative_to(repo)))}
    if actual != inventory or active_hashes != committed_hashes:
        return {'status': 'UNVERIFIED', 'recorded_commit': commit,
                'recorded_tree': tree, 'recorded_object_verified': True,
                'logged_source_verified': True, 'relation_to_verifier': relation,
                'verifier_commit': current, 'verifier_tree': current_tree,
                'reason': 'recorded_identity_not_bound_to_actual_verifier_source',
                'strict_identity_satisfied': False}
    return {'status': 'VERIFIED', 'recorded_commit': commit, 'recorded_tree': tree,
            'tracked_inventory_sha256': digest(inventory), 'tracked_files': len(inventory),
            'logged_source_verified': True, 'relation_to_verifier': relation,
            'verifier_commit': current, 'verifier_tree': current_tree,
            'strict_identity_satisfied': True}
