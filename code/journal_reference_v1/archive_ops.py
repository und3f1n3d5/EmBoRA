"""Small lossless batch archive/restore/retention tool. No dispatch authority.

Confirmation is an operator trust boundary: run confirm on the retained copy's
machine, then independently bring back its receipt and SHA256. No remote service.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import stat
import sys
import zipfile

VERSION = 'EMBORA-ARCHIVE-OPS-v1.0'
CHUNK = 1024 * 1024


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def hash_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(CHUNK), b''):
            h.update(chunk)
    return h.hexdigest()


def write(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        f.write(canonical(data)+'\n'); f.flush(); os.fsync(f.fileno())


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def safe_name(name):
    p = PurePosixPath(name)
    require(type(name) is str and name and '\\' not in name and '\x00' not in name and
            not p.is_absolute() and all(x not in ('', '.', '..') for x in name.split('/')),
            'Unsafe archive relative path')
    return name


def inventory(root):
    root = Path(root)
    require(not root.is_symlink() and root.is_dir(), 'Ordinary source directory required')
    files = {}; directories = []
    for p in sorted(root.rglob('*')):
        name = safe_name(p.relative_to(root).as_posix()); mode = p.lstat().st_mode
        require(not stat.S_ISLNK(mode), 'Symlink forbidden')
        if stat.S_ISDIR(mode):
            directories.append(name)
        else:
            require(stat.S_ISREG(mode), 'Special file forbidden')
            files[name] = dict(bytes=p.stat().st_size, sha256=hash_file(p))
    return dict(files=files, directories=directories)


def check_space(path, needed, reserve=0):
    require(type(needed) is int and needed >= 0 and type(reserve) is int and reserve >= 0,
            'Nonnegative integer capacity required')
    p = Path(path).absolute()
    while not p.exists():
        p = p.parent
    free = shutil.disk_usage(p).free
    require(free >= needed + reserve, f'Insufficient free space: free={free}, required={needed+reserve}')
    return dict(free_bytes=free, needed_bytes=needed, reserve_bytes=reserve)


def archive_bound(files):
    # zlib compressBound per independently deflated file + conservative ZIP64
    # headers/central directory. No compression-ratio credit.
    return 256 + sum(v['bytes'] + (v['bytes'] >> 12) + (v['bytes'] >> 14) +
                     (v['bytes'] >> 25) + 13 + 256 + 2*len(k.encode('utf-8'))
                     for k, v in files.items())


def outside(root, paths):
    root = Path(root).resolve()
    require(all(Path(p).resolve() != root and not Path(p).resolve().is_relative_to(root) for p in paths),
            'Output/evidence must be outside immutable source')


def pack(source, archive, manifest, batch_id, reserve=0):
    source, archive, manifest = map(lambda p: Path(p).absolute(), (source, archive, manifest))
    require(batch_id and type(batch_id) is str, 'Batch identity required')
    outside(source, (archive, manifest)); require(archive != manifest, 'Distinct outputs required')
    require(not archive.exists() and not manifest.exists(), 'Write-once output exists')
    before = inventory(source)
    capacity = check_space(archive.parent, archive_bound(before['files']) + len(canonical(before).encode()) + 65536, reserve)
    # A partial archive is preserved on error; no automatic retry or deletion.
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for name in before['files']:
            check_space(archive.parent, 0, reserve)
            with (source/name).open('rb') as f, z.open(name, 'w', force_zip64=True) as dst:
                for chunk in iter(lambda: f.read(CHUNK), b''):
                    check_space(archive.parent, len(chunk) + 65536, reserve)
                    dst.write(chunk)
    with archive.open('rb') as f:
        os.fsync(f.fileno())
    require(inventory(source) == before, 'Source changed during archive')
    out = dict(schema_id=VERSION, batch_id=batch_id, source_host=socket.gethostname(), source_root=str(source.resolve()),
               source_archive=str(archive.resolve()), payload=before, compression='ZIP_DEFLATED_6',
               archive_bytes=archive.stat().st_size, archive_sha256=hash_file(archive), capacity=capacity)
    verify_archive(archive, out)
    write(manifest, out)
    return out


def verify_archive(archive, manifest):
    require(manifest['schema_id'] == VERSION and manifest['compression'] == 'ZIP_DEFLATED_6', 'Unknown archive contract')
    require(Path(archive).stat().st_size == manifest['archive_bytes'] and
            hash_file(archive) == manifest['archive_sha256'], 'Archive byte hash/size mismatch')
    files = manifest['payload']['files']
    for name in list(files) + manifest['payload']['directories']:
        safe_name(name)
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        require(len(infos) == len(files) and len({i.filename for i in infos}) == len(infos) and
                {i.filename for i in infos} == set(files), 'Archive exact file-set mismatch')
        for info in infos:
            require(info.compress_type == zipfile.ZIP_DEFLATED and info.file_size == files[info.filename]['bytes'],
                    'Archive method/size mismatch')
            h = hashlib.sha256()
            with z.open(info) as f:
                for chunk in iter(lambda: f.read(CHUNK), b''):
                    h.update(chunk)
            require(h.hexdigest() == files[info.filename]['sha256'], 'Payload hash mismatch')
        require(z.testzip() is None, 'Archive CRC failure')
    return True


def restore(archive, manifest_path, destination, receipt, reserve=0):
    manifest = read(manifest_path); verify_archive(archive, manifest)
    destination = Path(destination).absolute()
    outside(destination, (archive, manifest_path, receipt))
    if manifest['source_host'] == socket.gethostname():
        outside(manifest['source_root'], (destination, receipt))
    require(not destination.exists() and not Path(receipt).exists(), 'Fresh restore/receipt required')
    payload = manifest['payload']; total = sum(v['bytes'] for v in payload['files'].values())
    capacity = check_space(destination.parent, total + 4096*(len(payload['files']) + len(payload['directories']) + 2), reserve)
    destination.mkdir()
    for name in payload['directories']:
        (destination/safe_name(name)).mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for name in payload['files']:
            dst = destination/safe_name(name); dst.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as src, dst.open('xb') as f:
                for chunk in iter(lambda: src.read(CHUNK), b''):
                    check_space(destination, len(chunk)+4096, reserve); f.write(chunk)
                f.flush(); os.fsync(f.fileno())
    require(inventory(destination) == payload, 'Restored bytes/file-set differ')
    out = dict(schema_id=VERSION, status='RESTORE_VERIFIED', batch_id=manifest['batch_id'],
               manifest_sha256=hash_file(manifest_path), archive_sha256=manifest['archive_sha256'],
               restored_root=str(destination.resolve()), capacity=capacity)
    write(receipt, out)
    return out


def confirm(archive, manifest_path, restored, receipt, copy_id, acknowledge):
    require(acknowledge is True and type(copy_id) is str and copy_id.strip(), 'Explicit retained-copy acknowledgement required')
    manifest = read(manifest_path); verify_archive(archive, manifest)
    if manifest['source_host'] == socket.gethostname():
        outside(manifest['source_root'], (receipt,))
    require(inventory(restored) == manifest['payload'], 'External restore must match payload')
    original = (manifest['source_host'], manifest['source_archive'])
    require((socket.gethostname(), str(Path(archive).resolve())) != original, 'Original archive is not an external retained copy')
    if original[0] == socket.gethostname() and Path(original[1]).exists():
        require(not os.path.samefile(archive, original[1]), 'Hardlink is not a separate retained copy')
    outside(Path(restored), (archive, manifest_path, receipt))
    out = dict(schema_id=VERSION, status='EXTERNAL_COPY_CONFIRMED', batch_id=manifest['batch_id'],
               manifest_sha256=hash_file(manifest_path), archive_sha256=manifest['archive_sha256'],
               copy_id=copy_id, host=socket.gethostname(), archive_path=str(Path(archive).resolve()),
               restored_root=str(Path(restored).resolve()), operator_acknowledged=True)
    write(receipt, out)
    return out


def cleanup(source, archive, manifest_path, restored, restore_receipt, confirmation, trusted_confirmation_sha256,
            receipt, acknowledge=False, remove_archive=False):
    require(acknowledge is True, 'Explicit cleanup acknowledgement required')
    require(hash_file(confirmation) == trusted_confirmation_sha256, 'Independently pinned external confirmation required')
    m = read(manifest_path); c = read(confirmation); r = read(restore_receipt)
    verify_archive(archive, m)
    for evidence, status in ((c, 'EXTERNAL_COPY_CONFIRMED'), (r, 'RESTORE_VERIFIED')):
        require(evidence['schema_id'] == VERSION and evidence['status'] == status and
                evidence['batch_id'] == m['batch_id'] and evidence['manifest_sha256'] == hash_file(manifest_path) and
                evidence['archive_sha256'] == m['archive_sha256'], 'Stale/wrong batch or verification evidence')
    require(c['operator_acknowledged'] is True and c['copy_id'] and
            (c['host'], c['archive_path']) != (m['source_host'], m['source_archive']), 'No retained external copy acknowledgement')
    source, restored = Path(source).absolute(), Path(restored).absolute()
    require(str(source.resolve()) == m['source_root'] and str(restored.resolve()) == r['restored_root'], 'Cleanup path binding mismatch')
    require(source != restored and not source.resolve().is_relative_to(restored.resolve()) and
            not restored.resolve().is_relative_to(source.resolve()), 'Overlapping cleanup roots forbidden')
    for root in (source, restored):
        require(root.resolve() != Path(root.anchor) and not Path.cwd().resolve().is_relative_to(root.resolve()), 'Unsafe cleanup root')
        outside(root, (archive, manifest_path, restore_receipt, confirmation, receipt))
        require(inventory(root) == m['payload'], 'Working copy changed; cleanup denied')
    if c['host'] == socket.gethostname():
        # A locally reachable external mount/copy can be checked again. A remote
        # laptop receipt instead rests on the explicit independently pinned ack.
        external = Path(c['archive_path'])
        require(external.resolve() != Path(archive).resolve() and
                not any(external.resolve().is_relative_to(root.resolve()) for root in (source, restored)),
                'Retained copy overlaps redundant copies')
        require(hash_file(external) == m['archive_sha256'] and not os.path.samefile(external, archive),
                'Retained local copy no longer matches')
    require(not Path(receipt).exists(), 'Write-once cleanup receipt exists')
    # Operator must quiesce this batch; this small tool is not a process manager.
    # Intent survives a partial deletion error, and no evidence is auto-repaired.
    intent = Path(str(receipt)+'.intent.json')
    write(intent, dict(schema_id=VERSION, status='CLEANUP_INTENT', batch_id=m['batch_id'],
                       manifest_sha256=hash_file(manifest_path), confirmation_sha256=trusted_confirmation_sha256,
                       source=str(source), restored=str(restored), remove_archive=remove_archive))
    shutil.rmtree(source); shutil.rmtree(restored)
    if remove_archive:
        Path(archive).unlink()
    out = dict(schema_id=VERSION, status='REDUNDANT_COPIES_REMOVED', batch_id=m['batch_id'],
               manifest_sha256=hash_file(manifest_path), confirmation_sha256=trusted_confirmation_sha256,
               archive_removed=remove_archive, intent_sha256=hash_file(intent))
    write(receipt, out)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    pack_p = sub.add_parser('pack')
    for name in ('source', 'archive', 'manifest', 'batch-id'):
        pack_p.add_argument('--'+name, required=True)
    pack_p.add_argument('--reserve-bytes', type=int, required=True)
    restore_p = sub.add_parser('restore')
    for name in ('archive', 'manifest', 'destination', 'receipt'):
        restore_p.add_argument('--'+name, required=True)
    restore_p.add_argument('--reserve-bytes', type=int, required=True)
    confirm_p = sub.add_parser('confirm')
    for name in ('archive', 'manifest', 'restored', 'receipt', 'copy-id'):
        confirm_p.add_argument('--'+name, required=True)
    confirm_p.add_argument('--acknowledge-retained', action='store_true')
    cleanup_p = sub.add_parser('cleanup')
    for name in ('source', 'archive', 'manifest', 'restored', 'restore-receipt', 'confirmation', 'confirmation-sha256', 'receipt'):
        cleanup_p.add_argument('--'+name, required=True)
    cleanup_p.add_argument('--acknowledge-cleanup', action='store_true')
    cleanup_p.add_argument('--remove-archive', action='store_true')
    space_p = sub.add_parser('space')
    space_p.add_argument('--path', required=True); space_p.add_argument('--needed-bytes', type=int, required=True)
    space_p.add_argument('--reserve-bytes', type=int, required=True)
    args = vars(p.parse_args(argv)); command = args.pop('command')
    try:
        if command == 'pack':
            out = pack(args['source'], args['archive'], args['manifest'], args['batch_id'], args['reserve_bytes'])
        elif command == 'restore':
            out = restore(args['archive'], args['manifest'], args['destination'], args['receipt'], args['reserve_bytes'])
        elif command == 'confirm':
            out = confirm(args['archive'], args['manifest'], args['restored'], args['receipt'], args['copy_id'], args['acknowledge_retained'])
        elif command == 'cleanup':
            out = cleanup(args['source'], args['archive'], args['manifest'], args['restored'], args['restore_receipt'],
                          args['confirmation'], args['confirmation_sha256'], args['receipt'], args['acknowledge_cleanup'], args['remove_archive'])
        else:
            out = check_space(args['path'], args['needed_bytes'], args['reserve_bytes'])
        print(canonical(out)); return 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError) as e:
        print(canonical(dict(status='FAIL', error_type=type(e).__name__, message=str(e))), file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
