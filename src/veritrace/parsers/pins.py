import shutil
from pathlib import Path

from ..cases.registry import check_ancestors, sha256_file
from ..errors import DependencyError


def pinned_command(command, hashes):
    """Resolve before changing parser cwd; never launch an unpinned PATH entry."""
    if not hashes:
        raise DependencyError("Parser executable/source hashes are missing")
    pins = {}
    for name, digest in hashes.items():
        path = Path(name).absolute()
        check_ancestors(path)
        if not path.is_file() or sha256_file(path) != digest:
            raise DependencyError("Pinned parser dependency is missing or changed")
        pins[str(path.resolve()).casefold()] = digest
    executable = shutil.which(command[0])
    if executable is None:
        raise DependencyError("Parser executable cannot be resolved")
    resolved = []
    for number, part in enumerate(command):
        if part in ("-m", "-c", "-", "--command"):
            raise DependencyError("Use a pinned executable/script entry point; module/inline dispatch is unsupported")
        path = Path(executable if number == 0 else part).absolute()
        if number == 0 or path.is_file():
            check_ancestors(path)
            identity = str(path.resolve())
            if identity.casefold() not in pins:
                raise DependencyError(f"Command file is not pinned: {identity}")
            resolved.append(identity)
        elif not part.startswith("-"):
            raise DependencyError(f"Command argument is not a pinned file: {part}")
        else:
            resolved.append(part)
    return resolved
