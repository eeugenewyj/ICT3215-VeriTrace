# Desktop model benchmark

## 14 November runtime and context refresh

Installed Ollama is now 0.40.16. The October runtime-bound profile was rejected,
and the genuine benchmark first passed again at 4,096 tokens. Acquired Jump List
conversations still reached that context limit after successful retrieval, even
with identical record projections replaced by references. An 8,192-token profile
was therefore benchmarked before acquired-case use.

The 8,192-token benchmark passed all three native tool trials, their nine token
checks, and the short, Unicode and near-boundary retention probes. It ran from
15:34:49 to 15:36:46 UTC with VMware reporting zero running VMs before and after.
It used the already-installed qwen3:8b, the same model/template/tokenizer hashes,
temperature 0.1 and 768-token output reserve. No model was downloaded. The local
record is .runs/disk-jumplist01/model-benchmark03-8k.json with its budget profile,
configuration, stdout/stderr and one-second resource observations.

Minimum observed available host memory was 631,214,080 bytes (about 602 MiB),
with a maximum physical-memory load of 96%. The API reported context_length 8192
and model size_vram 6,312,228,290 bytes, equal to its reported model size. This
does not establish sustained-load capacity or independently reverify the GPU
backend. Keep the victim stopped during inference.

Focused acquired runs use
.runs/jumplist01-preparation/veritrace.jumplist01-8k-validated.toml. The general
private configuration and the earlier 4,096-token records remain unchanged.
A first 8,192-token launch failed before benchmarking because it referenced a
not-yet-created budget profile; its error/configuration were retained as
model-benchmark02-8k. The successful attempt used a capability configuration
without that prerequisite, then a case configuration bound to the new profile.
This synthetic capability pass does not establish forensic classification accuracy.

## Historical 2 October measurement

Measured on 2 October 2026, 12:02:00-12:02:38 SGT, in the existing desktop
checkout on codex/veritrace-prototype at ee34968. The genuine VeriTrace CLI
benchmark contacted the installed localhost Ollama server. Model weights were
already present and were not downloaded again. The pinned tokenizer JSON was
downloaded as the separate context-accounting prerequisite.

### Environment and frozen identities

| Item | Observed value |
| --- | --- |
| Host | Windows 11 Home; Ryzen 7 5700X, 8 cores/16 threads; approximately 16 GB RAM |
| GPU | AMD Radeon RX 6750 XT; server reports 12,272 MiB VRAM |
| Display driver | 32.0.21030.2001 |
| Python / uv | Python 3.12.15 in .venv; uv 0.12.22 |
| Ollama | 0.35.0; API listening on 127.0.0.1:11434 |
| Model | qwen3:8b, Q4_K_M, 8.2B parameters |
| Context / temperature | 4,096 tokens / 0.1 |
| Thinking / output reserve | false / 768 tokens |
| Protocol | native-tools-then-json-v1 |
| VMware | vmrun reported zero running VMs before and after |

Model digest:
`500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.

Template SHA-256:
`ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4`.

Tokenizer: official Qwen/Qwen3-8B revision
`b968826d9c46dd6066d109eabc6255188de91218`, tokenizer.json SHA-256
`aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4`.

Dependency lock SHA-256:
`8432966c8920acbd88d0222ce04205cba74eb8dad21428f198e61681ebf54e5f`.

### Results

**Passed.** Each of three trials made a model-generated get_benchmark_fact
request with the correct arguments. The host generated and returned a fresh
nonce only after receiving the request. Retrieval then stopped, and a separate
JSON-constrained turn with tools omitted returned that exact nonce. All nine
trial-stage server token counts were positive and below their conservative
estimates. No repair or failed trial was recorded.

| Trial | Elapsed seconds | Result |
| --- | --- | --- |
| 1, initially unloaded model | 10.396 | Passed; first API call includes 7.617 seconds of load time |
| 2, loaded model | 2.169 | Passed |
| 3, loaded model | 1.811 | Passed |

| Retention probe | Estimated prompt tokens | Server prompt tokens | Result |
| --- | --- | --- | --- |
| Short | 578 | 47 | Exact sentinel retained |
| Unicode | 583 | 52 | Exact sentinel retained |
| Near conservative input boundary | 3,156 | 2,626 | Exact sentinel retained |

The benchmark subprocess, including all probes and budget preparation, took
34.171 seconds. Aggregate generation over the nine tool-trial turns was
72.30 tokens/second using the API's eval_count/eval_duration. These are short
synthetic requests; they do not measure acquired-case latency or accuracy.

The profile uses tokenizer-json-upper-bound-v1 with a 512-token framing
allowance. It binds the runtime, model digest, template hash, tokenizer hash,
context length and protocol. The empirical check is not an exact reproduction
of the provider's chat template or a guarantee for arbitrary prompts.

### GPU and host resources

The retained server log identifies Vulkan0 as the RX 6750 XT and records
37/37 model layers offloaded to the GPU. ollama ps reports 100% GPU, 4,096
context tokens and 5.6 GB. The API reports size_vram = 5,569,815,510 bytes,
approximately 5.19 GiB. This is the runtime's reported model allocation,
not a measurement of total GPU usage. All twelve server completion entries
report truncated = 0.

One-second GlobalMemoryStatusEx samples recorded approximately 2.98 GiB
available at benchmark start, a minimum of 50.73 MiB and 99% physical-memory
usage, and approximately 1.40 GiB available at benchmark end. Other desktop
applications remained open. GPU offload therefore does not establish abundant
host RAM headroom. Keep the victim stopped during inference and close
unnecessary applications before acquired runs. Longer-run resource stability
has not been evaluated.

### Retained evidence and configuration

Local, ignored evidence directory:
`.runs/desktop-20261002T120200+0800/`.

It contains benchmark.json, benchmark.budget.json, benchmark stdout/stderr,
summary.json, resources.jsonl, the benchmark server-log segment, configuration
snapshot, doctor output, model inventory, ollama ps before/after, VM stop
checks, host observations, Git identity and environment hashes. These local
artefacts are not included in the repository and will not travel with a clone.

veritrace.local.toml now references
`.runs/desktop-20261002T120200+0800/benchmark.budget.json` and
`.external/qwen3-tokenizer.json`. The runtime/model/template/tokenizer/context/
protocol must still match at case-run time; any adjustment requires a fresh
benchmark and a new output path. The configuration retains the existing
unconfigured parser state; this benchmark does not enable additional families.

The recreated desktop environment also passed CLI help, locked package
installation and **88 unit tests, with one acquired integration test
deselected**. Approved victim-only, artefact-folder-first, preserved-RAM,
local inference, CLI and offline HTML decisions remain in force.

Next acceptance work is deployment and independent comparison of actual parser
outputs against preserved Windows 10 Pro victim samples, followed by genuine
acquired-case integration and reviewed evaluation. This capability benchmark
does not provide forensic labels, parser validation, citation-relevance
ratings, classification accuracy or investigation-time improvement.
