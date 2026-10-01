from ..errors import IntegrityError, InputError
from .registry import supplied_files, sha256_file, check_ancestors


def verify_originals(case):
    try:
        check_ancestors(case.source_root)
        current = {p.relative_to(case.source_root).as_posix(): sha256_file(p) for p in supplied_files(case.source_root)}
    except (OSError, InputError) as exc:
        raise IntegrityError(f"Original evidence cannot be verified: {exc}") from exc
    if current != case.source_hashes:
        raise IntegrityError("Original source inventory/content changed after registration")
