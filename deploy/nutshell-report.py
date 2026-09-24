#!/usr/bin/env python3
"""Bilan quotidien d'activité (nginx + serveur MCP), envoyé par mail via exim.

Usage : nutshell-report.py [--to ADRESSE] [--hours 24] [--stdout]
Stdlib uniquement ; lit les logs nginx (combined, y compris rotations) et journald.
"""
import argparse
import glob
import gzip
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

LOG_GLOB = "/var/log/nginx/access.log*"
UNIT = "nutshell-mcp"
LINE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+)[^"]*" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) "[^"]*" "(?P<ua>[^"]*)"'
)
BOT = re.compile(r"bot|crawl|spider|scan|curl|python-requests|go-http|zgrab|censys|headless", re.I)


def read_lines(since):
    for name in sorted(glob.glob(LOG_GLOB)):
        opener = gzip.open if name.endswith(".gz") else open
        try:
            with opener(name, "rt", errors="replace") as f:
                yield from f
        except OSError:
            continue


def parse(since):
    for raw in read_lines(since):
        m = LINE.match(raw)
        if not m:
            continue
        ts = datetime.strptime(m["ts"], "%d/%b/%Y:%H:%M:%S %z")
        if ts >= since:
            yield ts, m


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def top(counter, n=8):
    return [f"  {c:>6}  {k}" for k, c in counter.most_common(n)] or ["  (aucun)"]


def fail2ban_section(since_local):
    bans, unbans = Counter(), 0
    for name in ("/var/log/fail2ban.log.1", "/var/log/fail2ban.log"):
        try:
            with open(name, errors="replace") as f:
                for l in f:
                    m = re.match(r"(\S+ \S+?),\d+ .*\[(\S+)\] (Ban|Unban) (\S+)", l)
                    if not m or datetime.strptime(m[1], "%Y-%m-%d %H:%M:%S") < since_local:
                        continue
                    if m[3] == "Ban":
                        bans[(m[2], m[4])] += 1
                    else:
                        unbans += 1
        except OSError:
            continue
    per_jail = Counter(j for j, _ in bans)
    out = ["== fail2ban ==",
           "Bans : " + (", ".join(f"{j}={n}" for j, n in per_jail.items()) or "aucun") + f"  |  débans : {unbans}"]
    out += [f"  {j:<11} {ip}" for (j, ip) in list(bans)[:10]]
    out.append("Actuellement bannies : " + run(["bash", "-c",
        "for j in $(sudo -n fail2ban-client status | sed -n 's/.*Jail list:\\s*//p' | tr -d ,); do "
        "echo -n \"$j=$(sudo -n fail2ban-client status $j | awk '/Currently banned/{print $NF}') \"; done"]))
    return out


def build(hours):
    now = datetime.now(UTC)
    since = now - timedelta(hours=hours)
    total = Counter()
    status, paths, ips, mcp_ips, uas, errors = Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    mcp = Counter()
    hourly = Counter()
    site_hits = 0
    scans = Counter()
    for ts, m in parse(since):
        total["all"] += 1
        st, path, ip = m["status"], m["path"].split("?")[0], m["ip"]
        status[st[0] + "xx"] += 1
        ips[ip] += 1
        hourly[ts.astimezone().strftime("%H")] += 1
        if path.startswith("/mcp"):
            mcp[f'{m["method"]} {st}'] += 1
            mcp_ips[ip] += 1
        else:
            paths[path] += 1
            if st == "200" and (path.endswith("/") or path.endswith(".html")):
                site_hits += 1
            if st in ("404", "400", "403", "444"):
                scans[path] += 1
        if st.startswith(("4", "5")):
            errors[f'{st} {m["method"]} {path[:60]}'] += 1
        uas["bot/outil" if BOT.search(m["ua"]) else "navigateur/client"] += 1

    out = [f"Bilan nutshell.scamp.fr — {hours} h jusqu'à {now.astimezone():%Y-%m-%d %H:%M}", ""]
    out += ["== HTTP (nginx) ==",
            f"Requêtes : {total['all']}  |  IP distinctes : {len(ips)}",
            "Statuts : " + ", ".join(f"{k}={v}" for k, v in sorted(status.items())),
            f"Pages du site servies (200) : {site_hits}", "",
            "Top chemins (hors /mcp) :", *top(paths),
            "", "Top erreurs 4xx/5xx :", *top(errors),
            "", "Sondes probables (404 fréquents) :", *top(scans, 5),
            "", "Top IP :", *top(ips, 5),
            "", "Clients : " + ", ".join(f"{k}={v}" for k, v in uas.items()), ""]
    n_mcp = sum(mcp.values())
    out += ["== MCP (/mcp) ==",
            f"Requêtes : {n_mcp}  |  IP distinctes : {len(mcp_ips)}",
            "Détail : " + (", ".join(f"{k}={v}" for k, v in mcp.most_common()) or "aucune"),
            "IP les plus actives :", *top(mcp_ips, 5), ""]
    if hourly:
        out += ["Activité par heure (locale) :",
                "  " + " ".join(f"{h}h:{hourly[h]}" for h in sorted(hourly)), ""]

    j = run(["journalctl", "-u", UNIT, "--since", f"{hours} hours ago", "--no-pager", "-o", "cat"])
    starts = len(re.findall(r"Started ", j))
    tb = j.count("Traceback")
    errs = [l for l in j.splitlines() if re.search(r"\b(ERROR|CRITICAL)\b|Traceback", l)]
    sessions = j.count("Created new transport")
    out += ["== Serveur MCP (journald) ==",
            f"Service : {run(['systemctl', 'is-active', UNIT])}  |  démarrages : {starts}  |  sessions créées : {sessions}",
            f"Erreurs/tracebacks : {len(errs)} ({tb} tracebacks)"]
    out += ["  " + l[:160] for l in errs[-5:]]
    out += [""] + fail2ban_section(since.astimezone().replace(tzinfo=None))
    out += ["", "== Système =="]
    du = shutil.disk_usage("/")
    out += [f"Disque / : {du.used / du.total:.0%} utilisé ({du.free / 2**30:.0f} Go libres)",
            "Services : " + ", ".join(f"{u}={run(['systemctl', 'is-active', u])}" for u in ("nginx", UNIT, "exim4")),
            "Queue exim : " + run(["sudo", "-n", "exim4", "-bpc"]),
            "Certificat TLS : " + run(["bash", "-c",
                "sudo -n openssl x509 -enddate -noout -in /etc/letsencrypt/live/nutshell.scamp.fr/fullchain.pem 2>&1"]),
            ]
    return "\n".join(out) + "\n", errs, status.get("5xx", 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", default="sebastien.campion@gmail.com")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--stdout", action="store_true")
    a = ap.parse_args()
    body, errs, n5xx = build(a.hours)
    if a.stdout:
        sys.stdout.write(body)
        return
    flag = " ⚠" if errs or n5xx else ""
    msg = EmailMessage()
    msg["From"] = "nutshell-report <debian@nutshell.scamp.fr>"
    msg["To"] = a.to
    msg["Subject"] = f"[nutshell] Bilan quotidien {datetime.now():%Y-%m-%d}{flag}"
    msg.set_content(body)
    subprocess.run(["/usr/sbin/sendmail", "-t", "-oi"], input=msg.as_bytes(), check=True)


if __name__ == "__main__":
    main()
