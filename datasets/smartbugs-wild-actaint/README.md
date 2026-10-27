# SmartBugs Wild / ACTaint source-only inputs for ASTRO

This package contains the 533 clear-result SmartBugs Wild contract sources selected for tool input. It was copied byte-for-byte from `brusevenn/smart-contract-AC-detector` commit `f10bc6c73280747013f2f5f4f1ef9f4e718e0ffa`, path `datasets/smartbugs-wild-actaint/subsets/actaint-usable-533-v1/`.

`subsets/actaint-usable-533-v1/input-manifest.json` records case IDs, input order, source paths, byte sizes, and SHA-256 only. `sources/` contains 533 Solidity files whose hashes match that manifest. No evaluation labels, reported vulnerable functions, root-cause text, or adjudication data are included. Do not read evaluation files from the source repository for detector input.

ASTRO has no source compiler settings in this package. The original manifest does not report compiler versions. Record compiler selection/failure per case; do not silently substitute a source-only result for ASTRO analysis. ASTRO's similarity stage also requires a separately identified reference WFG corpus; this package does not provide one.
