# Victim acquisition rehearsal

## Latest controlled acquisition: 14 November 2026

The owner completed the jumplist01 Notepad experiment, captured RAM, verified
the desktop transfer and shut down the victim. The new stopped-VM preservation
contains 339 files with matching source/copy SHA-256 values. Its current disk
descriptor is .runs/disk-jumplist01/vm-preserved/Windows 10 Pro x64-000005.vmdk,
with all required parents and extents. The owner demonstrated FTK filesystem
access and exported four automatic and four custom Jump Lists plus two NTFS
index extras. All 20 parsed records matched independent source checks. Focused
genuine Agent 1/2 runs and the acquired integration test subsequently passed.
See [current implementation status](implementation-status.md) and
[Jump List contribution](jumplist-contribution.md) for evidence and limitations.
RAM remains preserved for later analysis; source completeness and formal
classification evaluation remain acceptance work.

## Historical rehearsal: 2–3 October 2026

The following records the earlier acquisition and its procedure. Its 000004
descriptor belongs to that preserved rehearsal, not the November case.
The owner completed
one victim RAM capture on 2 October 2026; desktop review verified its log and
matching transferred dump hash. A powered-off VM preservation copy was completed
and verified at 17:08 SGT. The owner then opened the preserved current disk in
FTK Imager and supplied a screenshot showing its NTFS filesystem, Windows and
Users/eugene directories. NTUSER.DAT with both logs and Default History have now
been exported. UserAssist's independent comparison passed; Edge needs a nonempty
sample. LNK, Jump List and Prefetch exports have now been received and hashed;
their source comparisons subsequently passed. Two Recycle Bin metadata/content pairs
were subsequently received after an owner directory-export warning; their native
comparison also passed; source-folder completeness remains unconfirmed.
Development happens on the desktop, which also hosts the victim VM and local model.
The physical spare SSD is excluded.

## Before generating a case

Record VMware 17.6.1 product/edition, the actual experiment snapshot identity,
Windows 10 Pro build, Edge version, account/SID, disk encryption status,
security settings and guest/host clock observations. The recorded baseline
is in the design. Check clock alignment after every snapshot restoration.
Check space for the VM, complete disk copies, model weights and RAM dumps.

Install acquisition utilities before freezing a new experiment baseline and
record that change. Ground-truth logs stay on the investigator machine, outside
the case folder supplied to the agents. Start with harmless actions:

1. Download a known PDF in Edge; record URL, resulting path and hash.
2. Open the downloaded local PDF in Edge; distinguish this from viewing a URL.
3. Launch Notepad through the GUI.
4. Delete that PDF into the Recycle Bin.

Record action times, account, observed outcomes and uncertainty independently.
Testimony may include true, false, negated, partly true and unclear claims.

## RAM preservation

Capture before shutdown/restart. [WinPmem's official instructions](https://github.com/Velocidex/WinPmem)
describe the standalone x64 executable and raw capture. Test a signed release
on a disposable experiment; retain its version, hash, driver/capture result and
start/end times. The [official release notes](https://github.com/Velocidex/WinPmem/releases)
inspected for this rehearsal designate go-winpmem_amd64_1.0-rc2_signed.exe for production use;
the newer 4.1 test driver requires test-signing mode. Use the designated signed
build for the rehearsal under the existing victim security settings. Keep its
host copy in .external/acquisition/winpmem and stage it in C:\Tools\Acquisition
inside the victim. Record that staging before freezing the experiment baseline.

The designated Go executable is now present on the desktop; help checks passed
and its embedded driver's signature was verified as valid. The outer executable
reports NotSigned. The owner subsequently staged the tool and captured RAM:
the retained October log shows driver service start, imaging completion, service stop
and exit code 0. The 5 GiB dump's desktop SHA-256 matches the guest checksum and
transcript. Files are in .runs/acquisition-rehearsal01/rehearsal01/, with the
verification record at .runs/acquisition-rehearsal01/verification.json.
VMware subsequently showed current snapshot "Acquisition-ready baseline", UID 3.
Historical linkage of that snapshot to the RAM capture and the security-setting
record remain unconfirmed. No RAM content analysis or export/parser validation
is credited by this check.
Retain the selected binary's -h output and rehearse its raw capture inside the
disposable victim. CLI arguments differ between the Go and mini imagers. For
the selected Go executable, run inside the victim's administrator terminal:

```powershell
& 'C:\Tools\Acquisition\go-winpmem_amd64_1.0-rc2_signed.exe' acquire --compression none --progress 'C:\Acquisition\dev01\physmem.raw'
if ($LASTEXITCODE -ne 0) { throw 'RAM capture failed; retain diagnostic output.' }
Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\Acquisition\dev01\physmem.raw'
```

Choose and record the actual output destination with sufficient space. Live
capture creates traces; document its effect and transfer the preserved dump to
the investigator. A failed capture is recorded as failed. Do not silently alter
the victim's baseline security configuration to make a tool run. RAM analysis
is outside this prototype.
The [tool setup procedure](tools-setup.md) includes staging hashes and a
rehearsal command sequence retaining capture times, exit status and transcript.

## Disk preservation and export

After RAM capture, stop the victim cleanly and record that shutdown. Preserve
the **complete required VM/disk snapshot chain** on the investigator's storage.
A snapshot alone is not an acquisition, and a lone base VMDK may omit changes
stored in child disks. Hash and inventory the retained files before further work.

The owner shut down the victim after the RAM rehearsal. vmrun reported zero
running VMs, no vmware-vmx process remained and checkpoint.vmState was empty.
The desktop session then copied the VM directory from
C:\Users\eugen\Documents\Virtual Machines\Windows 10 Pro x64 to
.runs/disk-rehearsal01/vm-preserved. All 309 included files (52,148,970,552 bytes,
about 48.57 GiB) have matching independently computed source/copy SHA-256 values.
Source size/write-time metadata stayed unchanged and the VM was stopped at all
state checks. Only the transient .vmx.lck configuration-lock directory was
excluded; disk/snapshot files, saved snapshot memory and metadata were retained.
The source lock was not deleted. Copy and hash records are in
.runs/disk-rehearsal01/preservation.json and sha256-manifest.json.

The preserved configuration selects Windows 10 Pro x64-000004.vmdk. Its parent
chain is 000004 -> 000002 -> 000001 -> the base Windows 10 Pro x64.vmdk.
All four descriptors and 64 required split extents are present, parent CIDs match
and references stay inside the preserved folder. The configured disk capacity
is 60 GiB. Current VM configuration reports 4 GiB RAM and four virtual CPUs;
the earlier approved baseline report recorded two virtual CPUs. Retain this
observed configuration difference with the experiment record. The current
snapshot metadata names "Acquisition-ready baseline" (UID 3), with ancestors
"updated" and "initial setup". This observation does not independently prove
which snapshot was restored before the earlier capture.

Use the installed [FTK Imager](https://www.exterro.com/digital-forensics-software/ftk-imager)
on a preserved copy. Record its version and demonstrate access to the victim
filesystem before collecting evaluation cases. If that reader cannot open the
preserved representation, validate and document a copy-only conversion/access
procedure first. The observed representation is a split sparse VMware disk
with snapshot parents. The owner-run FTK filesystem-access check has now passed.
This is manual acquisition;
VeriTrace does not yet ingest disk images directly.

For the recorded October owner-run FTK access check on the desktop:

1. Open FTK Imager and choose File -> Add Evidence Item -> Image File.
2. Select the preserved current descriptor, not a split extent or base snapshot:
   C:\Users\eugen\Github\ICT3215-VeriTrace\.runs\disk-rehearsal01\vm-preserved\Windows 10 Pro x64-000004.vmdk.
3. Check whether its Windows volume and Users directory are readable. Merely
   adding an item without a readable filesystem is not a passed access check.
4. If it works, export supported sources and record original paths/hashes.
   If this split snapshot representation is unsupported, retain the exact
   message and resolve a copy-only conversion to a supported format before
   collecting evaluation cases. Conversion must retain the preserved chain
   and write a separate derived output. All six source families were subsequently
   exported; five comparison gates passed, while Edge's supplied History was empty.

The installed FTK Imager user guide was inspected at
C:\Program Files\AccessData\FTK Imager\help\enu\FTKImager_UserGuide.pdf,
PDF page 56 for adding evidence. Its format list does not explicitly establish
support for this split snapshot chain. Guide identity and the disk dependency
check are recorded in .runs/disk-rehearsal01/ftk-guide-review.json and disk-chain.json.

The owner's supplied screenshot shows FTK Imager 8.3.0.27 reading the victim NTFS
volume and Users/eugene directory. The report was supplied after the preserved
current descriptor was specified; its image-source pathname is outside the
screenshot crop. Access evidence is retained in .runs/disk-rehearsal01/ftk-access.json
and ftk-filesystem-access.png. Sizes/write times of all included preserved files
were compared with the pre-copy record after this check and remained unchanged.
This screenshot is filesystem-access evidence. The subsequent export and
parser comparison results are recorded separately below.

The desktop export root is prepared at
C:\Users\eugen\Github\ICT3215-VeriTrace\.runs\disk-rehearsal01\exports.
Its subdirectories mirror source Windows paths; empty prepared directories do
not establish that the corresponding victim sources exist. Begin with these
two samples, using the image in FTK rather than the desktop's live filesystem:

1. In the currently visible Users/eugene folder, select NTUSER.DAT and any
   NTUSER.DAT.LOG1/NTUSER.DAT.LOG2 companions in the File List. Choose
   File -> Export Files and export to the prepared exports/Users/eugene folder.
2. Navigate to Users/eugene/AppData/Local/Microsoft/Edge/User Data/Default.
   Select History and any History-wal/History-shm companions. Export to the
   matching prepared directory under the export root. Inspect actual additional
   profiles separately and preserve each profile's directory identity.
3. Keep filenames unchanged and companions next to their source. Record absent
   files/profiles explicitly. The local guide's PDF page 94 documents file
   selection and File -> Export Files.
4. Hash/inventory the actual exports, retain these as acquired originals and
   parse working copies. Compare native records before enabling either family.

Private per-family source/destination instructions are retained at
.runs/disk-rehearsal01/export-instructions.json. These are rehearsal samples;
no controlled evaluation-case actions or ground-truth claims are inferred.

The owner exported NTUSER.DAT with LOG1/LOG2 and Default's History. The actual
four-file SHA-256 inventory and retained parser outputs are in
.runs/disk-rehearsal01/parser-validation01. All 31 UserAssist records matched an
independent hive reader, including encoded names, decoded targets, counters,
focus fields and timestamps. The configured pinned adapter repeated that
result, and source hashes remained unchanged. The hive is clean; no dirty-hive
replay pass is inferred. UEME control/session values remain distinguished from
application executions.

The owner confirms no additional Edge profiles and no History-wal/History-shm.
History passes SQLite integrity checks but all activity tables are empty;
zero parsed records agrees with the source. A nonempty browser sample is still
needed. LNK, Jump Lists, Prefetch and Recycle Bin exports subsequently passed
their native comparisons. Retain path layout and explicitly record absent
files in future acquisitions. Do not infer that browsing never occurred from
this empty database.

Export supported files while retaining original Windows path mappings:

| Family | Typical source |
| --- | --- |
| Edge | Each relevant profile's History plus available History-wal/History-shm |
| UserAssist | Relevant NTUSER.DAT and supplied adjacent transaction logs |
| LNK | Relevant user Recent folders and other selected .lnk files |
| Jump Lists | AutomaticDestinations and CustomDestinations in the user's Recent folder |
| Prefetch | Windows\Prefetch selected .pf files |
| Recycle Bin | $Recycle.Bin account directory's $I metadata and available $R companions |

Record omissions with reasons. Do not infer collection completeness from these
typical paths. Hash exports, preserve originals, and build case.json with the
actual acquisition/snapshot/tool identities. Keep companions adjacent to their
parent file in the exported directory. VeriTrace registers/copies them before
parsing. Inspect one record per present family against the source; only then
record the acquired-sample comparison in its private parser profile.

Create source-removal/corrupt-source **derivative cases**, retaining the base
acquisition. Every variant remains in its base case's development/test split.
