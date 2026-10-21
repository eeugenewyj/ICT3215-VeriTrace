import hashlib
import os
import shutil
import stat
from pathlib import Path, PureWindowsPath

from pydantic import ValidationError

from ..errors import InputError, IntegrityError
from .models import CaseManifest, EvidenceItem, RegisteredCase


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_reparse(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def check_ancestors(path):
    for parent in [path, *path.parents]:
        if parent.exists() and is_reparse(parent):
            raise InputError(f"Reparse/symlink path is not accepted: {parent}")


def supplied_files(root):
    result = []
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(parent) / name
            if is_reparse(path):
                raise InputError(f"Reparse/symlink entry is not accepted: {path}")
            if path.is_file():
                result.append(path)
    return sorted(result)


def safe_acquired_path(evidence, value):
    windows = PureWindowsPath(value)
    parts = value.replace("\\", "/").split("/")
    if windows.is_absolute() or windows.drive or any(p in ("", ".", "..") or ":" in p or "\x00" in p for p in parts):
        raise InputError(f"Unsafe acquired path: {value}")
    path = evidence.joinpath(*parts)
    check_ancestors(path)
    if not path.resolve().is_relative_to(evidence.resolve()):
        raise InputError("Acquired path escapes evidence directory")
    return path


def register_case(input_dir: Path, output_dir: Path) -> RegisteredCase:
    input_dir, output_dir = Path(input_dir).absolute(), Path(output_dir).absolute()
    check_ancestors(input_dir)
    check_ancestors(output_dir)
    source, working = input_dir.resolve(), output_dir.resolve()
    if source.is_relative_to(working) or working.is_relative_to(source):
        raise InputError("Evidence and output directories overlap")
    if working.exists():
        raise InputError("Run output already exists; choose a fresh directory")
    try:
        manifest = CaseManifest.model_validate_json((source / "case.json").read_bytes())
        testimony_bytes = (source / "testimony.txt").read_bytes()
        testimony = testimony_bytes.decode("utf-8")
        evidence = source / "evidence"
        if not evidence.is_dir():
            raise InputError("Missing evidence directory")
        files = supplied_files(source)
        hashes = {p.relative_to(source).as_posix(): sha256_file(p) for p in files}
        declared = {}
        for item in manifest.items:
            path = safe_acquired_path(evidence, item.acquired_path)
            if not path.is_file():
                raise InputError(f"Declared evidence file is missing: {item.acquired_path}")
            digest = hashes[path.relative_to(source).as_posix()]
            if item.supplied_sha256 and item.supplied_sha256.lower() != digest:
                raise IntegrityError(f"Supplied hash mismatch: {item.item_id}")
            key = path.relative_to(evidence).as_posix()
            declared[key] = item.model_copy(update={"acquired_path": key, "calculated_sha256": digest})
        items = list(declared.values())
        for path in files:
            if path.is_relative_to(evidence):
                key = path.relative_to(evidence).as_posix()
                if key not in declared:
                    identity = hashlib.sha256(key.encode()).hexdigest()[:24]
                    items.append(EvidenceItem(item_id="unknown_" + identity, acquired_path=key, calculated_sha256=hashes[path.relative_to(source).as_posix()]))
        manifest = manifest.model_copy(update={"items": items})
    except (OSError, UnicodeError, ValidationError) as exc:
        raise InputError(f"Cannot register case: {exc}") from exc
    working.mkdir(parents=True, exist_ok=False)
    for item in items:
        original = safe_acquired_path(evidence, item.acquired_path)
        copy = working / "evidence" / item.acquired_path
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, copy)
        if sha256_file(copy) != item.calculated_sha256:
            raise IntegrityError(f"Working copy hash mismatch: {item.item_id}")
    result = RegisteredCase(manifest=manifest, testimony=testimony, testimony_sha256=hashlib.sha256(testimony_bytes).hexdigest(), source_root=source, working_root=working, source_hashes=hashes)
    (working / "registration.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    from .integrity import verify_originals
    verify_originals(result)
    return result
