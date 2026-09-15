import json, pathlib, datetime

root = pathlib.Path(__file__).parent
r = root / "research"

# Load wave-1 industries (research/*.json, excluding factory.json)
industries = []
for p in sorted(r.glob("*.json")):
    if p.name == "factory.json":
        continue
    industries.append(json.loads(p.read_text(encoding="utf-8-sig")))

# Load wave-2 industries (research/wave2/*.json)
w2 = r / "wave2"
if w2.is_dir():
    for p in sorted(w2.glob("*.json")):
        industries.append(json.loads(p.read_text(encoding="utf-8-sig")))

factory = json.loads((r / "factory.json").read_text(encoding="utf-8-sig")) if (r / "factory.json").exists() else {}

# recompute scores for consistency and report stats
for ind in industries:
    n = 0
    for d in ind.get("domains", []):
        for g in d.get("groups", []):
            for c in g.get("capabilities", []):
                c["whitespace_score"] = int(c["ai_readiness"]) * (6 - int(c["market_coverage"]))
                n += 1
    print(ind["industry"], "domains", len(ind.get("domains", [])), "caps", n, "sources", len(ind.get("sources", [])))

data = json.dumps({"industries": industries, "factory": factory}, ensure_ascii=False).replace("</", "<\\/")
html = (root / "template.html").read_text(encoding="utf-8")
html = html.replace("__DATA__", data).replace("__DATE__", datetime.date.today().isoformat())
(root / "whitespace-atlas.html").write_text(html, encoding="utf-8")
print("wrote whitespace-atlas.html", len(html) // 1024, "KB")
