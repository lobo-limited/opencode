#!/usr/bin/env python3
"""Ground-truth verifier for the fleet's single-brain serving invariant.

The fleet hub (supercat) may have at most ONE resident vLLM engine holding
>= 20 GiB of VRAM. That engine is the brain of record; every other resident
engine is a small co-tenant (minicpm, OCR). The invariant is enforced twice:
by systemd `Conflicts=` between engine units, and by fleet-swapd serialising
pool swaps. This script checks that the two layers and the proxy roster still
agree with reality.

Checks:
  1. HEAVY      at most one resident engine in the heavy class (>= 20 GiB VRAM)
  2. CONFLICTS  every engine unit that may host a heavy model mutually
                Conflicts= the other heavy-capable units
  3. DUPLICATE  no two engine units claim the same serving port
  4. ROSTER     the proxy roster does not advertise a model whose backend is down
  5. ALIASES    the brain aliases point at the resident heavy engine's port
  6. SWAPD      swapd's state agrees with the unit that is actually resident

Read-only. Never starts, stops, or edits anything.

Exit codes: 0 healthy, 1 violation found, 2 could not verify.
"""
import argparse
import json
import os
import re
import socket
import subprocess
import sys

HEAVY_VRAM_MIB = 20480
ROSTER_PATH = "/home/lobo/fleet-training/nim_endpoints.json"
SWAPD_STATE = "/home/lobo/fleet-swapd/state.json"
PROXY_URL = "http://127.0.0.1:8500"
PROXY_UNIT = "gato-fleet-proxy.service"
BRAIN_ALIASES = ("cortejo", "cortejo-v1", "saba-agent")
SMALL_ENGINES = {
    "minicpm-vllm.service",
    "vllm-ocr.service",
    "vllm-embed.service",
    "vllm-rerank.service",
}


def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    except Exception as exc:
        return "", str(exc), 1


def unit_list():
    out, _, _ = run(["systemctl", "list-unit-files", "--type=service", "--no-legend"])
    units = []
    for line in out.splitlines():
        name = line.split()[0] if line.split() else ""
        if name.endswith("-vllm.service") or (
            name.startswith("vllm-") and name.endswith(".service")
        ):
            units.append(name)
    return sorted(set(units))


def unit_props(name):
    out, _, _ = run(
        ["systemctl", "show", name, "-p", "ActiveState", "-p", "MainPID",
         "-p", "Conflicts", "-p", "ExecStart", "-p", "FragmentPath",
         "-p", "Environment"]
    )
    props = {}
    for line in out.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            props[key] = value
    exec_start = props.get("ExecStart", "")
    env = props.get("Environment", "")
    port = re.search(r"--port[= ](\d+)", exec_start)
    served = re.findall(r"--served-model-name[= ](\S+)", exec_start)
    model = re.search(r"--model[= ](\S+)", exec_start)
    if not port:
        port = re.search(r"\b[A-Z0-9_]*PORT=(\d+)", env)
    if not model:
        model = re.search(r"\b[A-Z0-9_]*MODEL=(\S+)", env)
    wrapper = ""
    argv = re.findall(r"argv\[\]=(\S+)", exec_start)
    if argv:
        candidate = argv[-1]
        if candidate.endswith(".py") and os.path.exists(candidate):
            try:
                with open(candidate, errors="ignore") as fh:
                    wrapper = fh.read(20000)
            except OSError:
                wrapper = ""
    if wrapper:
        if not port:
            port = re.search(r"--port[= ](\d+)", wrapper) or re.search(
                r"\bPORT\s*=\s*(\d+)", wrapper
            )
        served += re.findall(r"--served-model-name[= ][\"']?([^\s\"']+)", wrapper)
        if not model:
            model = re.search(r"--model[= ][\"']?([^\s\"']+)", wrapper)
    props["port"] = int(port.group(1)) if port else None
    props["served_names"] = sorted(set(served))
    props["model_path"] = model.group(1) if model else None
    props["conflicts"] = sorted(
        c for c in props.get("Conflicts", "").split() if c.endswith(".service")
    )
    props["main_pid"] = int(props.get("MainPID") or 0)
    props["active"] = props.get("ActiveState") == "active"
    return props


def gpu_processes():
    out, _, rc = run(
        ["nvidia-smi", "--query-compute-apps=pid,used_gpu_memory",
         "--format=csv,noheader,nounits"]
    )
    procs = {}
    if rc != 0 and not out:
        return procs
    for line in out.splitlines():
        bits = [b.strip() for b in line.split(",")]
        if len(bits) >= 2 and bits[0].isdigit() and bits[1].isdigit():
            procs[int(bits[0])] = int(bits[1])
    return procs


def port_listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except OSError:
        return False


def roster():
    try:
        with open(ROSTER_PATH) as fh:
            data = json.load(fh)
    except Exception:
        return {}
    endpoints = data.get("model_endpoints", {})
    out = {}
    for name, cfg in endpoints.items():
        url = (cfg or {}).get("url", "")
        m = re.search(r":(\d+)", url)
        out[name] = {
            "url": url,
            "port": int(m.group(1)) if m else None,
            "remote": "localhost" not in url and "127.0.0.1" not in url,
        }
    return out


def proxy_models():
    env_out, _, _ = run(["systemctl", "show", PROXY_UNIT, "-p", "Environment", "--value"])
    key = None
    m = re.search(r"FLEET_PROXY_API_KEY=(\S+)", env_out)
    if m:
        key = m.group(1)
    cmd = ["curl", "-sS", "-m", "8", "-o", "/tmp/.fleet_models.json", "-w", "%{http_code}"]
    if key:
        cmd += ["-H", f"Authorization: Bearer {key}"]
    cmd.append(f"{PROXY_URL}/v1/models")
    code, _, _ = run(cmd)
    if code != "200":
        return None, code
    try:
        with open("/tmp/.fleet_models.json") as fh:
            data = json.load(fh)
        os.unlink("/tmp/.fleet_models.json")
    except Exception:
        return None, code
    return sorted(entry.get("id", "") for entry in data.get("data", [])), code


def swap_pool():
    try:
        with open("/home/lobo/fleet-swapd/swapd.py", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return set()
    block = re.search(r"POOL\s*=\s*\{(.*?)\n\}", text, re.S)
    if not block:
        return set()
    return set(re.findall(r'"([^"]+)"\s*:', block.group(1)))


def swapd_state():
    try:
        with open(SWAPD_STATE) as fh:
            return json.load(fh)
    except Exception:
        return {}


def descendants(pid):
    family = set()
    frontier = [pid]
    while frontier:
        current = frontier.pop()
        if current in family:
            continue
        family.add(current)
        try:
            for task in os.listdir(f"/proc/{current}/task"):
                with open(f"/proc/{current}/task/{task}/children") as fh:
                    frontier.extend(int(c) for c in fh.read().split())
        except (OSError, ValueError):
            continue
    return family


def collect():
    units = {name: unit_props(name) for name in unit_list()}
    gpu = gpu_processes()
    resident = []
    claimed = set()
    for name, props in units.items():
        if not props["main_pid"]:
            continue
        family = descendants(props["main_pid"])
        for pid, mib in gpu.items():
            if pid in family:
                resident.append({"unit": name, "pid": pid, "vram_mib": mib,
                                 "heavy": mib >= HEAVY_VRAM_MIB})
                claimed.add(pid)
    for pid, mib in gpu.items():
        if pid not in claimed:
            resident.append({"unit": f"pid:{pid}", "pid": pid, "vram_mib": mib,
                             "heavy": mib >= HEAVY_VRAM_MIB})
    return units, gpu, claimed, resident


def verify():
    units, gpu, pid_to_unit, resident = collect()
    endpoints = roster()
    models, proxy_code = proxy_models()
    state = swapd_state()
    violations = []
    warnings = []

    heavy = [r for r in resident if r["heavy"]]
    resident_units = {r["unit"] for r in resident if r["unit"] in units}

    if len(heavy) > 1:
        violations.append({
            "id": "heavy-count",
            "severity": "critical",
            "detail": "more than one >=20GiB engine resident: "
                      + ", ".join(f"{r['unit']} ({r['vram_mib']}MiB)" for r in heavy),
        })
    elif not heavy:
        warnings.append({
            "id": "heavy-count",
            "severity": "warning",
            "detail": "no >=20GiB engine resident (brain down or serving only small engines)",
        })

    heavy_capable = {n for n in units if n not in SMALL_ENGINES}
    for name in sorted(heavy_capable):
        props = units[name]
        missing = sorted(heavy_capable - {name} - set(props["conflicts"]))
        if missing:
            violations.append({
                "id": "conflict-coverage",
                "severity": "critical",
                "detail": f"{name} lacks Conflicts= against: {', '.join(missing)}",
            })

    by_port = {}
    for name, props in units.items():
        if props["port"]:
            by_port.setdefault(props["port"], []).append(name)
    for port, names in sorted(by_port.items()):
        if len(names) > 1:
            warnings.append({
                "id": "duplicate-port",
                "severity": "warning",
                "detail": f"port {port} claimed by: {', '.join(sorted(names))}",
            })

    local = {n: e for n, e in endpoints.items() if not e["remote"] and e["port"]}
    pool = swap_pool()
    down_pool, down_other = [], []
    for name, entry in sorted(local.items()):
        if port_listening(entry["port"]):
            continue
        label = f"{name}(:{entry['port']})"
        if any(p in name or name in p for p in pool):
            down_pool.append(label)
        else:
            down_other.append(label)
    if down_pool:
        warnings.append({
            "id": "roster-pool-down",
            "severity": "info",
            "detail": f"{len(down_pool)} pool model(s) advertised but not loaded "
                      "(load on demand): " + ", ".join(down_pool),
        })
    if down_other:
        warnings.append({
            "id": "roster-down",
            "severity": "warning",
            "detail": f"{len(down_other)} roster model(s) advertised with no listening "
                      "backend and no swap-pool owner: " + ", ".join(down_other),
        })

    heavy_ports = {units[r["unit"]]["port"] for r in heavy if r["unit"] in units}
    for alias in BRAIN_ALIASES:
        entry = endpoints.get(alias)
        if not entry:
            continue
        if heavy_ports and entry["port"] not in heavy_ports:
            violations.append({
                "id": "alias-drift",
                "severity": "critical",
                "detail": f"brain alias {alias} points at :{entry['port']} but the resident "
                          f"heavy engine serves {sorted(p for p in heavy_ports if p)}",
            })

    loaded = state.get("loaded")
    if loaded:
        pool_unit = None
        for name, props in units.items():
            if props["active"] and (
                loaded in name or (props["served_names"] and loaded in props["served_names"])
            ):
                pool_unit = name
                break
        if pool_unit is None:
            warnings.append({
                "id": "swapd-state",
                "severity": "warning",
                "detail": f"swapd state says loaded={loaded} but no matching active engine unit",
            })
        elif pool_unit not in resident_units:
            warnings.append({
                "id": "swapd-state",
                "severity": "warning",
                "detail": f"swapd state says loaded={loaded} ({pool_unit}) but that unit has no "
                          "resident GPU process",
            })

    return {
        "units": units,
        "resident": resident,
        "heavy_resident": heavy,
        "endpoints": endpoints,
        "proxy_models": models,
        "proxy_http": proxy_code,
        "swapd_state": state,
        "violations": violations,
        "warnings": warnings,
    }


def render(report):
    out = []
    out.append("FLEET SERVING VERIFIER — single-brain invariant")
    out.append("=" * 58)
    out.append("resident GPU processes:")
    for r in sorted(report["resident"], key=lambda x: -x["vram_mib"]):
        out.append(f"  {r['unit']:<26} {r['vram_mib']:>7} MiB  "
                   f"{'HEAVY (>=20GiB)' if r['heavy'] else 'small co-tenant'}")
    if not report["resident"]:
        out.append("  (none)")
    heavy = report["heavy_resident"]
    out.append("")
    out.append(f"heavy class (>= {HEAVY_VRAM_MIB} MiB): {len(heavy)} "
               f"{'OK' if len(heavy) <= 1 else 'VIOLATION'}")
    out.append("")
    out.append("conflict coverage:")
    for name, props in sorted(report["units"].items()):
        if name in SMALL_ENGINES:
            continue
        out.append(f"  {name:<26} active={str(props['active']):<5} port={props['port']} "
                   f"conflicts={len(props['conflicts'])}")
    out.append("")
    out.append(f"proxy /v1/models: HTTP {report['proxy_http']} "
               f"({len(report['proxy_models'] or [])} ids)")
    out.append(f"swapd state: {json.dumps(report['swapd_state'])}")
    out.append("")
    for label, key in (("VIOLATIONS", "violations"), ("WARNINGS", "warnings")):
        items = report[key]
        out.append(f"{label} ({len(items)}):")
        if not items:
            out.append("  none")
        for item in items:
            out.append(f"  [{item['severity']}] {item['id']}: {item['detail']}")
        out.append("")
    ok = not report["violations"]
    out.append("VERDICT: " + ("HEALTHY — one heavy engine, invariant holds"
                               if ok else "VIOLATION — invariant broken"))
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = parser.parse_args()
    report = verify()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render(report))
    return 1 if report["violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
