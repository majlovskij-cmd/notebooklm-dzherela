#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notebooklm-dzherela engine.

Turns several deep-research exports (Perplexity / Parallel / Gemini / GPT / any)
into a NotebookLM-ready pack WITHOUT changing the wording of the research:

  1. A cleaned, copy-ready TEXT for every synthesis (URLs + citation markers stripped).
  2. One deduplicated, priority-ordered list of external source URLs.
  3. A list of URLs removed because they matched an excluded domain (optional).
  4. A plain-text report (per-file counts, unique total, limit math, top domains).
  5. An offline HTML "copy center" with one Copy button per synthesis + a URLs tab.

Nothing is invented, rewritten or summarised. Only removed: URLs, footnote/citation
markers, and trailing "Sources" sections. Wording is preserved verbatim.

Usage:
    python3 build.py /path/to/config.json

See references/config.md for the config schema.
"""
import re, json, os, sys
from collections import Counter
from urllib.parse import urlparse

URL_RE = re.compile(r'https?://[^\s)\]>"}　]+')

# ---------------------------------------------------------------- helpers
def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()

def clean_url(u):
    return u.rstrip('.,;*)>»"\'​ ')

def norm(u):
    """Normalisation key for dedup (host + path, lowercased, tracking stripped)."""
    u = clean_url(u)
    m = re.match(r'https?://([^/]+)(.*)', u)
    if not m:
        return u.lower()
    host, path = m.group(1).lower(), m.group(2)
    if host.startswith('www.'):
        host = host[4:]
    path = path.split('#')[0]
    if '?' in path:
        base, q = path.split('?', 1)
        keep = [p for p in q.split('&')
                if not re.match(r'(utm_|ref|fbclid|gclid|igshid|si=|gad_|gbraid|gclsrc)', p)]
        path = base + ('?' + '&'.join(keep) if keep else '')
    path = path.rstrip('/')
    return host + path

def domain_of(u):
    return urlparse(u).netloc.replace('www.', '').lower()

def is_excluded(u, excl):
    lo = u.lower()
    return any(d.lower() in lo for d in excl)

# ---------------------------------------------------------------- cleaning
def clean_synthesis(text, strip_inline_digits=False):
    """Remove links & citation cruft, KEEP wording. Order matters."""
    t = text

    # 1) ChatGPT deep-research citations. The whole block is wrapped in PUA markers:
    #    U+E200 "cite" U+E202 "turn27view0" U+E202 "turn26view0" ... U+E201
    #    Match the ENTIRE block start..end (non-greedy stops at its own U+E201).
    t = re.sub('\ue200.*?\ue201', '', t, flags=re.S)
    t = re.sub('[\ue000-\uf8ff]', '', t)                # any stray PUA char
    # fallback for de-wrapped tokens ("citeturn27view0turn26view0", "turn3search14")
    t = re.sub(r'cite(?:turn\d+[a-z]*\d*)+', '', t)
    t = re.sub(r'(?:turn\d+(?:view|search|news|image)\d+)+', '', t)

    # 2) trailing "Sources / References / Джерела / Источники" section -> drop to EOF
    t = re.sub(r'\n[#>\s]*(Джерела|Источники|Sources|References|Список джерел|Посилання)\s*:?\s*\n.*$',
               '\n', t, flags=re.S | re.I)

    # 3) footnote-list lines like "12. [Title](http...) - desc" or "[^1]: http..."
    def _is_footnote_line(ln):
        return (re.match(r'^\s*\d+\.\s*\[.*\]\(https?://', ln) or
                re.match(r'^\s*\[\^?\d+\]\s*:?\s*https?://', ln))
    t = '\n'.join(ln for ln in t.split('\n') if not _is_footnote_line(ln))

    # 4) bracketed citations that contain a URL: [ label — https://... ]
    t = re.sub(r'\[[^\[\]]*https?://[^\[\]]*\]', '', t)

    # 5) inline markdown links [text](url) -> keep text
    t = re.sub(r'\[([^\]]+)\]\(https?://[^)]+\)', r'\1', t)

    # 6) footnote reference markers [^1] and bare [1] style
    t = re.sub(r'\[\^\d+\]', '', t)

    # 7) any remaining bare URLs
    t = URL_RE.sub('', t)

    # 8) OPTIONAL: flattened superscript citation digits glued to a word/paren/quote,
    #    e.g. "розкоші11." -> "розкоші.". Safe: a digit followed by a letter (Y2K, SS27
    #    when followed by more digits/letters) is never touched because the lookahead
    #    requires a non-word boundary after the digits. Only enable for sources whose
    #    footnotes were flattened into the prose.
    if strip_inline_digits:
        t = re.sub(r'(?<=[)\w"»”’])\d{1,2}(?=[\s.,;:!?)»”"\'’]|$)', '', t)

    # tidy
    t = re.sub(r'\[\s*\]', '', t)
    t = re.sub(r'\(\s*\)', '', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    t = re.sub(r'[ \t]+([,.;:!?])', r'\1', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

# ---------------------------------------------------------------- main
def main(cfg_path):
    cfg = json.loads(read(cfg_path))
    topic      = cfg.get('topic', 'NotebookLM pack')
    out_dir    = cfg['out_dir']
    limit      = int(cfg.get('limit', 300))
    excl       = cfg.get('exclude_domains', []) or []
    sources    = cfg['sources']
    labels     = [s['label'] for s in sources]
    priority   = cfg.get('priority', labels)
    prefix     = cfg.get('file_prefix', 'NotebookLM')
    os.makedirs(out_dir, exist_ok=True)

    by_label = {s['label']: s for s in sources}

    # ---- clean syntheses ----
    syntheses, counts = {}, {}
    for s in sources:
        txt = clean_synthesis(read(s['path']), s.get('strip_inline_digits', False))
        syntheses[s['label']] = txt
        counts[s['label']] = len(txt)
        with open(os.path.join(out_dir, f"{prefix}_{s['label']}_copy_ready.txt"), 'w', encoding='utf-8') as f:
            f.write(txt)

    # ---- pool URLs in priority order, dedup, exclude domains ----
    seen, kept, removed = {}, [], []
    per_label = Counter()
    for label in priority:
        if label not in by_label:
            continue
        for u in URL_RE.findall(read(by_label[label]['path'])):
            u = clean_url(u)
            if not u.startswith('http'):
                continue
            if is_excluded(u, excl):
                removed.append(u)
                continue
            k = norm(u)
            if k in seen:
                continue
            seen[k] = u
            kept.append((label, u))
            per_label[label] += 1

    n_syn = len(sources)
    slots = max(0, limit - n_syn)
    trimmed = []
    if len(kept) > slots:
        trimmed = kept[slots:]      # lowest-priority overflow
        kept = kept[:slots]

    kept_urls = [u for _, u in kept]
    uniq_removed = sorted(set(removed))

    # ---- write URL files ----
    with open(os.path.join(out_dir, f"{prefix}_external_unique_{len(kept_urls)}_URLs.txt"), 'w', encoding='utf-8') as f:
        f.write('\n'.join(kept_urls) + '\n')
    if uniq_removed:
        with open(os.path.join(out_dir, f"{prefix}_removed_excluded_domains_{len(uniq_removed)}.txt"), 'w', encoding='utf-8') as f:
            f.write('\n'.join(uniq_removed) + '\n')

    # ---- report ----
    R = []
    R.append(f"NotebookLM SOURCE PACK — {topic}")
    R.append("=" * 64)
    R.append("")
    R.append("SYNTHESES (cleaned, copy-ready — wording unchanged):")
    for label in labels:
        R.append(f"  • {label:12s} — {counts[label]:7d} chars")
    R.append("")
    R.append(f"UNIQUE EXTERNAL URLS: {len(kept_urls)}")
    for label in priority:
        if label in per_label or label in labels:
            R.append(f"  • {label:12s} — {per_label.get(label,0)} kept")
    R.append("")
    R.append(f"NotebookLM limit: {limit}. {n_syn} syntheses + {len(kept_urls)} URLs = {n_syn+len(kept_urls)} sources.")
    R.append(f"Spare slots: {limit-(n_syn+len(kept_urls))}.")
    if trimmed:
        R.append(f"⚠ Trimmed {len(trimmed)} lowest-priority URLs to fit the limit.")
    R.append("")
    if uniq_removed:
        R.append(f"REMOVED (excluded domains {excl}): {len(uniq_removed)}")
        for u in uniq_removed:
            R.append(f"  ✗ {u}")
        R.append("")
    dom = Counter(domain_of(u) for u in kept_urls)
    R.append("TOP DOMAINS IN POOL:")
    for d, c in dom.most_common(20):
        R.append(f"  {c:3d}  {d}")
    with open(os.path.join(out_dir, f"{prefix}_source_report.txt"), 'w', encoding='utf-8') as f:
        f.write('\n'.join(R) + '\n')

    # ---- HTML copy center ----
    write_html(out_dir, prefix, topic, labels, syntheses, counts, kept_urls, limit, n_syn)

    # ---- machine-readable summary for the calling agent ----
    summary = {
        'out_dir': out_dir, 'topic': topic,
        'syntheses': {l: counts[l] for l in labels},
        'urls_total': len(kept_urls),
        'per_label': dict(per_label),
        'removed': len(uniq_removed),
        'trimmed': len(trimmed),
        'total_sources': n_syn + len(kept_urls),
        'spare': limit - (n_syn + len(kept_urls)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

# ---------------------------------------------------------------- html
def write_html(out_dir, prefix, topic, labels, syntheses, counts, urls, limit, n_syn):
    payload = {'syntheses': syntheses, 'counts': counts, 'urls': urls}
    DATA = json.dumps(payload, ensure_ascii=False)
    urls_text = json.dumps("\n".join(urls), ensure_ascii=False)
    total = n_syn + len(urls)
    html = HTML_TEMPLATE
    html = (html
        .replace('__TITLE__', json_escape_html(topic))
        .replace('__DATA__', DATA)
        .replace('__TABS__', json.dumps(labels, ensure_ascii=False))
        .replace('__URLSTEXT__', urls_text)
        .replace('__NURLS__', str(len(urls)))
        .replace('__TOTAL__', str(total))
        .replace('__LIMIT__', str(limit))
        .replace('__SPARE__', str(limit - total)))
    with open(os.path.join(out_dir, f"{prefix}_copy_center.html"), 'w', encoding='utf-8') as f:
        f.write(html)

def json_escape_html(s):
    return s.replace('<', '&lt;').replace('>', '&gt;')

HTML_TEMPLATE = r"""<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ — NotebookLM copy center</title>
<style>
  :root{ --bg:#f6f7f9; --card:#fff; --ink:#0b0b0c; --sub:#6b7280; --line:#e6e8eb;
         --accent:#111; --accent-ink:#fff; --ok:#16a34a; }
  @media (prefers-color-scheme: dark){
    :root{ --bg:#0f1113; --card:#17191c; --ink:#e9eaec; --sub:#9aa0a6; --line:#2a2d31;
           --accent:#e9eaec; --accent-ink:#0f1113; --ok:#22c55e; } }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
  .wrap{max-width:900px;margin:0 auto;padding:28px 18px 60px;}
  h1{font-size:24px;margin:0 0 4px;letter-spacing:-.01em;}
  .lead{color:var(--sub);margin:0 0 20px;font-size:14px;}
  .tabs{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}
  .tab{border:1px solid var(--line);background:var(--card);border-radius:10px;
       padding:8px 16px;cursor:pointer;font-weight:600;font-size:14px;color:var(--ink);}
  .tab.active{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);}
  .panel{display:none;background:var(--card);border:1px solid var(--line);border-radius:14px;
         padding:20px;box-shadow:0 1px 2px rgba(0,0,0,.03);}
  .panel.active{display:block;}
  .phead{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;}
  .phead h2{margin:0;font-size:19px;}
  .meta{color:var(--sub);font-size:13px;}
  .btn{width:100%;margin:14px 0;background:var(--accent);color:var(--accent-ink);border:0;
       border-radius:12px;padding:14px;font-size:15px;font-weight:700;cursor:pointer;}
  .btn:active{transform:translateY(1px);}
  .btn.done{background:var(--ok);color:#fff;}
  .box{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:14px;
       max-height:340px;overflow:auto;white-space:pre-wrap;font-size:13px;}
  .box.urls{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;}
  .note{font-size:12.5px;color:var(--sub);margin-top:14px;line-height:1.9;}
  .pill{display:inline-block;background:var(--card);border:1px solid var(--line);
        border-radius:999px;padding:3px 11px;font-size:12px;margin-right:6px;}
</style>
</head>
<body>
<div class="wrap">
  <h1>__TITLE__</h1>
  <p class="lead">Відкрий вкладку → «Копіювати весь синтез» → встав у Gemini / NotebookLM.
     Текст очищено від URL і службових citation-маркерів, слова не змінено.</p>
  <div class="tabs" id="tabs"></div>
  <div id="panels"></div>
  <div class="note">
    <span class="pill">Ліміт: __LIMIT__</span>
    <span class="pill">синтезів: <b id="nsyn"></b></span>
    <span class="pill">URL: __NURLS__</span>
    <span class="pill">разом: __TOTAL__</span>
    <span class="pill">запас: __SPARE__</span>
  </div>
</div>
<script>
const DATA = __DATA__;
const TABS = __TABS__;
const URLS_TEXT = __URLSTEXT__;
const tabsEl = document.getElementById('tabs');
const panelsEl = document.getElementById('panels');
document.getElementById('nsyn').textContent = TABS.length;
function fmt(n){return n.toLocaleString('uk-UA');}
function copy(text, btn){
  navigator.clipboard.writeText(text).then(()=>{
    const old = btn.textContent; btn.textContent='✓ Скопійовано'; btn.classList.add('done');
    setTimeout(()=>{btn.textContent=old;btn.classList.remove('done');},1600);
  });
}
TABS.forEach((name,i)=>{
  const t=document.createElement('button');
  t.className='tab'+(i===0?' active':''); t.textContent=name; t.dataset.k=name; tabsEl.appendChild(t);
  const p=document.createElement('div');
  p.className='panel'+(i===0?' active':''); p.dataset.k=name;
  const txt=DATA.syntheses[name]; const c=DATA.counts[name];
  p.innerHTML='<div class="phead"><h2>'+name+'</h2><span class="meta">'+fmt(c)+' символів</span></div>'+
    '<button class="btn">Копіювати весь синтез</button><div class="box"></div>';
  p.querySelector('.box').textContent=txt;
  p.querySelector('.btn').addEventListener('click',e=>copy(txt,e.target));
  panelsEl.appendChild(p);
});
const ut=document.createElement('button');
ut.className='tab'; ut.textContent='Посилання ('+DATA.urls.length+')'; ut.dataset.k='__urls'; tabsEl.appendChild(ut);
const up=document.createElement('div');
up.className='panel'; up.dataset.k='__urls';
up.innerHTML='<div class="phead"><h2>Унікальні зовнішні посилання</h2><span class="meta">'+DATA.urls.length+' URL</span></div>'+
  '<button class="btn">Копіювати всі посилання</button><div class="box urls"></div>';
up.querySelector('.box').textContent=URLS_TEXT;
up.querySelector('.btn').addEventListener('click',e=>copy(URLS_TEXT,e.target));
panelsEl.appendChild(up);
tabsEl.addEventListener('click',e=>{
  const b=e.target.closest('.tab'); if(!b)return;
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===b));
  document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.dataset.k===b.dataset.k));
});
</script>
</body>
</html>
"""

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: python3 build.py config.json", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
