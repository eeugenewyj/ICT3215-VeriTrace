# Desktop acquisition and parser setup

Latest progress reviewed on 15 November 2026, using the recorded 14 November
checks. All six parser tools are already
installed; no tool or model download is needed for the focused Jump List work.
The jumplist01 RAM/disk acquisition, FTK export, 20-record native comparison and
genuine Agent 1/2 runs passed their recorded operational checks. Ollama 0.40.16
passed a new 8,192-token benchmark. Use the focused configuration documented in
[setup](setup.md) and [Jump List integration](jumplist-contribution.md); the
general private configuration still needs its older runtime/normalizer pins
revalidated. Formal classification and repeatability evaluation remain pending.

The installation history below was recorded on 2–3 October; the current-state
table incorporates the November progress where observed.
Reviewed on 2 October 2026 at approximately 15:35 SGT; Hindsight setup completed
at 16:07 SGT and RECmd/WinPmem desktop preparation at 16:15–16:20 SGT.
The owner's guest RAM capture was reviewed and its desktop dump hash verified
at 16:50 SGT.
The powered-off VM preservation copy and all included file hashes passed
verification at 17:08 SGT. The owner subsequently demonstrated FTK NTFS access
in a screenshot. The first two source exports were received; UserAssist's
independent comparison and pinned configured launch passed at 23:22–23:24 SGT.
Edge History is readable but empty. The 3 October export check received nine
LNK files, three automatic/four custom Jump Lists and 207 nonempty Prefetch files.
Recycle Bin subsequently received six files, including two matching nonempty
$I/$R pairs, after an owner directory-export warning. Twenty-two zero-byte .copy0
extras are recorded separately. Five native parser-family comparisons and the
configured dispatcher passed; source-folder completeness, a nonempty Edge
sample and genuine agent integration remained pending at that October check.
Focused Jump List integration subsequently passed in November.
This is the current desktop installation inventory and the
remaining setup procedure. The approved design and implementation plan remain
unchanged.

## Current state

| Component | Observed state | Remaining acceptance work |
| --- | --- | --- |
| VMware Workstation | 17.6.1 build-24319023 observed in October; November victim shutdown and full preservation verified; snapshot JL01-ready (UID 4) observed after the experiment | Confirm historical baseline linkage and security-setting record; keep acquisitions reproducible |
| FTK Imager | 8.3.0.27; November screenshot shows readable NTFS/Windows/Users/eugene from the preserved 000005 descriptor; Jump List exports received and compared | Retain companions/original paths/hashes for future cases; source-folder completeness remains unconfirmed |
| Python / uv | Project Python 3.12.15 and uv 0.12.22 available | No further installation required; the system's default python is still 3.13 |
| .NET | Microsoft.NETCore.App and Microsoft.WindowsDesktop.App 9.0.14 installed | No further runtime installation required for the selected .NET 9 tools |
| 7-Zip | 26.02 installed | No further installation required |
| Local inference | Ollama 0.40.16 and existing qwen3:8b; new 8,192-token capability profile passed and focused acquired cases completed | Keep the victim stopped; broader evaluation and general-configuration refresh remain pending |
| LECmd | 2026.5.0; nine acquired records matched native headers and available LinkInfo paths; pinned configured extraction passes | Broader controlled-case evaluation; shell-only resolver accuracy remains outside this comparison |
| JLECmd | 2026.5.0; 16 October and 20 November acquired records matched native sources; three valid empty containers per acquisition; refreshed focused profile and genuine Agent 2 extraction passed | Broader controlled-case evaluation |
| PECmd | 2026.5.0; 207 acquired records matched independently decompressed executable/counter/runtime fields; pinned configured extraction passes | Broader controlled-case evaluation |
| RBCmd | 2026.5.0; both acquired deletion records match metadata fields and $R companions; pinned configured extraction passes | Broader controlled-case evaluation |
| Hindsight | Pinned source 4cf136f, version 2026.06 and separate Python 3.12 environment installed; actual victim History integrity passes and parser returns zero records matching its empty activity tables | Collect and compare a nonempty victim visit/download sample; family remains disabled |
| RECmd / UserAssist | RECmd 2026.5.0 with UserAssist 0.5; 31 victim records independently matched with zero mismatches; 70 package/batch files pinned; configured launch repeats matching result | Clean-hive sample gate passed; dirty-hive replay and broader evaluation remain untested |
| WinPmem | Designated Go rc2 signed-driver release staged by the owner in the victim; log shows driver service started, imaging completed and service stopped; exit 0; desktop SHA-256 matches the guest's 5 GiB dump | Record actual snapshot identity/security settings; preserve RAM again for each real case before shutdown |
| VeriTrace parser configuration | October five-family dispatcher produced 265 records without failures; November Jump List-only profile/configuration passed genuine model-generated extraction/assessment | Revalidate older general runtime/normalizer pins, compare nonempty Edge evidence, then evaluate broader cases |

FTK Imager is now installed; the earlier observation that only its installer
was present is superseded. Its installed application SHA-256 was recorded.
The installer has a valid Authenticode signature; the installed FTK Imager.exe
reports NotSigned. The four Zimmerman executable signatures report Valid.
This inventory does not treat file presence or a help check as acquisition or
forensic validation.

The current session's inherited PATH does not resolve uv directly. The uv
executable is present and works at
C:\Users\eugen\AppData\Roaming\Python\Python313\Scripts\uv.exe.
The commands below call it directly, avoiding the Python module lookup that
failed in the user's terminal. Its directory is also in the saved user PATH.
Do not recreate or alter the working VeriTrace environment to install parser
dependencies.

## 1. Hindsight on the desktop host

Use the source revision already inspected by this project:
4cf136fd70577b0da540b9a69750b769c6c27f32, display version 2026.06.
Its [source requirements](https://raw.githubusercontent.com/RyanDFIR/hindsight/4cf136fd70577b0da540b9a69750b769c6c27f32/requirements.txt)
also pin ccl_chromium_reader to a specific commit. Preserve those requirements
and resolve a separate desktop dependency lock before installation.

The desktop source checkout, environment and locked dependencies are now
installed. The following is a fresh-install recipe for another checkout;
do not repeat the clone/environment creation on this desktop. Inspect existing
directories before any later repair. The final two commands can be used to
repeat the read-only CLI checks.

```powershell
Set-Location 'C:\Users\eugen\Github\ICT3215-VeriTrace'
$taskUvExecutable = 'C:\Users\eugen\AppData\Roaming\Python\Python313\Scripts\uv.exe'
git clone --no-checkout https://github.com/RyanDFIR/hindsight.git .external/hindsight
git -C .external/hindsight checkout --detach 4cf136fd70577b0da540b9a69750b769c6c27f32
& $taskUvExecutable --cache-dir .uv-cache venv --python 3.12 .external/hindsight-env
& $taskUvExecutable --cache-dir .uv-cache pip compile .external/hindsight/requirements.txt --python .external/hindsight-env/Scripts/python.exe --output-file .external/hindsight-requirements.lock.txt
& $taskUvExecutable --cache-dir .uv-cache pip sync --python .external/hindsight-env/Scripts/python.exe .external/hindsight-requirements.lock.txt
& '.external\hindsight-env\Scripts\python.exe' '.external\hindsight\hindsight.py' --help
& '.external\hindsight-env\Scripts\python.exe' '.external\hindsight\hindsight.py' --list-artifacts
```

Confirm that the actual help advertises --only, --list-artifacts and JSONL
output, and that the artifact list includes history and downloads. Retain
the source revision, resolved dependency lock, interpreter identity/hashes and
CLI output. Configure an absolute interpreter-plus-script command; VeriTrace
does not support a parser command using python -m or inline code.

On this desktop all 22 installed packages passed the dependency check, help
advertises the required flags/JSONL output, and the artifact list contains
history and downloads. The dependency lock also retains the pinned transitive
ccl_simplesnappy revision. That parser installation did not change the main
application's uv.lock; the later feature commit adds tzdata for Windows zones.

Before production enablement, compare native visit/download row IDs, targets,
timestamps and companions against one preserved victim Edge History sample.
The earlier upstream Chromium 60 fixture result does not establish Edge 154
compatibility. See the [pinned Hindsight documentation](https://raw.githubusercontent.com/RyanDFIR/hindsight/4cf136fd70577b0da540b9a69750b769c6c27f32/README.md).

## 2. RECmd and decoded UserAssist on the desktop host

Desktop installation is complete. The full package was downloaded from
[the official .NET 9 RECmd archive](https://download.ericzimmermanstools.com/net9/RECmd.zip)
and extracted with 7-Zip. No separate UserAssist download or .NET installation
is needed on this desktop. Keep the entire RECmd folder together; it includes
RECmd.exe, RECmd.dll, RECmd.runtimeconfig.json, Plugins and BatchExamples.

Observed executable version: 2026.5.0+bcd0ac33ed98de61ea6de551eef96052bddbbd49.
The signed bundled RegistryPlugin.UserAssist.dll reports semantic plugin version
0.5 by read-only reflection; its file/assembly version is 1.0.0.0. These are
different version fields. No hive was processed during that metadata check.

The prepared restricted batch is
C:\Users\eugen\Github\ICT3215-VeriTrace\.external\RECmd\BatchExamples\VeriTraceUserAssist.reb.
It selects only NTUSER UserAssist\*\Count keys. Its batch/plugin export was
subsequently validated against 31 records in the preserved victim hive with
zero native-comparison mismatches. The earlier empty-directory CLI check was
only a launch check; the clean-hive comparison does not establish transaction-log
replay behavior. The supplied broader sample batch remains unchanged.

For a fresh deployment elsewhere:

1. Download the .NET 9 RECmd package from [Eric Zimmerman's official page](https://ericzimmerman.github.io/).
2. Extract its complete contents with 7-Zip into
   C:\Users\eugen\Github\ICT3215-VeriTrace\.external\RECmd. Keep supplied
   plugin/configuration directories and dependencies with the executable.
3. Inspect its signature and record the executable version/hash. Run the
   executable's --help and retain the output. The deployed version, rather
   than a version printed in an old upstream README, is the pinning authority.
4. Confirm a compatible UserAssist decoder is deployed. The existing adapter
   contract targets RegistryPlugin.UserAssist 0.5. Inspect the actual package
   and plugin version; do not assume the decoder is present because RECmd runs.
5. Create a restricted batch configuration for the UserAssist Count keys in
   the working NTUSER.DAT. Use the installed tool's documented batch format
   and retain the configuration hash. The unrestricted DFIR batch is not the
   intended production configuration for this adapter.
6. On a preserved victim hive and its supplied transaction logs, verify the
   encoded value name, decoded program name, execution counter and time
   against the source. Confirm the batch CSV and plugin-detail CSV satisfy
   the adapter's schema. Record failures or schema differences explicitly.

The [RECmd documentation](https://github.com/EricZimmerman/RECmd) covers batch
mode and plugin deployment. The [inspected UserAssist decoder source](https://raw.githubusercontent.com/EricZimmerman/RegistryPlugins/c16219db698f7ee66fbd97de7ec5d17fc10bdf8e/RegistryPlugin.UserAssist/UserAssist.cs)
documents version 0.5 and the decoded fields. A bare RECmd executable without
validated decoded output does not complete this family's setup.

## 3. WinPmem for the victim VM

Desktop preparation is complete at
C:\Users\eugen\Github\ICT3215-VeriTrace\.external\acquisition\winpmem\go-winpmem_amd64_1.0-rc2_signed.exe.
Executable SHA-256:
86691BB4AF2C17DD9EC4834C04A99AD51E04F780A07D1B05BC382A5D1892E0C4.

The outer Go executable reports Authenticode NotSigned. Its embedded x64
driver was extracted with the tool's save command, which saves and exits without
loading the driver. That SYS file reports a valid Binalyze LLC signature with
a trusted timestamp; driver SHA-256:
B1B866F7CF86BD2BBBD8BECA081E9DF836911D938FD129CD615CFCB04399212B.
This verifies the signed-driver package distinction, not successful kernel
loading on the victim. No acquisition or driver installation ran on the host.

The owner has now completed guest staging and a RAM capture. The guest tool hash
was reported as matching the host copy. The preserved Windows PowerShell
transcript identifies victim machine DESKTOP-E702D74 and Windows build 19045.
Capture ran from 08:45:04.1651924Z to 08:45:14.0139716Z on 2 October 2026;
the imager reported 9.4356013 seconds and exit code 0. Logs show the driver
service installed/started, memory ranges copied, imaging completed and the
service stopped, followed by a driver-removal message. No capture errors were
observed in the retained transcript/output.

The dump is 5,368,709,120 bytes (5 GiB). Its final address range ends at
0x140000000, so the logical file includes memory-address gaps. The desktop
Get-FileHash result matches both the guest's checksum file and transcript:
87CC5F3C14EEFEE9C9B6712A8A231F553B463DAC8D8CBF7024F46EF0D3BD514F.
Original capture files are retained in
.runs/acquisition-rehearsal01/rehearsal01/; the extra nested folder is the actual
transfer layout. Verification metadata is outside those files at
.runs/acquisition-rehearsal01/verification.json. No RAM content analysis occurred.
Later VMware metadata names current baseline "Acquisition-ready baseline", UID 3;
historical capture linkage and the security-setting record remain pending.
The transcript alone does not establish either. A powered-off full disk/snapshot
chain preservation copy has since passed file-hash verification. FTK filesystem
access has passed the owner-run check. The first two source families were
exported and UserAssist's comparison passed. Four further source comparisons
subsequently passed; Edge still needs a nonempty activity sample.

For subsequent rehearsals or real cases:

1. From the [official WinPmem release](https://github.com/Velocidex/WinPmem/releases/tag/v4.0.rc1),
   obtain go-winpmem_amd64_1.0-rc2_signed.exe, the build its release notes
   designate for production use. The 4.1 test driver requires test signing;
   preserve the victim's existing security settings for this rehearsal.
2. Keep the desktop copy at
   C:\Users\eugen\Github\ICT3215-VeriTrace\.external\acquisition\winpmem.
   Record its release URL, version, signature status and SHA-256.
3. Copy the same executable into C:\Tools\Acquisition inside the Windows 10
   Pro victim. Check that its SHA-256 matches the desktop copy. Record this
   staging change and the experiment snapshot used.
4. Open an administrator terminal inside the disposable victim experiment.
   Retain its -h and acquire --help output. The downloaded binary advertises
   acquire, --compression and --progress. Use the selected Go capture command
   below; the legacy mini-imager syntax is different.
5. Rehearse RAM capture under the current security settings, with enough guest
   storage for the dump. Record capture start/end times, result, size and
   SHA-256; transfer and preserve the dump on the investigator host. Capture
   before shutdown. A blocked driver or failed capture remains a failure to
   resolve, not a successful acquisition.

Inside the victim, after staging and recording the experiment baseline:

```powershell
$taskCaptureExe = 'C:\Tools\Acquisition\go-winpmem_amd64_1.0-rc2_signed.exe'
Get-FileHash -Algorithm SHA256 -LiteralPath $taskCaptureExe
# Compare the complete hash with the desktop value above before proceeding.
& $taskCaptureExe acquire --help
# Confirm guest free space covers the dump and address gaps before capture.
New-Item -ItemType Directory -Path 'C:\Acquisition\rehearsal01' | Out-Null
Start-Transcript -Path 'C:\Acquisition\rehearsal01\capture.log'
(Get-Date).ToUniversalTime().ToString('o')
& $taskCaptureExe acquire --compression none --progress 'C:\Acquisition\rehearsal01\physmem.raw'
$taskCaptureExit = $LASTEXITCODE
(Get-Date).ToUniversalTime().ToString('o')
"Capture exit code: $taskCaptureExit"
if ($taskCaptureExit -eq 0) {
    Get-Item -LiteralPath 'C:\Acquisition\rehearsal01\physmem.raw' | Select-Object Length
    Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\Acquisition\rehearsal01\physmem.raw'
}
Stop-Transcript
if ($taskCaptureExit -ne 0) { throw 'RAM capture failed; retain diagnostics and resolve before case acquisition.' }
```

Use a new output directory per rehearsal so prior outputs cannot be overwritten.
The upstream [Go acquisition implementation](https://raw.githubusercontent.com/Velocidex/WinPmem/master/go-winpmem/cmd/acquire.go)
uses none for uncompressed output. It creates a temporary driver service during
capture and attempts cleanup afterward. Preserve the transcript and dump on the
host and verify the transferred dump's hash matches. Keep the victim's existing
security settings; a load failure needs investigation before any approved
baseline change. Perform this rehearsal before collecting evaluation cases.

Use the actual transferred directory when checking a host copy. Copying the
whole guest folder into a host folder can create another nested directory.
The verification must stop on missing or malformed input; two absent hashes
must never be treated as equal. For the current preserved rehearsal:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $taskFolder = 'C:\Users\eugen\Github\ICT3215-VeriTrace\.runs\acquisition-rehearsal01\rehearsal01'
    $taskExpected = (Get-Content -LiteralPath (Join-Path $taskFolder 'physmem.sha256') -Raw -ErrorAction Stop).Trim()
    if ($taskExpected -notmatch '^[0-9A-Fa-f]{64}$') { throw 'Invalid expected SHA-256.' }
    $taskDump = Join-Path $taskFolder 'physmem.raw'
    if (-not (Test-Path -LiteralPath $taskDump -PathType Leaf)) { throw 'RAM dump is missing.' }
    if ((Get-Item -LiteralPath $taskDump).Length -eq 0) { throw 'RAM dump is empty.' }
    $taskActual = (Get-FileHash -Algorithm SHA256 -LiteralPath $taskDump -ErrorAction Stop).Hash
    if ($taskActual -ne $taskExpected) { throw 'Transferred dump hash does not match.' }
    'Transferred dump hash matches.'
}
```

This step preserves RAM for later analysis. It does not add RAM parsing to
VeriTrace. See [acquisition procedure](acquisition.md) for the full sequence.

## 4. FTK Imager and preserved disk access

Installation and stopped-VM preservation are complete. All 309 included VM files
(about 48.57 GiB) have matching source/copy SHA-256 values. The preserved current
disk is .runs/disk-rehearsal01/vm-preserved/Windows 10 Pro x64-000004.vmdk;
its four-descriptor parent chain and all 64 required split extents were checked.
Only the transient .vmx.lck configuration lock was excluded. Those details
describe the October preservation; the November case uses 339 files and the
000005 descriptor under .runs/disk-jumplist01, as recorded in implementation-status.md.
Supported exports and five source comparisons subsequently passed. The owner has
already demonstrated NTFS/Windows/Users/eugene access in FTK 8.3.0.27. A copy-only
format conversion is not required by this observed access result. Follow the
export procedure in [acquisition procedure](acquisition.md), using the prepared
.runs/disk-rehearsal01/exports directories. Do not select the desktop's live
system disk as victim evidence.

At the initial review C: had approximately 148.85 GiB free and G: 141.40 GiB.
The later RECmd/WinPmem preparation audit recorded C: 158.26 GiB free on NTFS
and G: 150.35 GiB free on FAT32. FAT32 cannot hold a single file of 4 GiB or
larger, which matters for raw RAM dumps and VM disk copies. These are
point-in-time observations; recheck before acquisition and compare free
space with the actual snapshot chain, preservation copies, RAM dumps and
working outputs. G:'s relationship to the excluded spare SSD has not been
established, so it is not selected as an acquisition destination here.

## 5. Configure and validate all six parser families

With all six parser tools present on the desktop, the configuration work applies
to all six families, including the four tools that already launch:

1. Retain actual parser help, runtime requirements, versions, hashes and export
   schemas. Use absolute pinned executable/script paths.
2. Run each parser on working copies of the supplied victim sources. Preserve
   available SQLite/Registry companions and all raw outputs and diagnostics.
3. Independently compare at least one record per present family with its
   original source; reconcile coverage and unchanged source hashes.
4. Complete a private parser profile based on examples/parser-profile.json,
   including dependency hashes, schema identity and the comparison record.
   Keep acquired_sample.verified false until the comparison passes.
5. Populate veritrace.local.toml's parser_commands, parser_versions,
   parser_config_hashes and parser_profiles. Enable only families whose
   acquired-sample gates have passed. Retain the existing model budget profile.
6. Run the acquired-case integration check and inspect the offline report,
   actual tool receipts, coverage and citations before evaluation.

See [parser compatibility contracts](parser-compatibility.md) and the approved
plan for these acceptance requirements. Five families have recorded
victim-source comparison passes; Edge remains pending. The independent comparator
uses python-registry 1.3.1 in a separate .external/registry-validation-env with
a hashed dependency lock. olefile 0.47 is separately locked for OLE comparison;
native Windows decompression and independent byte reads check Prefetch fields.
The project and Hindsight environments were preserved. The configured check has
265 records, three valid empty sources, no failures and unchanged originals.

## Review evidence

Local audit directory: .runs/tool-readiness-20261002T153451/. It contains the
executable inventory and SHA-256 values, Authenticode results, four parser help
outputs, launch-check results, doctor output and storage observations. Prior
model benchmark evidence remains in .runs/desktop-20261002T120200+0800/.
These ignored artefacts remain on this desktop and do not travel with a clone.
Hindsight installation evidence is retained in
.runs/hindsight-setup-20261002T160757/: help and artifact-list output, dependency
checks/freeze, source identity, dependency lock and executable/source hashes.
RECmd/WinPmem preparation evidence is retained in
.runs/remaining-tools-setup-20261002T161524/: full RECmd package manifest,
versions/signatures/hashes, CLI help, UserAssist plugin metadata, restricted-batch
hash and the extracted embedded driver's signature. These checks do not certify
a victim capture or decoded victim export.
The later owner-run capture/transfer evidence and its verification record are
retained in .runs/acquisition-rehearsal01/. The dump itself was hashed on the
desktop; matching was not inferred from file presence or the user's console
success message.
Stopped-VM preservation evidence is retained in .runs/disk-rehearsal01/:
copy log, all-file source/copy SHA-256 manifest, preservation summary, dependency
chain validation, installed FTK guide identity and post-copy storage observation.
The preserved VM folder is about 48.57 GiB; C: had 88.38 GiB free afterward.
The owner's FTK screenshot and filesystem-access record are retained in the
same audit directory. The received NTUSER.DAT, LOG1/LOG2 and Default History
inventory, native comparisons, actual parser receipts and configured launch
are retained under its parser-validation01 subdirectory. The owner reports no
additional Edge profiles and no History-wal/History-shm. The subsequent dated
export-check directory inventories/hashes all 253 received files, confirms the
original four hashes and records nine LNK files, seven Jump Lists and 207 nonempty
Prefetch files. A later check hashes 259 files, including two acquired Recycle
Bin metadata/content pairs and two extra files in the SID directory. Directory
creation-error investigation is recorded separately; the exact FTK cause is
unconfirmed and no permissions were changed.
