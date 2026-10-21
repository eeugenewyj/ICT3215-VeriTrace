"""Resolve exported sidecars without assuming acquisition filenames are original."""
from pathlib import PureWindowsPath
import shutil

from ..errors import ParserError


def resolve_companions(case, item, suffixes):
    found = {}
    declared = set(item.companion_item_ids)
    for candidate in case.manifest.items:
        if candidate.item_id == item.item_id:
            continue
        roles = [suffix for suffix in suffixes if
                 candidate.acquired_path.casefold() == (item.acquired_path + suffix).casefold() or
                 item.original_path and candidate.original_path and candidate.original_path.casefold() == (item.original_path + suffix).casefold()]
        if candidate.item_id in declared and not roles:
            raise ParserError(f"Cannot determine source role of declared companion {candidate.item_id}; preserve its original_path")
        if len(roles) > 1:
            raise ParserError(f"Ambiguous role for companion {candidate.item_id}")
        if roles:
            role = roles[0]
            if role in found:
                raise ParserError(f"Multiple companions supplied for {item.item_id}{role}")
            found[role] = candidate
    return found


def stage_source(case, item, folder, name, suffixes):
    folder.mkdir(parents=True, exist_ok=False)
    source = folder / name
    shutil.copyfile(case.working_root / "evidence" / item.acquired_path, source)
    companions = resolve_companions(case, item, suffixes)
    provenance, handling = [], []
    for suffix in suffixes:
        companion = companions.get(suffix)
        if companion is None:
            handling.append(f"{suffix}: not supplied; completeness/replay cannot be assumed")
        else:
            shutil.copyfile(case.working_root / "evidence" / companion.acquired_path, folder / (name + suffix))
            provenance.append({"item_id": companion.item_id, "sha256": companion.calculated_sha256, "role": suffix})
            handling.append(f"{suffix}: supplied {companion.item_id}; staged in isolated working input, see parser replay diagnostics")
    return source, provenance, handling


def registry_name(item):
    name = PureWindowsPath(item.original_path).name if item.original_path else "NTUSER.DAT"
    return name if name and ":" not in name else "NTUSER.DAT"
