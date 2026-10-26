# ACToolBench-cleaned-154 input package for ASTRO

This is a dataset-only adaptation for `ASTRO`. No detector/research code was changed, and no detector run, compilation, or evaluation was performed during packaging.

**Target execution platform: Ubuntu 22.04 LTS.** Run the commands below from the repository root with POSIX paths. Each project needs its own compatible Python environment; this dataset packaging did not provision or test those environments.

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

The ASTRO README specifies Python 3.8. The repository has no requirements file, so install its dependencies in an isolated Python 3.8 environment on Ubuntu 22.04; do not combine it with ACTaint’s Python 3.12 environment.

- `tools/astro/source-files.txt` contains 694 Solidity paths relative to the repository root. `tools/astro/input-index.json` maps each path to the canonical project tree and case records.
- ASTRO's documented `contractlint.py -c` entry point accepts one source file (or a non-recursive directory); the list is intended for one-file-at-a-time ACFG generation. Example from the repository root:

```sh
python3.8 astro/analysis/contractlint.py -c "<path from tools/astro/source-files.txt>" -o case_result/ACToolBench154/<unique-output> -dg -scale -prune -normalize
```

- `find_candidate/sim.py` compares generated function graphs against a target/reference directory. This package supplies ACToolBench source inputs and indexes, not an ASTRO target-function/reference database or precomputed ACFGs; the full similarity-detection stage is not turnkey from the source list alone.
- Project `config.json` files are preserved but ASTRO's file-based entry point does not automatically apply them as compiler settings/remappings. Compilation and import resolution need tool-specific validation.

### ASTRO WFG comparison helper

The local checkout now resolves `contractlint.py`, `sim.py`, and `call_contractlint.py` relative to the repository instead of using the original `/root/...` paths. `astro/wfg/call_hungarian.py` resolves its helper relative to the repository and uses `ASTRO_PYTHON2` (default `python2`). That helper is Python 2.7 syntax and imports the external `hungarian` module and `numpy` in that interpreter; the main ASTRO code still requires Python 3.8. The local path portability changes have regression tests but have not been pushed to GitHub, and the Python 2.7/helper dependency environment has not been exercised here.
