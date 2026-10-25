import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze contract to collect simple function level information")
    parser.add_argument("--sname", "-sn", dest="sname", help="the name to specify function name that need to match by re")
    parser.add_argument("--test", "-tt", dest="test", action="store_true", help="     000.json    ")
    parser.add_argument("--contract-dir", "-c", dest="contract", help="path to the smart contract or the directory containing multiple contracts")
    parser.add_argument("--output-dir", "-o", dest="output", help="path to the output directory")
    parser.add_argument("--ac-target", "-actarget", dest="actarget", action="store_true", help="Boolean value indicates which directory is used")
    parser.add_argument("--target-output", "-tout", dest="toutput", help="Path to the output directory of target contract")
    parser.add_argument("--inter-contract-call", "-icc", dest="icc", action='store_true', help="Consider inter-contract analysis")
    parser.add_argument("--contracts-mapping-file-path", "-mappingfpath", dest="mappingfpath", help="Path to the contract name to address mapping file")
    parser.add_argument("--dump-graphs", "-dg", dest="graph", action='store_true', help="Dumps all the generated graphs")
    parser.add_argument("--range-type", "-r", dest="range", help="Types of range analysis can be either range, havoc or none")
    parser.add_argument("--solver", "-sv", dest="solver", help="The name of the solver either z3 or cvc4")
    parser.add_argument("--patterns", "-p", type=str, help="comma separated patterns for running the analysis e.g DAO, TOD etc")
    parser.add_argument("--static-only", "-s", dest="static", action='store_true', help="executes only the static analysis")
    parser.add_argument("--owner-only", "-oo", dest="owner_only", action='store_true', help="Applies external call heuristic")
    parser.add_argument("--solc-path", "-sc", dest="solc_path", help="Path to the solc binary to compile the contract")
    parser.add_argument("--xblock-json", "-xblock", dest="xblock", action="store_true", help="Catogory Xblock dataset")
    parser.add_argument("--x_dir", "-xdir", dest="xdir", help="   xdir       ")
    parser.add_argument("--prune", "-prune", dest="prune",action="store_true", help="       ICFG")
    parser.add_argument("--normalize", "-normalize", dest="normalize",action="store_true", help="       ICFG")
    parser.add_argument("--scale", "-scale", dest="scale", action="store_true", help="           ")
    parser.add_argument("--contract-name", "-cname", dest="contract_name", help="      ")
    parser.add_argument("--dappscan", "-dappscan", dest="dappscan", action="store_true", help="Adapt the DAPPSCAN   ")
    parser.add_argument("--datacsv_dir", "-csvdir", dest="csvdir", help="                ")
    parser.add_argument("--dataset_dir", "-setdir", dest="setdir", help="    XBlock     ")
    parser.add_argument("--dataset_cve", "-dataset_cve", dest="dataset_cve", action="store_true", help="        cve   ")
    parser.add_argument("--dataset_smartbugs", "-dataset_smartbugs", dest="dataset_smartbugs", action="store_true",
                        help="        smartbug   ")
    parser.add_argument("--chain", "-chain", dest="chain", help="            ")
    parser.add_argument("--dataset_latest", "-dataset_latest", dest="dataset_latest", action="store_true",
                        help="                 ")
    parser.add_argument("--openfilter", "-openfilter", dest="openfilter", help="        openzeppelin    ")
    parser.add_argument("--count_time", "-count_time", dest="count_time", action="store_true", help="        ")
    parser.add_argument("--levenshtein_sim", "-levenshtein_sim", dest="levenshtein_sim", action="store_true", help="  levelshtein_sim      corresponding functions")
    parser.add_argument("--bert_sim", "-bert_sim", dest="bert_sim", action="store_true", help="  bert_sim      corresponding functions")
    args = parser.parse_args()
    return args


