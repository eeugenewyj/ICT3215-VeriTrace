# Victim acquisition rehearsal

This is an owner-run procedure to validate on the desktop. No victim disk or
RAM acquisition has been performed by the development session. Development
happens on the laptop; the desktop hosts the victim VM and local model.
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
start/end times. Its documented capture syntax is:

```powershell
.\winpmem_mini_x64.exe 'C:\Acquisition\dev01\physmem.raw'
Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\Acquisition\dev01\physmem.raw'
```

Choose and record the actual output destination with sufficient space. Live
capture creates traces; document its effect and transfer the preserved dump to
the investigator. A failed capture is recorded as failed. Do not silently alter
the victim's baseline security configuration to make a tool run. RAM analysis
is outside this prototype.

## Disk preservation and export

After RAM capture, stop the victim cleanly and record that shutdown. Preserve
the **complete required VM/disk snapshot chain** on the investigator's storage.
A snapshot alone is not an acquisition, and a lone base VMDK may omit changes
stored in child disks. Hash and inventory the retained files before further work.

Use the installed [FTK Imager](https://www.exterro.com/digital-forensics-software/ftk-imager)
on a preserved copy. Record its version and demonstrate access to the victim
filesystem before collecting evaluation cases. If that reader cannot open the
preserved representation, validate and document a copy-only conversion/access
procedure first. The development session cannot confirm which VMware disk
representation the desktop created. This rehearsal is manual acquisition;
VeriTrace does not yet ingest disk images directly.

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
