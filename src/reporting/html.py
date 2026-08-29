from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def generate_html(payload: dict[str, Any], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    embedded = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    output.write_text(_template(embedded), encoding="utf-8")


def _template(embedded_json: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="AI Agent early opportunity radar for Kimi API commercial teams">
  <title>Agent Opportunity Radar</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #080b10;
      --panel: #10151d;
      --panel-2: #151c26;
      --line: #26303d;
      --text: #f4f7fb;
      --muted: #91a0b4;
      --lime: #b5f36b;
      --cyan: #63d8ef;
      --amber: #ffcc66;
      --red: #ff7a86;
      --purple: #ba9cff;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: radial-gradient(circle at 78% -10%, #182637 0, transparent 34%), var(--bg); color: var(--text); font: 14px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    a {{ color: inherit; }}
    .shell {{ max-width: 1440px; margin: 0 auto; padding: 28px; }}
    header {{ display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; margin-bottom: 22px; }}
    .eyebrow {{ display: flex; align-items: center; gap: 9px; color: var(--lime); font-size: 12px; font-weight: 800; letter-spacing: .15em; text-transform: uppercase; }}
    .pulse {{ width: 8px; height: 8px; border-radius: 50%; background: var(--lime); box-shadow: 0 0 0 6px #b5f36b1b; }}
    h1 {{ margin: 8px 0 4px; font-size: clamp(28px, 4vw, 48px); line-height: 1.06; letter-spacing: -.045em; }}
    .subtitle {{ color: var(--muted); max-width: 760px; margin: 0; }}
    .run-meta {{ color: var(--muted); text-align: right; font-size: 12px; white-space: nowrap; }}
    .run-meta strong {{ color: var(--text); display: block; font-size: 14px; }}
    .notice {{ display: none; border: 1px solid #8b6a2f; background: #2b2110; color: #ffd98e; border-radius: 10px; padding: 10px 14px; margin: 0 0 18px; }}
    .notice.show {{ display: block; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }}
    .metric {{ background: linear-gradient(145deg, #131a23, #0e131b); border: 1px solid var(--line); border-radius: 14px; padding: 16px; }}
    .metric-label {{ color: var(--muted); font-size: 12px; }}
    .metric-value {{ display: flex; align-items: baseline; gap: 7px; margin-top: 6px; font-size: 28px; font-weight: 760; letter-spacing: -.03em; }}
    .metric-value small {{ font-size: 11px; color: var(--muted); font-weight: 600; }}
    .toolbar {{ display: grid; grid-template-columns: minmax(220px, 1fr) 180px 180px auto; gap: 10px; background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 12px; margin-bottom: 16px; }}
    input, select, button {{ width: 100%; border: 1px solid var(--line); background: #0a0f16; color: var(--text); border-radius: 9px; padding: 10px 12px; font: inherit; }}
    input:focus, select:focus, button:focus-visible {{ outline: 2px solid var(--cyan); outline-offset: 1px; }}
    button {{ width: auto; cursor: pointer; font-weight: 700; }}
    .content {{ display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start; }}
    .list {{ display: grid; gap: 10px; }}
    .card {{ position: relative; display: grid; grid-template-columns: 86px minmax(0, 1fr) 190px; gap: 16px; background: linear-gradient(120deg, #10161f, #0d1219); border: 1px solid var(--line); border-radius: 14px; padding: 16px; overflow: hidden; }}
    .card::before {{ content: ""; position: absolute; inset: 0 auto 0 0; width: 3px; background: var(--cyan); }}
    .card.contact::before {{ background: var(--lime); }}
    .card.skip::before {{ background: #526070; }}
    .score {{ display: grid; place-items: center; align-content: center; width: 72px; height: 72px; border: 1px solid #334052; border-radius: 50%; background: #0a1017; }}
    .score strong {{ font-size: 24px; line-height: 1; }}
    .score span {{ color: var(--muted); font-size: 10px; margin-top: 4px; }}
    .card-title {{ display: flex; gap: 9px; align-items: center; flex-wrap: wrap; margin: 0 0 4px; font-size: 17px; }}
    .card-title a {{ text-decoration: none; }}
    .card-title a:hover {{ text-decoration: underline; }}
    .tag {{ border: 1px solid #364457; color: #b9c7d9; border-radius: 999px; padding: 2px 7px; font-size: 10px; font-weight: 700; }}
    .type-openclaw {{ color: var(--cyan); border-color: #285c69; }}
    .type-manus {{ color: var(--purple); border-color: #55427f; }}
    .description {{ color: #c1ccda; margin: 0 0 10px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
    .reason {{ color: var(--text); margin: 0; }}
    .reason::before {{ content: "Why now  "; color: var(--lime); font-size: 10px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }}
    .source-row {{ display: flex; flex-wrap: wrap; gap: 7px; margin-top: 11px; color: var(--muted); font-size: 11px; }}
    .source-row span {{ border-right: 1px solid var(--line); padding-right: 7px; }}
    .source-row span:last-child {{ border: 0; }}
    .dimensions {{ display: grid; gap: 7px; align-content: center; }}
    .dimension {{ display: grid; grid-template-columns: 64px 1fr 27px; align-items: center; gap: 7px; color: var(--muted); font-size: 10px; }}
    .bar {{ height: 5px; background: #242e3a; border-radius: 10px; overflow: hidden; }}
    .bar i {{ display: block; height: 100%; background: linear-gradient(90deg, var(--cyan), var(--lime)); border-radius: inherit; }}
    aside {{ position: sticky; top: 16px; display: grid; gap: 12px; }}
    .side-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 16px; }}
    .side-card h2 {{ font-size: 13px; margin: 0 0 10px; }}
    .side-card p, .side-card li {{ color: var(--muted); font-size: 12px; }}
    .side-card ul {{ margin: 0; padding-left: 18px; }}
    .legend {{ display: grid; gap: 9px; }}
    .legend div {{ display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: 12px; }}
    .legend strong {{ color: var(--text); }}
    .empty {{ display: none; padding: 40px; text-align: center; color: var(--muted); border: 1px dashed var(--line); border-radius: 14px; }}
    footer {{ color: var(--muted); font-size: 11px; margin-top: 24px; text-align: center; }}
    @media (max-width: 980px) {{ .content {{ grid-template-columns: 1fr; }} aside {{ position: static; grid-template-columns: 1fr 1fr; }} .card {{ grid-template-columns: 74px 1fr; }} .dimensions {{ grid-column: 1 / -1; }} }}
    @media (max-width: 680px) {{ .shell {{ padding: 18px 12px; }} header {{ display: block; }} .run-meta {{ text-align: left; margin-top: 12px; }} .metrics {{ grid-template-columns: 1fr 1fr; }} .toolbar {{ grid-template-columns: 1fr 1fr; }} .toolbar input {{ grid-column: 1 / -1; }} .card {{ grid-template-columns: 1fr; }} .score {{ width: 60px; height: 60px; }} aside {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div>
        <div class="eyebrow"><span class="pulse"></span>Commercial Signal Intelligence</div>
        <h1>Agent Opportunity Radar</h1>
        <p class="subtitle">从公开开发者与产品信号中，提前发现可能成为Kimi API客户、生态伙伴或重要竞品的Agent项目。</p>
      </div>
      <div class="run-meta"><strong id="generatedAt">—</strong><span id="mode">—</span></div>
    </header>
    <div id="notice" class="notice"></div>
    <section class="metrics" aria-label="Radar summary">
      <div class="metric"><div class="metric-label">入榜候选</div><div class="metric-value" id="metricTotal">0<small id="metricPool">shortlisted</small></div></div>
      <div class="metric"><div class="metric-label">立即联系</div><div class="metric-value" id="metricContact">0<small>priority</small></div></div>
      <div class="metric"><div class="metric-label">OpenClaw型</div><div class="metric-value" id="metricOpen">0<small>ecosystem</small></div></div>
      <div class="metric"><div class="metric-label">Manus型</div><div class="metric-value" id="metricManus">0<small>product</small></div></div>
    </section>
    <section class="toolbar" aria-label="Filters">
      <input id="search" type="search" placeholder="搜索项目、证据或商业价值…" aria-label="搜索项目">
      <select id="typeFilter" aria-label="项目类型"><option value="">全部类型</option><option>OpenClaw型</option><option>Manus型</option><option>其他Agent</option></select>
      <select id="actionFilter" aria-label="推荐动作"><option value="">全部动作</option><option>立即联系</option><option>持续观察</option><option>暂不跟进</option></select>
      <button id="reset" type="button">重置</button>
    </section>
    <div class="content">
      <section>
        <div id="list" class="list"></div>
        <div id="empty" class="empty">没有符合当前筛选条件的项目。</div>
      </section>
      <aside>
        <section class="side-card">
          <h2>判断框架</h2>
          <div class="legend">
            <div><span>增长速度</span><strong>25%</strong></div>
            <div><span>Agent创新性</span><strong>20%</strong></div>
            <div><span>社区与用户信号</span><strong>20%</strong></div>
            <div><span>API消耗潜力</span><strong>15%</strong></div>
            <div><span>商业化成熟度</span><strong>10%</strong></div>
            <div><span>Kimi战略适配</span><strong>10%</strong></div>
          </div>
        </section>
        <section class="side-card">
          <h2>销售使用方式</h2>
          <ul>
            <li>立即联系：补全创始人与模型栈，进入销售线索。</li>
            <li>持续观察：跟踪增速、定价、融资和API依赖。</li>
            <li>暂不跟进：保留历史，不占用SDR精力。</li>
          </ul>
        </section>
      </aside>
    </div>
    <footer>Public-signal prototype · Scores support prioritization and require human review.</footer>
  </main>
  <script id="radar-data" type="application/json">{embedded_json}</script>
  <script>
    const payload = JSON.parse(document.getElementById('radar-data').textContent);
    const candidates = payload.candidates || [];
    const labels = {{growth_speed:'增速',agent_innovation:'创新',community_signal:'社区',api_consumption_potential:'API潜力',commercialization:'商业化',kimi_strategic_fit:'Kimi适配'}};
    const list = document.getElementById('list');
    const empty = document.getElementById('empty');
    const search = document.getElementById('search');
    const typeFilter = document.getElementById('typeFilter');
    const actionFilter = document.getElementById('actionFilter');
    const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}}[ch]));
    const typeClass = value => value === 'OpenClaw型' ? 'type-openclaw' : value === 'Manus型' ? 'type-manus' : '';
    const actionClass = value => value === '立即联系' ? 'contact' : value === '暂不跟进' ? 'skip' : '';
    function render() {{
      const term = search.value.trim().toLowerCase();
      const filtered = candidates.filter(c => {{
        const haystack = [c.name,c.description,c.reason_to_contact_now,c.commercial_summary,c.source].join(' ').toLowerCase();
        return (!term || haystack.includes(term)) && (!typeFilter.value || c.opportunity_type === typeFilter.value) && (!actionFilter.value || c.recommended_action === actionFilter.value);
      }});
      list.innerHTML = filtered.map(c => `
        <article class="card ${{actionClass(c.recommended_action)}}">
          <div class="score"><strong>${{Math.round(c.score)}}</strong><span>OPPORTUNITY</span></div>
          <div>
            <h2 class="card-title"><a href="${{esc(c.url)}}" target="_blank" rel="noopener">${{esc(c.name)}}</a><span class="tag ${{typeClass(c.opportunity_type)}}">${{esc(c.opportunity_type)}}</span><span class="tag">${{esc(c.recommended_action)}}</span></h2>
            <p class="description">${{esc(c.description)}}</p>
            <p class="reason">${{esc(c.reason_to_contact_now)}}</p>
            <div class="source-row"><span>${{esc(c.source)}}</span><span>${{esc(c.commercial_summary)}}</span><span>${{esc(c.confidence)}} confidence</span></div>
          </div>
          <div class="dimensions">${{Object.entries(c.dimension_scores || {{}}).map(([key,value]) => `<div class="dimension"><span>${{labels[key] || key}}</span><div class="bar"><i style="width:${{Math.max(0,Math.min(100,value))}}%"></i></div><b>${{Math.round(value)}}</b></div>`).join('')}}</div>
        </article>`).join('');
      empty.style.display = filtered.length ? 'none' : 'block';
    }}
    document.getElementById('generatedAt').textContent = payload.meta?.generated_at_display || payload.meta?.generated_at || '—';
    document.getElementById('mode').textContent = payload.meta?.mode || '—';
    document.getElementById('metricTotal').childNodes[0].nodeValue = candidates.length;
    document.getElementById('metricPool').textContent = `shortlisted / ${{payload.meta?.candidate_pool_size || candidates.length}} pool`;
    document.getElementById('metricContact').childNodes[0].nodeValue = candidates.filter(c => c.recommended_action === '立即联系').length;
    document.getElementById('metricOpen').childNodes[0].nodeValue = candidates.filter(c => c.opportunity_type === 'OpenClaw型').length;
    document.getElementById('metricManus').childNodes[0].nodeValue = candidates.filter(c => c.opportunity_type === 'Manus型').length;
    const messages = [...(payload.meta?.warnings || []), ...(payload.meta?.notices || [])];
    if (messages.length) {{ const notice = document.getElementById('notice'); notice.textContent = messages.join(' · '); notice.classList.add('show'); }}
    [search,typeFilter,actionFilter].forEach(el => el.addEventListener('input', render));
    document.getElementById('reset').addEventListener('click', () => {{ search.value=''; typeFilter.value=''; actionFilter.value=''; render(); }});
    render();
  </script>
</body>
</html>"""
