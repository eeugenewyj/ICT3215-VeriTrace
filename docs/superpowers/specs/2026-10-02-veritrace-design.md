# VeriTrace proof-of-concept design

Date: 2 October 2026 (Asia/Singapore)

Status: Implementation planning requested by the user on 2 October 2026 following design review and VM setup. Choices explicitly agreed in discussion are recorded below; runtime and parser defaults remain subject to feasibility checks. The backend prototype is implemented; live desktop-model, victim parser and acquired-case validation remain pending. See docs/implementation-status.md for current evidence and limitations.

## 1. Purpose and agreed scope

Demonstrate two local LLM agent roles that turn victim testimony into structured claims, call forensic tools against acquired Windows 10 evidence, and produce a traceable assessment for investigator review. The project evaluates the correctness and usefulness of this workflow.

Agreed constraints:

- Development happens in the current development environment. The existing project repository is C:\Users\eugen\Github\ICT3215-VeriTrace.
- The desktop hosts a standalone Windows 10 Pro victim VM in VMware, with disk encryption verified off for the first prototype. The physical spare SSD will not be used.
- Acquisitions concern the victim only. Attacker-device forensics is excluded.
- The first prototype accepts an acquired artefact folder. Direct disk-image ingestion is a later milestone.
- Collect and preserve RAM during lab acquisition; RAM analysis is a later milestone.
- Initial actions: download a file, open a document, launch a program, and delete a file into the Recycle Bin.
- Use Edge for browsing and viewing downloaded local PDFs. Notepad is the proposed separate program-launch test.
- Assessment runs automatically; the investigator reviews the complete report.
- Build a command-line interface and standalone HTML report first. Keep the backend independent of the interface so a local browser interface can be added.
- Inference is fully local. The desktop has a Ryzen 7 5700X, 16 GB system RAM, and RX 6750 XT with 12 GB VRAM.
- Stronger prompt-injection defences and optional claim review are future work. The prototype retains basic case-scoped tool and output validation.

The longer-term case is a compromised victim device following phishing, suspicious execution, enumeration, attempted or successful privilege escalation, and security response. It does not require building every incident-analysis capability in the first prototype.

## 2. Proposed implementation defaults

Use Python for orchestration and parser adapters, SQLite for the evidence index, schema validation for agent inputs and outputs, and a template renderer for an escaped, offline HTML report. Use a small explicit agent loop, with fixed tool definitions and bounded retries, rather than introducing an agent framework initially.

Keep the first Windows 10 Pro victim baseline standalone, without domain membership or organisational management. Verify that BitLocker/device encryption is off before preserving the baseline snapshot and collecting evaluation evidence; do not infer encryption status from the Windows edition. Pro supports BitLocker Drive Encryption, while some Home devices also support Device Encryption. See [Microsoft's encryption documentation](https://support.microsoft.com/en-us/windows/security/encryption/device-encryption-in-windows). Record the edition, build, Edge version, and security settings so each experiment can be reproduced. Selecting Pro leaves the planned agents, evidence index, tool contracts, and HTML report unchanged. Encrypted acquisitions, organisational management, and Defender for Endpoint integration are later extensions with separate setup and evaluation requirements.

First inference candidate: Ollama with a Vulkan backend and the quantized qwen3:8b model. Ollama currently lists this model as Q4_K_M, approximately 5.2 GB of model data. This does not represent total runtime memory. GPU acceleration, tool calling, context length, and latency must be benchmarked on the actual desktop. Freeze the tested runtime version, model digest, quantization, prompt versions, and generation settings in each run manifest. See [model listing](https://ollama.com/library/qwen3:8b), [hardware support](https://docs.ollama.com/gpu), and [tool-calling documentation](https://docs.ollama.com/capabilities/tool-calling).

Start with one loaded model serving both roles sequentially and a 4,096-token context budget. Each claim receives a fresh verification context containing its interpretation and case/coverage metadata. Keep the full tool ledger outside the prompt; paginate compact records and retain an explicit cited-record set. The application checks cumulative prompt size and requests a narrower query or reports context exhaustion when necessary; it does not silently truncate testimony or evidence fields. Context or model changes require a recorded benchmark. Begin with low-temperature generation and record its settings; repeated results are still measured, not assumed identical.

The model server runs on the desktop host, separately from the victim VM. The development application can call it over the trusted local network. The victim's experiment network is separate from the model-server access path.

Run experiments and inference at different times to reduce contention for 16 GB RAM. Start the victim with 4-6 GB RAM and 2-4 virtual CPUs, then measure. The investigator performs analysis after preserving the case and stopping the victim VM.

## 3. Case input and acquisition boundary

A case consists of testimony.txt, case.json, and an evidence folder. The folder preserves original Windows-relative paths where possible; the manifest supplies explicit original-path mappings where exports have been renamed.

The case manifest records case ID, evidence items and SHA-256 hashes, original source paths, acquisition method and tool versions, collection times, Windows edition/build, Edge version/profile, account/SID information where known, source timezone, and a testimony reference date/time where supplied. Record disk-encryption status with its verification method/time, standalone or managed status, and security settings relevant to the experiment, including Microsoft Defender status, firewall profiles, UAC, and audit/logging configuration. Keep a baseline configuration record and document changes between cases. Missing metadata is explicitly unknown; the application does not invent it.

For the first prototype, the investigator manually exports supported sources from the preserved disk acquisition using FTK Imager or the agreed acquisition workflow. The tool does not collect from a running victim or perform acquisition automatically.

RAM capture is a separate live collection before shutdown/restart. Preserve the dump, hash, capture times, and tool version with the case even though it is not parsed by the first version. Document the effect of live collection. The VMware-specific disk preservation procedure must be tested on the installed VMware edition before generating the evaluation corpus.

Retain browser SQLite databases and available sidecar files together; retain Registry transaction logs with hives. Parsers use working copies so recovery/checkpoint processing cannot modify originals. Record which companion files were supplied and how they were handled. A missing sidecar is not by itself proof of lost data.

Hash evidence at registration and check that originals remain unchanged after processing. All parser output, indexes, and reports go to a separate working/output directory.

## 4. Initial extraction coverage

The proposed parser adapters are:

| Source family | Initial parser | Intended relevance |
| --- | --- | --- |
| Edge Chromium history and downloads | Hindsight, restricted to those declared source types | Browser visits and download records |
| LNK files | LECmd | File-target interaction context |
| Automatic and custom Jump Lists | JLECmd | Application-associated recent activity |
| Prefetch | PECmd | Program execution context |
| Registry UserAssist records | RECmd with a pinned UserAssist-capable configuration/plugin | GUI program-activity context |
| Recycle Bin metadata | RBCmd | Original path and deletion-to-Recycle-Bin context |

Primary tool references: [Hindsight](https://github.com/RyanDFIR/hindsight), [LECmd](https://github.com/EricZimmerman/LECmd), [JLECmd](https://github.com/EricZimmerman/JLECmd), [PECmd](https://github.com/EricZimmerman/PECmd), [RECmd](https://github.com/EricZimmerman/RECmd), and [RBCmd](https://github.com/EricZimmerman/RBCmd).

The first extraction integration check must confirm the actual Edge schema and the UserAssist decoding configuration. Pin working parser versions/configuration hashes and retain raw outputs. Reading generic Registry keys is not sufficient to claim decoded UserAssist support.

Process every supplied source within this declared coverage and retain all returned records, independently of which claims are present. "All supported artefacts" refers to this list, not every possible Windows trace or every capability of these external tools. Other sources discovered in the folder are inventoried as unsupported.

Track status per discovered evidence item and summarise by family: parsed, parsed-with-no-records, failed, unavailable-in-input, or unsupported. If the manifest states a source was not collected, retain that reason. A file not supplied does not establish that it never existed on the victim.

The controlled lab determines which traces each action actually generates. LNK/Jump List presence or Edge execution alone must not be treated as definitive proof that a particular PDF was viewed. Record correlations and dependencies between sources rather than counting them as independent proof.

## 5. Evidence and claim contracts

Each indexed record contains:

- Stable record ID within the case and artefact family/type.
- Source evidence-item ID, SHA-256, original path, and source locator, such as database table/row key, Registry key/value, or parser item identifier.
- Raw timestamp values, their semantic roles and units/encoding, normalized UTC time where defensible, precision, and timezone assumptions.
- User/account scope, application, target paths/URLs, original parser fields, and known interpretation limits.
- Parser name, version, configuration hash, and a locator into preserved raw output.

Unknown timestamps remain unknown. File metadata times, artefact update times, and activity times retain their distinct meanings. SQLite results with no usable source-record locator cannot be presented as fully validated source citations.

Agent 1 produces atomic claims containing claim ID, exact source sentence, character offsets into the original UTF-8-decoded text, action, target, claimed actor, negation, time expression, resolved bounds if possible, uncertainty, and interpretation notes.

Keep the testimony unchanged. Preserve qualifiers such as "around", "I think", and "never". Unsupported actions remain explicit unsupported interpretations rather than being forced into the four initial actions. Relative dates require the supplied testimony reference date, not the acquisition date.

Exact time expressions retain their stated precision. Vague times remain unresolved unless the case supplies an explicit interpretation policy. Searches may use a broader exploratory window, but that search window is identified separately from what the witness actually asserted. The report exposes all assumptions.

## 6. Agent workflow and tool boundary

1. The CLI registers and hashes the case, validates metadata, and creates the working store.
2. Agent 1 produces claims; code validates exact source spans and schema. It may receive up to two repair attempts; invalid extraction produces an explicit run error.
3. Agent 2 calls extract_case(case_id). The backend runs the complete supported-source extraction set and returns coverage and counts, not the entire event corpus.
4. For each claim, Agent 2 uses search_records(case_id, filters, cursor), get_record(case_id, record_id), and get_source_coverage(case_id) to obtain relevant evidence.
5. Agent 2 returns an assessment with citations, concise evidence-based justification, alternative explanations, and limitations.
6. Code validates the assessment and builds the HTML report and JSON output.

The tools operate only on registered case IDs and controlled output locations. Search filters include family, target/path/URL text, account, and time. Pagination returns at most 25 compact records plus a continuation cursor and result count. Larger raw details are obtained by record ID when needed.

The host exposes a fixed function allowlist, validates arguments, and invokes configured parsers using argument arrays with no shell interpretation. The model receives no arbitrary shell, filesystem-path selection, deletion, or network-fetch tool.

The extraction call is a required workflow step. If the model fails to request it after one correction, stop with a workflow error; do not disguise a hardcoded extraction call as an agent-generated call. Repeated extraction with unchanged inputs is cached and preserves a trace of the request.

Allow up to 12 retrieval/tool calls per claim and two output-repair attempts. Limits and parser/model timeouts are configurable and logged. Exhausted limits, unavailable models, and invalid output produce operational errors or explicit partial reports, not fabricated forensic verdicts.

Citations must refer to existing case records actually returned to the agent and displayed in the report. Code checks ID, case membership, retrieval history, and source locator validity. Citation relevance and evidential sufficiency still require evaluation; ID validation alone cannot establish them.

Log actual tool requests, validated arguments, execution results/errors, durations, and cited record IDs. Persist concise justifications; private model reasoning is not required as a report artefact.

Testimony and artefact text are presented as untrusted case data. HTML rendering escapes their content and includes no externally loaded scripts. Prompt-injection resistance remains unevaluated until adversarial testing is performed. See [OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

## 7. Assessment meanings

| Assessment | Required interpretation |
| --- | --- |
| Supported | Positive relevant evidence is consistent with the interpreted activity at the stated time/target precision; the report qualifies what it establishes and what it does not. |
| Contradicted | Positive evidence conflicts with the interpreted claim, including its quantifiers and scope. Absence alone is insufficient. |
| Unverified | No sufficient relevant evidence was located within supported, available sources, or the action is outside coverage. |
| Inconclusive | Relevant evidence exists, but ambiguity, conflicting sources, timestamp uncertainty, attribution limits, or missing context prevents a defensible assessment. |

Separate account/device activity from attribution to a particular person. An activity under the victim's account does not by itself establish that the victim initiated it, especially in the compromise scenario. Explain attribution uncertainty alongside every affected assessment.

For negated claims, conflicting evidence must concern the same operational action, target, time scope, and attribution level. A record showing a file existed, or an unrelated program ran, is not enough.

The four assessments concern available evidence, not an assertion of the witness's honesty or a final legal finding. Technical execution failures are separately reported as run/claim errors.

## 8. Outputs and reusable backend

The standalone HTML report includes the original testimony, interpreted claims, assessments, source-linked records, limitations, coverage, model/parser/run metadata, and tool-call trace. It has a clear incomplete/error banner where applicable. Evidence identifiers link to embedded record details; source locations remain visible.

Produce machine-readable claims.json, assessments.json, coverage.json, run.json, raw parser outputs, an evidence SQLite index, and a structured tool-call log. This supports reproducible evaluation without scraping HTML.

The CLI calls a backend service API implemented as Python functions. Parsing, agent execution, and report generation do not depend on terminal input/output. A later browser interface can call the same functions; it is not part of the first delivery.

## 9. Evaluation and acceptance

Maintain two distinct labels: independently recorded action ground truth and the expected evidence-aware assessment. A true action with removed evidence can correctly be unverified. A false statement with no contradictory evidence need not be contradicted.

Initial corpus target: six independent acquired lab cases, split into three development cases and three held-out cases. Each has at least ten labelled claims spanning the four actions, false/negated statements, uncertain times/targets, and unsupported or unverified claims. Add source-removal and malformed-source variants; all variants from a base case stay in the same split.

Ground truth records actual actions, target identity/hashes, account, times, and experimental configuration. Two team members independently review the expected claims and evidence-aware labels, resolving disagreements with recorded reasons. Keep the action script/ground-truth log outside the evidence supplied to the agents.

Refine prompts and parser mappings on development cases. Freeze configuration before opening held-out cases. Model comparison uses the development split; the held-out set is not used for prompt selection or fine-tuning.

Measure source-span preservation; action, target, negation, and time-field correctness; retrieval of known relevant records; tool-call execution success and count; four-class assessment confusion matrix/macro-F1; citation existence and human-checked relevance; latency and resource use; and repeat-run agreement. Report denominators and operational failures.

Compare with a manual timeline/keyword-search workflow over the same available records. If participants are available, counterbalance cases/order and record experience, correctness, and review time. Separate descriptive results from claims of statistically established improvement.

The prototype is acceptable when a genuine victim acquisition passes an end-to-end run, tool calls visibly execute, all displayed citations resolve, originals remain unchanged, all available supported sources have recorded processing status, missing evidence alone never produces contradiction in the labelled omission tests, and reports preserve the exact source text and limitations. Accuracy and speed are measured results, not assumed benefits.

Synthetic records may support parser/contract tests during development. They do not substitute for real acquired evidence in the final demonstration.

## 10. Delivery sequence and later scope

Build in this order: local runtime/tool-call benchmark; case/record contracts; deterministic extraction and provenance; evidence queries; both agent roles; report generation; real-case integration and held-out evaluation.

Direct disk-image ingestion remains the intended final workflow and the next planned capability after the folder-based prototype. An image-access adapter will locate/export the supported files into the same case-input contract; its supported format and filesystem reader receive a focused follow-up design and feasibility check. The first implementation plan covers the folder-based prototype, not this later adapter.

Add compromise-relevant sources such as Windows event logs and persistence records as separately evaluated extensions. RAM parsing, a browser interface, and stronger prompt-injection evaluation are later milestones/future work. Cloud detection/isolation records require separate victim-related exports and actual service access. The final report must distinguish implemented capabilities from intended extensions.

Windows 10 Pro provides a suitable baseline for the later Microsoft Defender for Endpoint detection/isolation scenario: Microsoft lists Pro among supported Windows editions. A Windows Pro licence does not include a Defender for Endpoint subscription; licensing, tenant access, and device onboarding must be established separately when implementing that extension. See [Microsoft Defender for Endpoint requirements](https://learn.microsoft.com/en-us/defender-endpoint/minimum-requirements).

Treat phishing, execution, remote access/persistence, enumeration, attempted versus successful privilege escalation, and detection/isolation as separate hypotheses. The disk image alone cannot be assumed to contain a complete cloud response history.

Final deliverables are due 29 November 2026: source and runnable distribution plus manual on GitHub; 6-10-page IEEE report in Word/PDF; 5-10-minute subtitled 1080p video; and a generative-AI-use statement. At least 70% of final references must be reputable journal/conference sources. Reserve the final two weeks for evaluation, report, packaging, and video.

Distribute the application with dependency/version instructions and licence notices. Model weights and external parser binaries are separate prerequisites unless their redistribution has been checked. Budget and timing improvements are not claimed without measurements.

## 11. First implementation checks

- Confirm Windows 10 Pro installation entitlement and record the VM's exact Windows edition/build and Edge version.
- Verify that the victim VM is standalone and BitLocker/device encryption is off; retain the verification method/time and baseline security settings before generating evaluation cases.
- Check available host storage for the VM, acquisition copies, and retained RAM dumps.
- Verify the installed VMware acquisition procedure and preserve one sample case before resetting it.
- Benchmark the local model's structured output and genuine tool calling with the Vulkan backend.
- Confirm Edge database and Registry UserAssist compatibility using acquired samples, then pin dependencies.

These are implementation feasibility checks. The design can be approved with these defaults; a failed check leads to a documented adjustment rather than silently changing the claimed scope.

## 12. Recorded victim VM baseline

The user has completed the initial victim VM setup. The following observations come from the user-supplied updated.txt report collected at 2026-10-02T02:14:53.3835778+08:00, supplemented by the user's VMware and snapshot confirmations. This records the lab configuration; acquisition, parser compatibility, and local-model tool calling have not yet been validated.

| Item | Recorded baseline | Evidence |
| --- | --- | --- |
| Virtualisation | VMware 17.6.1; NAT networking | User confirmation; VMware product edition not supplied |
| Windows | Windows 10 Pro 22H2, 64-bit, build 19045.6456 | Updated configuration report |
| Membership | WORKGROUP; domain, Azure AD, enterprise, and workplace joins reported NO | Updated configuration report |
| Resources | 4 GB RAM; 2 logical processors | Updated configuration report |
| Guest disk | C: NTFS, 59.68 GB capacity; 35 GB free at collection | Updated configuration report; host storage availability remains unverified |
| Encryption | Fully Decrypted; 0.0% encrypted; encryption method None; protection Off | manage-bde -status in the updated report |
| Browser | Edge 154.0.4258.48 | Executable version in the updated report; parser compatibility remains untested |
| Defender | Normal running mode; antivirus, real-time protection, behaviour monitoring, and tamper protection enabled | Updated configuration report |
| Defender signatures | 1.459.505.0; reported last update 1 October 2026 at 20:48:05 | Updated configuration report; current platform version was not included |
| Firewall and UAC | All three firewall profiles enabled; inbound Block/outbound Allow; UAC enabled with secure desktop | Updated configuration report |
| Audit policy | Process Creation, File System, and Registry auditing report No Auditing | Updated configuration report; retain the recorded policy for the first artefact-based experiments |
| Clock | Singapore Standard Time, UTC+08:00; VM clock manually checked against the desktop host | Timezone from report; alignment confirmed by user, with no measured offset supplied |
| Snapshots | Fresh-install snapshot taken before diagnostic commands; experiment baseline snapshot subsequently confirmed taken | User confirmations; exact snapshot names/identifiers and creation times not supplied |

The updated report still returns W32Time error 0x80070426 (service not started). Preserve this result alongside the user's manual clock-alignment confirmation; do not describe it as a successful Windows Time synchronization query. Recheck clock alignment after restoring the experiment snapshot and before recording each case's actions. Record the actual snapshot identifier used for each experiment.

Source report SHA-256: 31961298B4107B550FE9D3BCE19E01BEA2F632D296195DA696E48121C6CBD784. The original updated.txt is retained in the user's Downloads folder; it is a setup report, not a disk or RAM acquisition.
