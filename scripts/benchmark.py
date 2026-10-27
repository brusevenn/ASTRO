#!/usr/bin/env python3
"""Run native ASTRO graph generation and WFG similarity for comparison inputs."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACT_INDEX = ROOT / "datasets/actoolbench-cleaned-154/tools/astro/input-index.json"
SB_MANIFEST = ROOT / "datasets/smartbugs-wild-actaint/subsets/actaint-usable-533-v1/input-manifest.json"
REF_SOURCE = ROOT / "case/the_audited_database/0x0a0b34fc24b6a3477abc354eea9c9d8ae2c32132-Reputation.sol"
REF_SCOPE = "single pre-existing audited example WFG corpus; not representative accuracy coverage"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_hash(path):
    return digest(Path(path).read_bytes())


def rel(path):
    return Path(os.path.relpath(str(path), str(ROOT))).as_posix()


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


def safe_log(text):
    for old, new in (
        ("/add/users/shanzy/ASTRO", "<ASTRO_ROOT>"),
        ("/add/users/shanzy/comparison-runs", "<EXPERIMENT_ROOT>"),
        ("/home/shanzy", "<HOME>"),
        ("/tmp/", "<TMP>/"),
    ):
        text = (text or "").replace(old, new)
    return text


def graphviz_env():
    env = dict(os.environ)
    dot = shutil.which("dot", path=env.get("PATH"))
    if not dot:
        candidates = sorted(Path.home().joinpath("anaconda3/pkgs").glob("graphviz-*/bin/dot"))
        dot = str(candidates[-1]) if candidates else None
    if not dot:
        raise RuntimeError("GRAPHVIZ_DOT_NOT_FOUND")
    env["PATH"] = str(Path(dot).parent) + os.pathsep + env.get("PATH", "")
    chk = subprocess.run([dot, "-V"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    if chk.returncode:
        raise RuntimeError("GRAPHVIZ_NOT_RUNNABLE")
    return env


def load_map(path):
    raw = Path(path).read_bytes()
    d = json.loads(raw.decode("utf-8"))
    if d.get("schema") != "COMPARISON_SOLC_MAP_V1" or not isinstance(d.get("versions"), dict):
        raise RuntimeError("COMPILER_MAP_SCHEMA_INVALID")
    versions = {}
    for version, item in d["versions"].items():
        p = item if isinstance(item, str) else item.get("path")
        if not p or not Path(p).is_file():
            raise RuntimeError("COMPILER_MAP_PATH_MISSING:" + str(version))
        versions[str(version)] = str(p)
    return versions, digest(raw)


def semver(s):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(s or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def atom_match(v, atom):
    m = re.match(r"^(\^|~|>=|<=|>|<|=)?\s*v?(\d+(?:\.\d+){0,2})(?:\.x)?$", atom.strip(), re.I)
    if not m:
        return False
    op, text = m.groups()
    nums = tuple(int(x) for x in text.split("."))
    t = (nums + (0, 0, 0))[:3]
    if op == "^":
        upper = (t[0] + 1, 0, 0) if t[0] else ((0, t[1] + 1, 0) if t[1] else (0, 0, t[2] + 1))
        return v >= t and v < upper
    if op == "~":
        return v >= t and v < (t[0], t[1] + 1, 0)
    return {">=":v>=t, "<=":v<=t, ">":v>t, "<":v<t, "=":v==t, None:v==t}[op]


def pragma_match(v, expr):
    return any(all(atom_match(v, a) for a in group.split() if a)
               for group in expr.split("||"))


def select_pragma(source, versions):
    pragmas = re.findall(r"pragma\s+solidity\s+([^;]+);", Path(source).read_text(encoding="utf-8", errors="replace"), re.I)
    if not pragmas:
        raise RuntimeError("SOURCE_PRAGMA_NOT_FOUND")
    choices = [(semver(v), v) for v in versions]
    choices = [(t, v) for t, v in choices if t and all(pragma_match(t, p) for p in pragmas)]
    if not choices:
        raise RuntimeError("NO_OFFICIAL_COMPILER_MATCHES_PRAGMA")
    return sorted(choices)[-1][1], pragmas


def probe_compiler(version, path, raw=None, method=None):
    h = file_hash(path)
    p = subprocess.run([path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    found = re.search(r"Version:\s*([^\s]+)", out)
    commit = re.search(r"commit\.([0-9a-fA-F]+)", out)
    actual = found.group(1) if found else None
    if p.returncode or semver(actual) != semver(version):
        raise RuntimeError("SOLC_MAP_BUILD_MISMATCH:" + version)
    return {"compiler_release":version, "compiler_reported_version":actual,
            "compiler_commit_id":commit.group(1) if commit else None,
            "compiler_binary_sha256":h, "selection_method":method,
            "raw_config_version":raw}


def raw_config_version(d):
    for key in ("CompilerVersion", "compiler_version", "compilerVersion", "SolcVersion"):
        if isinstance(d.get(key), str) and d[key].strip():
            return d[key].strip()
    return None


def solc_args(d):
    opt = d.get("OptimizationUsed", d.get("optimize", d.get("optimizer")))
    if isinstance(opt, dict):
        enabled = str(opt.get("enabled", False)).lower() in ("true", "1")
        runs = opt.get("runs", d.get("Runs"))
    else:
        enabled = str(opt).strip().lower() in ("1", "true", "yes", "on")
        runs = d.get("Runs", d.get("optimizer_runs"))
    settings = {"optimizer_present":opt is not None, "optimizer_enabled":enabled,
                "optimizer_runs":str(runs) if runs is not None else None,
                "evm_version":None, "via_ir":None, "libraries_present":False}
    args = ["--optimize"] if enabled else []
    if enabled and runs is not None and str(runs).isdigit():
        args += ["--optimize-runs", str(int(runs))]
    evm = d.get("EVMVersion", d.get("evm_version"))
    if isinstance(evm, str) and evm.strip().lower() not in ("", "default"):
        settings["evm_version"] = evm.strip()
        args += ["--evm-version", evm.strip()]
    via = d.get("via-ir", d.get("viaIR", d.get("via_ir")))
    if via is not None:
        settings["via_ir"] = str(via).lower() in ("1", "true", "yes")
        if settings["via_ir"]:
            args.append("--via-ir")
    libs = d.get("Library", d.get("libraries"))
    settings["libraries_present"] = libs not in (None, "", {}, [])
    if settings["libraries_present"]:
        raise RuntimeError("COMPILE_CONFIG_LIBRARIES_UNSUPPORTED")
    return " ".join(args), settings


def compiler_for(dataset_kind, project, source, versions):
    if dataset_kind == "actoolbench":
        paths = project.get("compile_config_paths", [])
        if len(paths) != 1:
            raise RuntimeError("PROJECT_COMPILE_CONFIG_COUNT_INVALID")
        cfg_path = ROOT / paths[0]
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        raw = raw_config_version(cfg)
        v = semver(raw)
        if not v:
            raise RuntimeError("PROJECT_COMPILER_VERSION_MISSING")
        release = ".".join(str(x) for x in v)
        if release not in versions:
            raise RuntimeError("EXACT_OFFICIAL_COMPILER_NOT_IN_MAP:" + release)
        args, settings = solc_args(cfg)
        meta = probe_compiler(release, versions[release], raw, "PROJECT_CONFIG_NORMALIZED_RELEASE")
        meta["compile_config_path"] = paths[0]
        meta["compile_config_sha256"] = file_hash(cfg_path)
        meta["compile_settings"] = settings
        return versions[release], meta, args
    release, pragmas = select_pragma(source, versions)
    meta = probe_compiler(release, versions[release], None, "SOURCE_PRAGMA_BEST_MATCH")
    meta["source_pragmas"] = pragmas
    meta["compile_settings"] = {"optimizer_present":False, "optimizer_enabled":False,
                                "optimizer_runs":None, "evm_version":None,
                                "via_ir":None, "libraries_present":False}
    return versions[release], meta, ""


def identity():
    try:
        c = subprocess.run(["git","rev-parse","HEAD"],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
        s = subprocess.run(["git","status","--porcelain"],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
        return {"git_commit":c.stdout.decode("ascii","replace").strip() if c.returncode == 0 else "UNAVAILABLE",
                "working_tree_dirty":bool(s.stdout.strip())}
    except Exception:
        return {"git_commit":"UNAVAILABLE","working_tree_dirty":True}


def load_act():
    d=json.loads(ACT_INDEX.read_text(encoding="utf-8"))
    if d.get("case_count")!=154 or d.get("tool_input_file_count")!=694:
        raise RuntimeError("ACT_INDEX_COUNTS_INVALID")
    return d


def load_sb():
    d=json.loads(SB_MANIFEST.read_text(encoding="utf-8"))
    if d.get("case_count")!=533 or d.get("label_free") is not True:
        raise RuntimeError("SMARTBUGS_MANIFEST_INVALID")
    return d


def graph_command(source_rel, cwd, graph_out, solc_path, solcargs, env, timeout):
    cmd=[sys.executable,str(ROOT/"astro/analysis/contractlint.py"),
         "--contract-dir",source_rel,"--output-dir",rel(graph_out),
         "--dump-graphs","--scale","--prune","--normalize","--solc-path",solc_path]
    if solcargs:
        cmd += ["--solc-args",solcargs]
    try:
        p=subprocess.run(cmd,cwd=str(cwd),env=env,stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,timeout=max(1,int(timeout)))
        return p.returncode,safe_log(p.stdout.decode("utf-8","replace")),safe_log(p.stderr.decode("utf-8","replace")),None
    except subprocess.TimeoutExpired as e:
        o=e.stdout or b""; er=e.stderr or b""
        if isinstance(o,bytes): o=o.decode("utf-8","replace")
        if isinstance(er,bytes): er=er.decode("utf-8","replace")
        return None,safe_log(o),safe_log(er),"TIMEOUT"


def reference_command(args):
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    path=out/"project-result.json"
    base={"schema":"astro-comparison-project-result-v1","tool":"ASTRO",
          "dataset":"reference-preparation","project_id":"native-audited-reference",
          "case_ids":[],"status":"RUNNING","ground_truth_read":False,
          "reference_scope":REF_SCOPE,"code_identity":identity()}
    write_json(path,base)
    try:
        versions,map_hash=load_map(args.compiler_map)
        source=REF_SOURCE
        sh=file_hash(source)
        act=load_act(); sb=load_sb()
        overlap=sh in set(x["sha256"] for x in act["files"]) or sh in set(x["source_sha256"] for x in sb["cases"])
        if overlap:
            raise RuntimeError("REFERENCE_OVERLAPS_BENCHMARK")
        v,pragmas=select_pragma(source,versions)
        comp=probe_compiler(v,versions[v],None,"SOURCE_PRAGMA_BEST_MATCH")
        graphroot=out/"reference-graphs"
        env=graphviz_env()
        code,stdout,stderr,error=graph_command(source.relative_to(ROOT).as_posix(),ROOT,
                                               graphroot,versions[v],"",env,args.timeout_seconds)
        (out/"reference.stdout.txt").write_text(stdout,encoding="utf-8")
        (out/"reference.stderr.txt").write_text(stderr,encoding="utf-8")
        graphdir=graphroot/source.stem
        wfg=sorted(p.name for p in graphdir.glob("*_wfg.dot")) if graphdir.is_dir() else []
        status="REFERENCE_READY" if code==0 and wfg else "REFERENCE_PREPARATION_ERROR"
        base.update(status=status,reference_source=source.relative_to(ROOT).as_posix(),
                    reference_source_sha256=sh,benchmark_source_hash_overlap=False,
                    reference_graph_dir=rel(graphdir),reference_wfg_files=wfg,
                    reference_coverage_count=1,source_pragmas=pragmas,compiler=comp,
                    compiler_map_sha256=map_hash,timeout_seconds=args.timeout_seconds,
                    file_results=[{"source_path":source.relative_to(ROOT).as_posix(),
                                   "source_sha256":sh,"status":"COMPLETED" if status=="REFERENCE_READY" else (error or "GRAPH_ERROR"),
                                   "return_code":code,"wfg_count":len(wfg)}])
        write_json(path,base)
        return 0 if status=="REFERENCE_READY" else 2
    except Exception as e:
        base.update(status="REFERENCE_PREPARATION_ERROR",error_type=type(e).__name__,
                    error_message=safe_log(str(e)),file_results=[])
        write_json(path,base)
        return 2


def compare_file(args):
    result={"schema":"astro-similarity-result-v1","status":"RUNNING",
            "comparison_scope":"single_reference_example"}
    try:
        sys.path.insert(0,str(ROOT/"astro"))
        from lib import config
        from find_candidate.sim import main as sim_main
        config.SINGLE_MAX_WORKER=1
        target=ROOT/args.target_graph_dir
        reference=ROOT/args.reference_graph_dir
        files=sorted(p.name for p in target.glob("*_wfg.dot"))
        if not files:
            result.update(status="NO_WFG_FILES",candidate_match=None,target_wfg_count=0,matches=[])
            write_json(args.result_json,result); return 2
        class Collector(object):
            def __init__(self): self.rows=[]
            def writerow(self,row): self.rows.append(row)
        collector=Collector()
        out=sim_main(str(target),str(reference),files,collector)
        match=out[0] if isinstance(out,tuple) else out
        result.update(status="COMPLETED",candidate_match=bool(match),
                      target_wfg_count=len(files),matches=collector.rows)
        write_json(args.result_json,result)
        return 0
    except Exception as e:
        result.update(status="SIMILARITY_ERROR",candidate_match=None,
                      error_type=type(e).__name__,error_message=safe_log(str(e)))
        write_json(args.result_json,result); return 2


def group_input(args):
    if args.dataset=="actoolbench154":
        idx=load_act()
        projects={p["project_id"]:p for p in idx["projects"]}
        project=projects.get(args.project_id)
        if not project: raise RuntimeError("ACT_PROJECT_NOT_IN_INDEX")
        cases=[c for c in idx["cases"] if c["project_id"]==args.project_id]
        if not cases: raise RuntimeError("ACT_PROJECT_HAS_NO_CASES")
        byfile={}
        for c in cases:
            for f in c["tool_input_files"]:
                byfile.setdefault(f,[]).append(c["case_id"])
        files=[f for f in idx["files"] if f["project_id"]==args.project_id]
        return project,[c["case_id"] for c in cases],files,byfile,"actoolbench"
    if args.dataset=="smartbugs533":
        m=load_sb(); cid=args.case_id or args.project_id
        c=next((x for x in m["cases"] if x["case_id"]==cid),None)
        if c is None: raise RuntimeError("SMARTBUGS_CASE_NOT_IN_MANIFEST")
        p={"project_id":cid,"source_root":str(Path(c["source_path"]).parent),"compile_config_paths":[]}
        f={"project_id":cid,"source_path":c["source_path"],"tool_input_path":c["source_path"],
           "sha256":c["source_sha256"],"bytes":c["source_bytes"]}
        return p,[cid],[f],{c["source_path"]:[cid]},"smartbugs"
    raise RuntimeError("DATASET_NOT_SUPPORTED")


def run_group(args):
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    path=out/"project-result.json"; started=time.monotonic()
    result={"schema":"astro-comparison-project-result-v1","tool":"ASTRO",
            "dataset":args.dataset,"project_id":args.project_id or args.case_id,
            "case_ids":[],"status":"RUNNING","ground_truth_read":False,
            "reference_scope":REF_SCOPE,"file_results":[],"timeout_seconds":args.timeout_seconds,
            "code_identity":identity()}
    write_json(path,result)
    try:
        versions,map_hash=load_map(args.compiler_map)
        project,case_ids,files,case_file_map,kind=group_input(args)
        reference=Path(args.reference_graphs)
        if not reference.is_absolute(): reference=ROOT/reference
        if not reference.is_dir() or not list(reference.glob("*_wfg.dot")):
            raise RuntimeError("REFERENCE_WFG_CORPUS_MISSING")
        project_id=project["project_id"]
        result.update(project_id=project_id,case_ids=case_ids,project_case_count=len(case_ids),
                      source_file_count=len(files),compiler_map_sha256=map_hash,
                      reference_graph_dir=rel(reference.resolve()))
        result["file_results"]=[{"source_path":f["source_path"],"source_sha256_expected":f["sha256"],
                                 "case_ids":case_file_map.get(f["tool_input_path"],case_ids),
                                 "status":"NOT_STARTED","candidate_match":None,
                                 "comparison_scope":"single_reference_example"} for f in files]
        write_json(path,result)
        env=graphviz_env()
        for i,row in enumerate(files):
            remaining=args.timeout_seconds-(time.monotonic()-started)
            item=result["file_results"][i]
            if remaining<=10:
                item["status"]="NOT_ATTEMPTED_GROUP_BUDGET"
                write_json(path,result); continue
            source=ROOT/row["source_path"]
            if not source.is_file() or file_hash(source)!=row["sha256"]:
                item.update(status="INPUT_HASH_MISMATCH",error_type="INPUT_HASH_MISMATCH")
                write_json(path,result); continue
            try:
                compiler,compinfo,compile_args=compiler_for(kind,project,source,versions)
                item["compiler"]=compinfo
            except Exception as e:
                item.update(status="COMPILER_SELECTION_ERROR",error_type=type(e).__name__,error_message=safe_log(str(e)))
                write_json(path,result); continue
            key=digest(row["source_path"].encode("utf-8"))[:20]
            graphroot=out/"graphs"/key
            graphdir=graphroot/source.stem
            logdir=out/"logs"; logdir.mkdir(exist_ok=True)
            code,stdout,stderr,error=graph_command(row["source_path"],ROOT,graphroot,compiler,compile_args,env,
                                                   max(1,args.timeout_seconds-(time.monotonic()-started)-10))
            sout=logdir/(key+".graph.stdout.txt"); serr=logdir/(key+".graph.stderr.txt")
            sout.write_text(stdout,encoding="utf-8"); serr.write_text(stderr,encoding="utf-8")
            wfg=sorted(p.name for p in graphdir.glob("*_wfg.dot")) if graphdir.is_dir() else []
            item.update(graph_return_code=code,graph_output=rel(graphdir),graph_stdout=rel(sout),
                        graph_stderr=rel(serr),graph_wfg_count=len(wfg))
            if error=="TIMEOUT":
                item.update(status="TIMEOUT",error_type="TIMEOUT")
                for pending in result["file_results"][i+1:]: pending["status"]="NOT_ATTEMPTED_GROUP_TIMEOUT"
                write_json(path,result); break
            if code!=0 or not wfg:
                item.update(status="GRAPH_TOOL_ERROR",error_type=error or ("NONZERO_EXIT" if code else "NO_WFG_OUTPUT"))
                write_json(path,result); continue
            item["target_wfg_files"]=wfg
            simjson=out/"similarity"/(key+".json"); simjson.parent.mkdir(parents=True,exist_ok=True)
            cmd=[sys.executable,str(Path(__file__).resolve()),"compare-file",
                 "--target-graph-dir",rel(graphdir),"--reference-graph-dir",rel(reference.resolve()),
                 "--result-json",rel(simjson)]
            try:
                p=subprocess.run(cmd,cwd=str(ROOT),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                 timeout=max(1,args.timeout_seconds-(time.monotonic()-started)-3))
                (logdir/(key+".similarity.stdout.txt")).write_text(safe_log(p.stdout.decode("utf-8","replace")),encoding="utf-8")
                (logdir/(key+".similarity.stderr.txt")).write_text(safe_log(p.stderr.decode("utf-8","replace")),encoding="utf-8")
                sr=json.loads(simjson.read_text(encoding="utf-8")) if simjson.is_file() else {}
                if p.returncode==0 and sr.get("status")=="COMPLETED":
                    item.update(status="COMPLETED",similarity_result=rel(simjson),
                                candidate_match=sr.get("candidate_match"),
                                comparison_count=sr.get("target_wfg_count"),
                                matched_rows=sr.get("matches",[]))
                else:
                    item.update(status="SIMILARITY_TOOL_ERROR",error_type=sr.get("error_type","SIMILARITY_FAILED"),
                                similarity_result=rel(simjson))
            except subprocess.TimeoutExpired:
                item.update(status="TIMEOUT",error_type="TIMEOUT_DURING_SIMILARITY")
            write_json(path,result)
            if item["status"]=="TIMEOUT":
                for pending in result["file_results"][i+1:]: pending["status"]="NOT_ATTEMPTED_GROUP_TIMEOUT"
                write_json(path,result); break
        result["cases"]=[]
        for cid in case_ids:
            relevant=[x for x in result["file_results"] if cid in x.get("case_ids",[])]
            states=[x["status"] for x in relevant]
            status="COMPLETED" if relevant and all(x=="COMPLETED" for x in states) else (
                "TIMEOUT" if "TIMEOUT" in states or "NOT_ATTEMPTED_GROUP_TIMEOUT" in states else (
                "PARTIAL" if any(x=="COMPLETED" for x in states) else "ERROR"))
            result["cases"].append({"case_id":cid,"project_id":project_id,"status":status,
                                    "source_file_count":len(relevant)})
        counts={}
        for row in result["file_results"]: counts[row["status"]]=counts.get(row["status"],0)+1
        result["file_status_counts"]=counts
        states=[x["status"] for x in result["file_results"]]
        result["status"]="COMPLETED" if states and all(x=="COMPLETED" for x in states) else (
            "TIMEOUT" if "TIMEOUT" in states or "NOT_ATTEMPTED_GROUP_TIMEOUT" in states else (
            "PARTIAL" if any(x=="COMPLETED" for x in states) else "ERROR"))
        write_json(path,result)
        return 0 if result["status"]=="COMPLETED" else 2
    except Exception as e:
        result.update(status="ERROR",error_type=type(e).__name__,error_message=safe_log(str(e)))
        write_json(path,result)
        return 2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sp=p.add_subparsers(dest="command")
    r=sp.add_parser("prepare-reference")
    r.add_argument("--compiler-map",required=True); r.add_argument("--output",required=True)
    r.add_argument("--timeout-seconds",type=int,default=1200)
    g=sp.add_parser("run")
    g.add_argument("--dataset",choices=["actoolbench154","smartbugs533"],required=True)
    g.add_argument("--project-id"); g.add_argument("--case-id")
    g.add_argument("--compiler-map",required=True); g.add_argument("--reference-graphs",required=True)
    g.add_argument("--output",required=True); g.add_argument("--timeout-seconds",type=int,default=1200)
    c=sp.add_parser("compare-file")
    c.add_argument("--target-graph-dir",required=True); c.add_argument("--reference-graph-dir",required=True)
    c.add_argument("--result-json",required=True)
    args=p.parse_args()
    if args.command=="prepare-reference": return reference_command(args)
    if args.command=="run": return run_group(args)
    if args.command=="compare-file": return compare_file(args)
    p.error("command required")


if __name__=="__main__":
    sys.exit(main())
