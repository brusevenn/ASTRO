# ACToolBench-cleaned-154 input package for ASTRO

This directory packages ACToolBench-cleaned inputs for `ASTRO`. Source/config bytes and the original manifest were preserved. The current working tree also contains local, uncommitted ASTRO portability/debug changes described below.

**Target execution platform: Ubuntu 22.04 LTS.** ASTRO's CLI and one synthetic Solidity contract were tested with Python 3.8.20, Slither 0.9.6, crytic-compile 0.3.11, web3 6.20.4, and Graphviz 14.1.2. The repository still has no complete, pinned runtime requirements file.

## Contents and provenance

- Source: [`brusevenn/smart-contract-AC-detector`](https://github.com/brusevenn/smart-contract-AC-detector), `main`, commit `99b0ad9f39ee54a7d9645ac693dd74e9d4479f7e`.
- Original full manifest: [`full/manifest.json`](full/manifest.json), copied byte-for-byte from `datasets/actoolbench-cleaned/full/manifest.json` (Git blob SHA-1 `9d4160fca8ff05ca2ab105deb8db732564829e79`, SHA-256 `9c74d0a6c647543e80cced49044639b7a8c40e241fc8593c21e574210584b5fa`).
- Source trees: `full/projects/<project_id>/source_code/`, including each project's original `config.json` and all Solidity sources/dependencies.
- Upstream license: [`UPSTREAM_LICENSE`](UPSTREAM_LICENSE).
- `file-hashes.jsonl` records each copied project/config file's repository-relative path, byte count, SHA-256, Git blob SHA-1, project ID, and role. The manifest's per-source SHA-256 values are retained unchanged.
- `tools/astro/input-index.json` preserves the case-to-project mapping and this tool's input paths; `source-files.txt` is the tool-ready unique Solidity input list.

Counts: **154 case records**, **121 project trees**, **694 unique Solidity files**, and **121 compile configuration files**. Multiple case records can share a project tree; the tool input list is therefore a list of unique source files, not 154 independently selected contracts. Use the case mapping in `input-index.json` when relating tool results back to records.

## Label boundary

Only source/config files are intended as detector input. The case manifest and tool index contain opaque case/project identifiers and source paths/hashes, but no per-case vulnerability type, official function name, root-cause description, or adjudication result. Do not pass `full/manifest.json`, `input-index.json`, `file-hashes.jsonl`, or `source-files.txt` into the model prompt; use only the `.sol` files through the tool's normal loader. The copied manifest has global dataset metadata but no case-level label assignments.

Source bytes, including original comments and formatting, are preserved. No evaluation-side files were copied. The upstream manifest records `source_compile_status: NOT_EXECUTED`; compiler compatibility is not implied by this package.

## ASTRO input layout and limitations

The ASTRO README specifies Python 3.8. The tested runtime used Python 3.8.20 with Slither 0.9.6, crytic-compile 0.3.11, web3 6.20.4, and Graphviz 14.1.2. The repository does not yet declare the full dependency set. A shared environment containing `spcon`/`manticore` may report dependency conflicts after upgrading Slither; use this runtime for ASTRO only unless those tools are separately checked.

- `tools/astro/source-files.txt` contains 694 Solidity paths relative to the repository root. `tools/astro/input-index.json` maps each path to the canonical project tree and case records.
- ASTRO's documented `contractlint.py -c` entry point accepts one source file (or a non-recursive directory); the list is intended for one-file-at-a-time ACFG generation. Example from the repository root:

```sh
export PATH="$CONDA_PREFIX/bin:$PATH"
python astro/analysis/contractlint.py -c "<path from tools/astro/source-files.txt>" -o case_result/ACToolBench154/<unique-output> -sc "$CONDA_PREFIX/bin/solc" -dg -scale -prune -normalize
```

- `find_candidate/sim.py` compares generated function graphs against a target/reference directory. This package supplies ACToolBench source inputs and indexes, not an ASTRO target-function/reference database or precomputed ACFGs; the full similarity-detection stage is not turnkey from the source list alone.
- Project `config.json` files are preserved but ASTRO's file-based entry point does not automatically apply them as compiler settings/remappings. Compilation and import resolution need tool-specific validation.

### ASTRO runtime verification and limitations

The checkout now resolves `contractlint.py`, `sim.py`, and `call_contractlint.py` paths relative to the repository. The local WFG helper uses SciPy's `linear_sum_assignment` instead of the original Python 2 `hungarian.lap` helper. Both minimize assignment cost, but tie-breaking parity is **not verified**. `criterion.find_addnode_candidate` consumes the mapping to select candidate anchors, so tied matrices can change downstream candidates; do not treat this replacement as baseline-equivalent until differential/golden tests establish parity.

The local `astro/lib/compile_config.py` wrapper delegates to `crytic_compile.localize.config` when that project-specific extension exists. Without it, non-XBlock mode is supported and `-xblock` raises an actionable error. In the Ubuntu 22.04 runtime listed above, the 10-test suite passes, `contractlint.py --help` exits successfully, and one synthetic Solidity contract completes through callgraph, ICFG, and WFG generation using the environment's `solc` wrapper and Graphviz. No ACToolBench case or full benchmark was run. Slither 0.9.6 resolves the former `Contract.is_fully_implemented` failure, but the upgraded shared environment reports strict-version conflicts for the installed `spcon` and `manticore` packages; their operation was not validated. Local changes are not pushed to GitHub.
