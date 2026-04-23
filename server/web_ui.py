from __future__ import annotations


def render_web_ui() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Blackstart City</title>
    <style>
      :root {
        --bg: #07111f;
        --panel: #0f172a;
        --panel-2: #111827;
        --border: #334155;
        --text: #e2e8f0;
        --muted: #94a3b8;
        --accent: #f59e0b;
        --danger: #ef4444;
        --safe: #22c55e;
        --warn: #eab308;
      }
      body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 2rem;
        background:
          radial-gradient(circle at top, rgba(245,158,11,0.12), transparent 35%),
          linear-gradient(180deg, #020617 0%, var(--bg) 100%);
        color: var(--text);
      }
      .hero {
        display: grid;
        grid-template-columns: 1.1fr 0.9fr;
        gap: 1.5rem;
        margin-bottom: 1.5rem;
      }
      .card {
        background: linear-gradient(180deg, rgba(17,24,39,0.95), rgba(15,23,42,0.95));
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 20px 60px rgba(2,6,23,0.45);
      }
      h1, h2, h3 { margin: 0 0 0.75rem; }
      p { color: var(--muted); line-height: 1.55; }
      code { color: var(--accent); }
      ul { line-height: 1.6; margin: 0; padding-left: 1.2rem; }
      .grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }
      .stats {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin-top: 1rem;
      }
      .stat {
        border: 1px solid rgba(148,163,184,0.2);
        border-radius: 12px;
        padding: 0.8rem;
        background: rgba(15,23,42,0.65);
      }
      .stat strong {
        display: block;
        font-size: 1.2rem;
        color: white;
      }
      .badge {
        display: inline-block;
        font-size: 0.78rem;
        padding: 0.2rem 0.45rem;
        border-radius: 999px;
        border: 1px solid rgba(148,163,184,0.25);
        color: var(--muted);
        margin-right: 0.35rem;
      }
      .map-wrap {
        background: radial-gradient(circle at 50% 35%, rgba(34,197,94,0.08), transparent 45%), #020617;
        border-radius: 16px;
        border: 1px solid rgba(148,163,184,0.14);
        padding: 0.6rem;
      }
      svg { width: 100%; height: auto; display: block; }
      .legend {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-top: 0.75rem;
        color: var(--muted);
        font-size: 0.9rem;
      }
      .dot {
        width: 0.8rem;
        height: 0.8rem;
        border-radius: 999px;
        display: inline-block;
        margin-right: 0.35rem;
      }
      .small {
        font-size: 0.92rem;
        color: var(--muted);
      }
      .controls {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        align-items: center;
      }
      button, select, input, textarea {
        background: #0b1220;
        color: var(--text);
        border: 1px solid rgba(148,163,184,0.25);
        border-radius: 10px;
        padding: 0.65rem 0.8rem;
        font: inherit;
      }
      button {
        cursor: pointer;
        background: linear-gradient(180deg, #1d4ed8, #1e40af);
        border-color: rgba(96,165,250,0.4);
      }
      button.secondary {
        background: linear-gradient(180deg, #374151, #1f2937);
      }
      button.warn {
        background: linear-gradient(180deg, #b45309, #92400e);
      }
      textarea {
        width: 100%;
        min-height: 132px;
        resize: vertical;
        font-family: Consolas, monospace;
        font-size: 0.92rem;
      }
      .data-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }
      .list {
        display: grid;
        gap: 0.55rem;
      }
      .item {
        border: 1px solid rgba(148,163,184,0.16);
        border-radius: 12px;
        padding: 0.75rem 0.85rem;
        background: rgba(2, 6, 23, 0.55);
      }
      .item strong {
        color: white;
      }
      .item-line {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
      }
      .tag {
        display: inline-block;
        border-radius: 999px;
        padding: 0.16rem 0.45rem;
        font-size: 0.78rem;
        margin-right: 0.35rem;
      }
      .tag.safe { background: rgba(34,197,94,0.15); color: #86efac; }
      .tag.warn { background: rgba(234,179,8,0.15); color: #fde047; }
      .tag.danger { background: rgba(239,68,68,0.15); color: #fca5a5; }
      .mono {
        font-family: Consolas, monospace;
        color: #cbd5e1;
      }
      .warning-list li { color: #fcd34d; }
      .log {
        max-height: 280px;
        overflow: auto;
        font-family: Consolas, monospace;
        font-size: 0.9rem;
        line-height: 1.5;
        white-space: pre-wrap;
        color: #cbd5e1;
      }
      .footer-note {
        color: var(--muted);
        font-size: 0.88rem;
        margin-top: 0.5rem;
      }
      .compare-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }
      .compare-card {
        border: 1px solid rgba(148,163,184,0.18);
        border-radius: 14px;
        padding: 0.9rem;
        background: rgba(2, 6, 23, 0.45);
      }
      .objective-box {
        border: 1px solid rgba(148,163,184,0.18);
        border-radius: 14px;
        padding: 0.85rem 0.95rem;
        background: rgba(2, 6, 23, 0.38);
        margin-bottom: 0.85rem;
      }
      .objective-box strong {
        color: white;
      }
      .overlay-banner {
        border-radius: 12px;
        padding: 0.55rem 0.7rem;
        margin-top: 0.6rem;
        font-size: 0.9rem;
        border: 1px solid rgba(148,163,184,0.18);
        background: rgba(2, 6, 23, 0.4);
      }
      .overlay-banner.safe { color: #86efac; border-color: rgba(34,197,94,0.35); }
      .overlay-banner.warn { color: #fde047; border-color: rgba(234,179,8,0.35); }
      .overlay-banner.danger { color: #fca5a5; border-color: rgba(239,68,68,0.35); }
      .reward-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 0.6rem;
        margin-top: 0.6rem;
      }
      .reward-item {
        background: rgba(15,23,42,0.45);
        border: 1px solid rgba(148,163,184,0.12);
        border-radius: 8px;
        padding: 0.5rem;
        text-align: center;
      }
      .reward-item .val {
        display: block;
        font-weight: 700;
        font-size: 1rem;
        margin-top: 0.2rem;
      }
      .reward-item.plus .val { color: #86efac; }
      .reward-item.minus .val { color: #fca5a5; }
      @media (max-width: 980px) {
        .hero, .grid, .stats, .data-grid, .compare-grid {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <div class="hero">
      <div class="card">
        <div class="badge">OpenEnv</div>
        <div class="badge">Wild Card / Long-Horizon</div>
        <h1>Blackstart City</h1>
        <p>An AI restoration commander must bring a dark city back to life before hospitals exhaust backup power, telecom towers fail, water pressure collapses, and one unsafe reconnection triggers a second blackout.</p>
        <div class="stats">
          <div class="stat"><span class="small">Task Families</span><strong>3</strong></div>
          <div class="stat"><span class="small">Critical Systems</span><strong>4</strong></div>
          <div class="stat"><span class="small">Score Range</span><strong>0.01-0.99</strong></div>
          <div class="stat"><span class="small">Main Failure</span><strong>2nd Collapse</strong></div>
        </div>
      </div>
      <div class="card">
        <h2>Demo Narrative</h2>
        <ul>
          <li>Hospitals start on backup power and lose minutes every step.</li>
          <li>Telecom outages reduce visibility and destabilize recovery.</li>
          <li>Water plants create city-scale penalties if left dark.</li>
          <li>Unsafe line closures can trip feeders and restart the blackout.</li>
        </ul>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>City Map</h2>
        <div class="map-wrap">
          <svg viewBox="0 0 700 430" aria-label="Blackstart City map">
            <defs>
              <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            <rect x="20" y="20" width="660" height="390" rx="22" fill="#04101e" stroke="#1e293b" />
            <line id="map-line-south-core" x1="170" y1="210" x2="325" y2="110" stroke="#ef4444" stroke-width="8" stroke-dasharray="14 9"/>
            <line id="map-line-south-medical" x1="170" y1="210" x2="330" y2="320" stroke="#22c55e" stroke-width="8"/>
            <line id="map-line-medical-east" x1="330" y1="320" x2="520" y2="240" stroke="#eab308" stroke-width="8"/>
            <line id="map-line-core-east" x1="325" y1="110" x2="520" y2="240" stroke="#ef4444" stroke-width="8" stroke-dasharray="14 9"/>

            <circle id="map-bus-south" cx="170" cy="210" r="28" fill="#22c55e" filter="url(#glow)"/>
            <circle id="map-bus-core" cx="325" cy="110" r="28" fill="#0ea5e9"/>
            <circle id="map-bus-medical" cx="330" cy="320" r="28" fill="#0ea5e9"/>
            <circle id="map-bus-east" cx="520" cy="240" r="28" fill="#f59e0b"/>

            <rect id="map-critical-hospital" x="85" y="110" width="78" height="46" rx="12" fill="#111827" stroke="#ef4444"/>
            <text id="map-label-hospital" x="124" y="139" text-anchor="middle" fill="#e2e8f0" font-size="18">Hospital</text>
            <rect id="map-critical-telecom" x="536" y="85" width="98" height="46" rx="12" fill="#111827" stroke="#eab308"/>
            <text id="map-label-telecom" x="585" y="114" text-anchor="middle" fill="#e2e8f0" font-size="18">Telecom</text>
            <rect id="map-critical-water" x="552" y="292" width="88" height="46" rx="12" fill="#111827" stroke="#ef4444"/>
            <text id="map-label-water" x="596" y="321" text-anchor="middle" fill="#e2e8f0" font-size="18">Water</text>
            <text id="map-timer-hospital" x="124" y="168" text-anchor="middle" fill="#fca5a5" font-size="14" font-weight="700">24 min</text>
            <text id="map-timer-telecom" x="585" y="143" text-anchor="middle" fill="#fde047" font-size="14" font-weight="700">15 min</text>
            <text id="map-timer-water" x="596" y="350" text-anchor="middle" fill="#fca5a5" font-size="14" font-weight="700">22 min</text>

            <rect x="34" y="350" width="218" height="32" rx="10" fill="#0b1220" stroke="#334155"/>
            <text id="map-banner-frequency" x="48" y="371" fill="#e2e8f0" font-size="14">Frequency stable</text>
            <rect x="268" y="350" width="198" height="32" rx="10" fill="#0b1220" stroke="#334155"/>
            <text id="map-banner-reserve" x="282" y="371" fill="#e2e8f0" font-size="14">Reserve margin healthy</text>
            <rect x="482" y="350" width="178" height="32" rx="10" fill="#0b1220" stroke="#334155"/>
            <text id="map-banner-risk" x="496" y="371" fill="#e2e8f0" font-size="14">No collapse risk</text>

            <text id="map-bus-label-south" x="170" y="216" text-anchor="middle" fill="#020617" font-size="18" font-weight="700">South Gen</text>
            <text id="map-bus-label-core" x="325" y="116" text-anchor="middle" fill="#020617" font-size="18" font-weight="700">Core</text>
            <text id="map-bus-label-medical" x="330" y="326" text-anchor="middle" fill="#020617" font-size="18" font-weight="700">Medical</text>
            <text id="map-bus-label-east" x="520" y="246" text-anchor="middle" fill="#020617" font-size="18" font-weight="700">East</text>

            <text id="map-line-label-a" x="256" y="150" text-anchor="middle" fill="#94a3b8" font-size="15">damaged tie-line</text>
            <text id="map-line-label-b" x="410" y="176" text-anchor="middle" fill="#94a3b8" font-size="15">unsafe corridor</text>
            <text id="map-line-label-c" x="250" y="282" text-anchor="middle" fill="#94a3b8" font-size="15">safe energized path</text>
          </svg>
        </div>
        <div class="legend">
          <span><span class="dot" style="background:#22c55e"></span>online generation</span>
          <span><span class="dot" style="background:#0ea5e9"></span>substation / bus</span>
          <span><span class="dot" style="background:#f59e0b"></span>critical node on backup</span>
          <span><span class="dot" style="background:#ef4444"></span>damaged or unsafe path</span>
        </div>
      </div>

      <div class="card">
        <h2>Primary Tasks</h2>
        <ul>
          <li><code>local_blackstart</code>: restore one district hospital and a telecom node before backup expires</li>
          <li><code>island_rejoin</code>: inspect a hidden-damage tie-line and safely reconnect islands</li>
          <li><code>city_cascade_recovery</code>: restore city-scale critical services while avoiding a second collapse</li>
        </ul>
        <h3 style="margin-top:1rem;">Reward Breakdown</h3>
        <ul>
          <li>critical-service restoration</li>
          <li>safe load restoration</li>
          <li>stability and reserve margin</li>
          <li>inspection quality</li>
          <li>communication accuracy</li>
          <li>catastrophe penalties</li>
        </ul>
      </div>
    </div>

    <div class="card" style="margin-top:1rem;">
        <h2>Interactive Rollout</h2>
      <div class="controls" style="margin-bottom:0.8rem;">
        <label>Task
          <select id="task-select">
            <option value="local_blackstart">local_blackstart</option>
            <option value="island_rejoin">island_rejoin</option>
            <option value="city_cascade_recovery">city_cascade_recovery</option>
          </select>
        </label>
        <label>Seed <input id="seed-input" type="number" value="0" min="0" style="width:90px"></label>
        <button id="reset-btn">Reset Scenario</button>
        <button id="heuristic-btn" class="secondary">Heuristic Step</button>
        <button id="auto-btn" class="warn">Autoplay Heuristic</button>
        <button id="suggest-btn" class="secondary">Suggest Action</button>
      </div>
      <div class="objective-box">
        <div class="small">Incident</div>
        <strong id="incident-id">-</strong>
        <div class="small" style="margin-top:0.45rem;">Scenario</div>
        <strong id="scenario-title">-</strong>
        <div class="small" style="margin-top:0.45rem;">Objective</div>
        <div id="scenario-objective" class="small">-</div>
      </div>
      <div class="data-grid">
        <div class="card" style="padding:0.9rem;">
          <h3>Live State</h3>
          <div class="stats" style="grid-template-columns: repeat(4, minmax(0, 1fr));">
            <div class="stat"><span class="small">Step</span><strong id="metric-step">-</strong></div>
            <div class="stat"><span class="small">Frequency</span><strong id="metric-frequency">-</strong></div>
            <div class="stat"><span class="small">Reserve</span><strong id="metric-reserve">-</strong></div>
            <div class="stat"><span class="small">Score</span><strong id="metric-score">-</strong></div>
          </div>
          <div class="stats" style="grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top:0.75rem;">
            <div class="stat"><span class="small">Generation</span><strong id="metric-gen">-</strong></div>
            <div class="stat"><span class="small">Served Load</span><strong id="metric-load">-</strong></div>
            <div class="stat"><span class="small">Unstable Islands</span><strong id="metric-islands">-</strong></div>
            <div class="stat"><span class="small">Done</span><strong id="metric-done">-</strong></div>
          </div>
          <div class="footer-note" id="last-result">No rollout yet.</div>
          <div id="overlay-frequency" class="overlay-banner safe">Grid frequency stable.</div>
          <div id="overlay-reserve" class="overlay-banner safe">Reserve margin healthy.</div>
          <div id="overlay-risk" class="overlay-banner safe">No immediate second-collapse risk.</div>

          <h3 style="margin-top:1.2rem;">Reward Decomposition</h3>
          <div class="reward-grid" id="reward-decomposition"></div>
        </div>

        <div class="card" style="padding:0.9rem;">
          <h3>Suggested / Manual Action</h3>
          <textarea id="action-json">{"action_type":"start_generator","target_id":"gen_south_blackstart"}</textarea>
          <div class="controls" style="margin-top:0.75rem;">
            <button id="step-btn">Submit Action</button>
          </div>
          <div class="footer-note">Use <code>Suggest Action</code> for the current heuristic next move, then edit if needed.</div>
        </div>
      </div>
    </div>

    <div class="grid" style="margin-top:1rem;">
      <div class="card">
        <h2>Critical Nodes</h2>
        <div id="critical-list" class="list"></div>
      </div>

      <div class="card">
        <h2>Grid Assets</h2>
        <div id="asset-list" class="list"></div>
      </div>
    </div>

    <div class="grid" style="margin-top:1rem;">
      <div class="card">
        <h2>Warnings</h2>
        <ul id="warning-list" class="warning-list"></ul>
      </div>

      <div class="card">
        <h2>Rollout Log</h2>
        <div id="rollout-log" class="log"></div>
      </div>
    </div>

    <div class="card" style="margin-top:1rem;">
      <h2>Policy Comparison</h2>
      <div class="controls" style="margin-bottom:0.8rem;">
        <button id="compare-btn">Run Greedy vs Heuristic</button>
      </div>
      <div class="compare-grid">
        <div class="compare-card">
          <h3>Greedy Policy</h3>
          <div id="compare-greedy-summary" class="small">No comparison yet.</div>
          <div id="compare-greedy-log" class="log" style="margin-top:0.6rem; max-height:220px;"></div>
        </div>
        <div class="compare-card">
          <h3>Heuristic Policy</h3>
          <div id="compare-heuristic-summary" class="small">No comparison yet.</div>
          <div id="compare-heuristic-log" class="log" style="margin-top:0.6rem; max-height:220px;"></div>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:1rem;">
      <h2>API</h2>
      <ul>
        <li><code>POST /reset</code> with <code>{ "task_id": ..., "seed": ... }</code></li>
        <li><code>POST /step</code> with a typed <code>BlackstartAction</code></li>
        <li><code>GET /state</code>, <code>/tasks</code>, <code>/grader</code>, <code>/schema</code></li>
        <li><code>GET /baseline/next</code> and <code>POST /baseline/step</code> for live heuristic demos</li>
        <li><code>POST /compare</code> for greedy vs heuristic rollout comparison</li>
      </ul>
    </div>

    <script>
      let currentObservation = null;
      let autoplayHandle = null;

      function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      }

      function appendLog(line) {
        const log = document.getElementById('rollout-log');
        log.textContent += line + "\\n";
        log.scrollTop = log.scrollHeight;
      }

      function formatTags(tags) {
        return tags.map(tag => `<span class="tag ${tag.kind}">${tag.label}</span>`).join('');
      }

      function renderCriticalNodes(nodes) {
        const container = document.getElementById('critical-list');
        container.innerHTML = nodes.map(node => {
          const tags = [];
          tags.push({ kind: node.powered ? 'safe' : (node.backup_minutes_remaining <= 15 ? 'danger' : 'warn'), label: node.powered ? 'powered' : 'backup' });
          tags.push({ kind: node.type === 'hospital' ? 'danger' : node.type === 'water' ? 'warn' : 'safe', label: node.type });
          return `
            <div class="item">
              <div class="item-line">
                <strong>${node.id}</strong>
                <span>${formatTags(tags)}</span>
              </div>
              <div class="small">Demand: ${node.demand_mw} MW | Backup: ${node.backup_minutes_remaining} min | Impact: ${node.population_impact.toLocaleString()}</div>
            </div>
          `;
        }).join('');
      }

      function renderAssets(observation) {
        const container = document.getElementById('asset-list');
        const generatorItems = observation.generators.map(item => `
          <div class="item">
            <div class="item-line">
              <strong>${item.id}</strong>
              <span>${item.online ? '<span class="tag safe">online</span>' : '<span class="tag danger">offline</span>'}</span>
            </div>
            <div class="small">Bus: ${item.bus} | Capacity: ${item.capacity_mw} MW</div>
          </div>
        `).join('');
        const lineItems = observation.lines.map(item => `
          <div class="item">
            <div class="item-line">
              <strong>${item.id}</strong>
              <span class="mono">${item.from_bus} → ${item.to_bus}</span>
            </div>
            <div class="small">
              ${item.closed ? '<span class="tag safe">closed</span>' : '<span class="tag warn">open</span>'}
              ${item.tripped ? '<span class="tag danger">tripped</span>' : ''}
              ${item.inspected ? '<span class="tag safe">inspected</span>' : ''}
              ${item.damaged ? '<span class="tag danger">damaged</span>' : ''}
              | Flow ${item.current_flow_mw}/${item.capacity_mw} MW
            </div>
          </div>
        `).join('');
        container.innerHTML = generatorItems + lineItems;
      }

      function renderWarnings(warnings) {
        const container = document.getElementById('warning-list');
        container.innerHTML = warnings.map(item => `<li>${item}</li>`).join('');
      }

      function statusColor(powered, severity) {
        if (powered === true) return '#22c55e';
        if (severity === 'danger') return '#ef4444';
        if (severity === 'warn') return '#eab308';
        return '#64748b';
      }

      function updateMap(observation) {
        const subMap = {};
        for (const sub of observation.substations) {
          subMap[sub.id] = sub;
        }
        const lineMap = {};
        for (const line of observation.lines) {
          lineMap[line.id] = line;
        }

        const critical = {};
        for (const node of observation.critical_nodes) {
          if (node.type === 'hospital' && !critical.hospital) critical.hospital = node;
          if (node.type === 'telecom' && !critical.telecom) critical.telecom = node;
          if (node.type === 'water' && !critical.water) critical.water = node;
        }

        const layout = getScenarioLayout(observation);
        const busBindings = layout.busBindings;
        for (const [id, candidates] of busBindings) {
          const active = candidates.map(c => subMap[c]).find(Boolean);
          const el = document.getElementById(id);
          if (!el) continue;
          const fill = active && active.energized ? '#22c55e' : '#0ea5e9';
          el.setAttribute('fill', fill);
        }

        const lineBindings = layout.lineBindings;
        for (const [id, candidates] of lineBindings) {
          const line = candidates.map(c => lineMap[c]).find(Boolean);
          const el = document.getElementById(id);
          if (!line || !el) continue;
          let color = '#64748b';
          if (line.tripped || line.damaged && !line.inspected) color = '#ef4444';
          else if (line.closed) color = '#22c55e';
          else if (line.inspected) color = '#eab308';
          el.setAttribute('stroke', color);
          el.setAttribute('stroke-dasharray', line.closed ? '' : '14 9');
        }

        const hospitalEl = document.getElementById('map-critical-hospital');
        const telecomEl = document.getElementById('map-critical-telecom');
        const waterEl = document.getElementById('map-critical-water');
        if (hospitalEl && critical.hospital) {
          hospitalEl.setAttribute('stroke', statusColor(critical.hospital.powered, critical.hospital.backup_minutes_remaining <= 15 ? 'danger' : 'warn'));
        }
        if (telecomEl && critical.telecom) {
          telecomEl.setAttribute('stroke', statusColor(critical.telecom.powered, critical.telecom.backup_minutes_remaining <= 15 ? 'danger' : 'warn'));
        }
        if (waterEl && critical.water) {
          waterEl.setAttribute('stroke', statusColor(critical.water.powered, critical.water.backup_minutes_remaining <= 15 ? 'danger' : 'warn'));
        }

        const timers = [
          ['map-timer-hospital', critical.hospital],
          ['map-timer-telecom', critical.telecom],
          ['map-timer-water', critical.water]
        ];
        for (const [id, node] of timers) {
          const el = document.getElementById(id);
          if (!el || !node) continue;
          el.textContent = node.powered ? 'grid' : `${node.backup_minutes_remaining} min`;
          el.setAttribute('fill', node.powered ? '#86efac' : (node.backup_minutes_remaining <= 15 ? '#fca5a5' : '#fde047'));
        }

        const textBindings = [
          ['map-bus-label-south', layout.busLabels[0]],
          ['map-bus-label-core', layout.busLabels[1]],
          ['map-bus-label-medical', layout.busLabels[2]],
          ['map-bus-label-east', layout.busLabels[3]],
          ['map-line-label-a', layout.lineLabels[0]],
          ['map-line-label-b', layout.lineLabels[1]],
          ['map-line-label-c', layout.lineLabels[2]],
          ['map-label-hospital', layout.criticalLabels[0]],
          ['map-label-telecom', layout.criticalLabels[1]],
          ['map-label-water', layout.criticalLabels[2]]
        ];
        for (const [id, label] of textBindings) {
          const el = document.getElementById(id);
          if (el) el.textContent = label;
        }

        const freqBanner = document.getElementById('map-banner-frequency');
        const reserveBanner = document.getElementById('map-banner-reserve');
        const riskBanner = document.getElementById('map-banner-risk');
        if (freqBanner) {
          freqBanner.textContent = `Freq ${observation.frequency_hz.toFixed(2)} Hz`;
          freqBanner.setAttribute('fill', observation.frequency_hz < 59.5 ? '#fca5a5' : observation.frequency_hz < 59.7 ? '#fde047' : '#86efac');
        }
        if (reserveBanner) {
          reserveBanner.textContent = `Reserve ${observation.reserve_margin_mw} MW`;
          reserveBanner.setAttribute('fill', observation.reserve_margin_mw < 6 ? '#fca5a5' : observation.reserve_margin_mw < 12 ? '#fde047' : '#86efac');
        }
        if (riskBanner) {
          let risk = 'Low risk';
          let color = '#86efac';
          if (observation.done && observation.reward_breakdown.catastrophe_penalty > 0) {
            risk = 'Collapse triggered';
            color = '#fca5a5';
          } else if (observation.frequency_hz < 59.5 || observation.reserve_margin_mw < 6) {
            risk = 'Collapse risk high';
            color = '#fca5a5';
          } else if (observation.warnings.some(item => item.toLowerCase().includes('backup below 15'))) {
            risk = 'Critical timers low';
            color = '#fde047';
          }
          riskBanner.textContent = risk;
          riskBanner.setAttribute('fill', color);
        }
      }

      function updateOverlays(observation) {
        const frequencyEl = document.getElementById('overlay-frequency');
        const reserveEl = document.getElementById('overlay-reserve');
        const riskEl = document.getElementById('overlay-risk');

        const setBanner = (el, text, kind) => {
          if (!el) return;
          el.textContent = text;
          el.className = `overlay-banner ${kind}`;
        };

        const freqKind = observation.frequency_hz < 59.5 ? 'danger' : observation.frequency_hz < 59.7 ? 'warn' : 'safe';
        setBanner(frequencyEl, `Grid frequency: ${observation.frequency_hz.toFixed(2)} Hz`, freqKind);

        const reserveKind = observation.reserve_margin_mw < 6 ? 'danger' : observation.reserve_margin_mw < 12 ? 'warn' : 'safe';
        setBanner(reserveEl, `Reserve margin: ${observation.reserve_margin_mw} MW`, reserveKind);

        let riskText = 'No immediate second-collapse risk.';
        let riskKind = 'safe';
        if (observation.reward_breakdown.catastrophe_penalty > 0) {
          riskText = 'Second-collapse conditions triggered.';
          riskKind = 'danger';
        } else if (observation.frequency_hz < 59.5 || observation.reserve_margin_mw < 6) {
          riskText = 'System is one bad action away from another collapse.';
          riskKind = 'danger';
        } else if (observation.warnings.some(item => item.toLowerCase().includes('backup below 15'))) {
          riskText = 'Critical backups are low. Prioritize hospitals and core services.';
          riskKind = 'warn';
        }
        setBanner(riskEl, riskText, riskKind);
      }

      function getScenarioLayout(observation) {
        if (observation.task_id === 'local_blackstart') {
          return {
            busBindings: [
              ['map-bus-south', ['sub_north', 'sub_west', 'sub_south']],
              ['map-bus-core', ['sub_civic', 'sub_medical_w', 'sub_dispatch']],
              ['map-bus-medical', ['gen_bus_n', 'gen_bus_w', 'gen_bus_s']],
              ['map-bus-east', ['sub_north', 'sub_west', 'sub_south']]
            ],
            lineBindings: [
              ['map-line-south-core', ['line_n_1', 'line_w_1', 'line_s_easy_1']],
              ['map-line-south-medical', ['line_n_2', 'line_w_2', 'line_s_easy_2']],
              ['map-line-medical-east', ['line_n_2', 'line_w_2', 'line_s_easy_2']],
              ['map-line-core-east', ['line_n_1', 'line_w_1', 'line_s_easy_1']]
            ],
            busLabels: ['District', 'Critical', 'Blackstart', 'Local Feed'],
            lineLabels: ['feeder path', 'medical spur', 'corridor restore'],
            criticalLabels: ['Hospital', 'Telecom', 'Water']
          };
        }
        if (observation.task_id === 'island_rejoin') {
          return {
            busBindings: [
              ['map-bus-south', ['sub_east', 'sub_harbor', 'sub_north_i']],
              ['map-bus-core', ['sub_civic', 'sub_core', 'sub_river']],
              ['map-bus-medical', ['sub_water', 'sub_telecom_r', 'sub_core']],
              ['map-bus-east', ['sub_core', 'sub_river', 'sub_telecom_r']]
            ],
            lineBindings: [
              ['map-line-south-core', ['line_tie_1', 'line_tie_hc', 'line_tie_nr']],
              ['map-line-south-medical', ['line_e_1', 'line_h_1', 'line_nr_1']],
              ['map-line-medical-east', ['line_c_2', 'line_rr_2', 'line_rr_1']],
              ['map-line-core-east', ['line_c_1', 'line_core_1', 'line_rr_1']]
            ],
            busLabels: ['Island A', 'Island B', 'Critical Spur', 'Sync Path'],
            lineLabels: ['inspection first', 'island feeder', 'rejoin corridor'],
            criticalLabels: ['Hospital', 'Telecom', 'Water']
          };
        }
        return {
          busBindings: [
            ['map-bus-south', ['sub_south', 'sub_north', 'sub_harbor_h']],
            ['map-bus-core', ['sub_core', 'sub_core_h', 'sub_core']],
            ['map-bus-medical', ['sub_medical', 'sub_medical_h', 'sub_water']],
            ['map-bus-east', ['sub_east', 'sub_corridor_h', 'sub_water_h']]
          ],
          lineBindings: [
            ['map-line-south-core', ['line_tie_city', 'line_tie_nc', 'line_tie_hstorm_1']],
            ['map-line-south-medical', ['line_s_1', 'line_n_1', 'line_hh_1']],
            ['map-line-medical-east', ['line_core_2', 'line_c_3', 'line_ch_3']],
            ['map-line-core-east', ['line_tie_east', 'line_tie_hstorm_2', 'line_ch_1']]
          ],
          busLabels: ['Generation', 'Core', 'Critical', 'Outer Grid'],
          lineLabels: ['damaged tie-line', 'feeder recovery', 'unsafe corridor'],
          criticalLabels: ['Hospital', 'Telecom', 'Water']
        };
      }

      function renderObservation(observation) {
        currentObservation = observation;
        setText('incident-id', observation.incident_id);
        setText('scenario-title', observation.title);
        setText('scenario-objective', observation.objective);
        setText('metric-step', `${observation.step}/${observation.step + observation.steps_remaining}`);
        setText('metric-frequency', observation.frequency_hz.toFixed(2));
        setText('metric-reserve', `${observation.reserve_margin_mw} MW`);
        setText('metric-score', observation.reward_breakdown.current_score.toFixed(2));
        setText('metric-gen', `${observation.available_generation_mw} MW`);
        setText('metric-load', `${observation.served_load_mw} MW`);
        setText('metric-islands', observation.unstable_islands);
        setText('metric-done', observation.done ? 'yes' : 'no');
        setText('last-result', observation.last_action_result || 'Scenario reset.');
        renderCriticalNodes(observation.critical_nodes);
        renderAssets(observation);
        renderWarnings(observation.warnings);
        updateMap(observation);
        updateOverlays(observation);
        renderRewardBreakdown(observation.reward_breakdown);
      }

      function renderRewardBreakdown(breakdown) {
        const container = document.getElementById('reward-decomposition');
        const items = [
          { label: 'Critical Restore', val: breakdown.critical_restore_reward, type: 'plus' },
          { label: 'Load Restore', val: breakdown.load_restore_reward, type: 'plus' },
          { label: 'Stability', val: breakdown.stability_reward, type: 'plus' },
          { label: 'Inspection', val: breakdown.inspection_reward, type: 'plus' },
          { label: 'Communication', val: breakdown.communication_reward, type: 'plus' },
          { label: 'Action Penalty', val: breakdown.action_penalty, type: 'minus' },
          { label: 'Collapse Penalty', val: breakdown.catastrophe_penalty, type: 'minus' }
        ];
        container.innerHTML = items.map(item => `
          <div class="reward-item ${item.type}">
            <div class="small">${item.label}</div>
            <span class="val">${item.val > 0 ? '+' : ''}${item.val.toFixed(2)}</span>
          </div>
        `).join('');
      }

      async function resetScenario() {
        stopAutoplay();
        document.getElementById('rollout-log').textContent = '';
        const payload = {
          task_id: document.getElementById('task-select').value,
          seed: Number(document.getElementById('seed-input').value)
        };
        const response = await fetch('/reset', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        const observation = data.observation;
        appendLog(`[RESET] ${observation.task_id} seed=${payload.seed}`);
        renderObservation(observation);
      }

      async function submitAction(action) {
        const response = await fetch('/step', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(action)
        });
        const data = await response.json();
        const observation = data.observation;
        appendLog(`[STEP] ${JSON.stringify(action)} -> reward=${data.reward.toFixed(2)} score=${observation.reward_breakdown.current_score.toFixed(2)}`);
        renderObservation(observation);
        return observation;
      }

      async function suggestAction() {
        const response = await fetch('/baseline/next');
        const payload = await response.json();
        document.getElementById('action-json').value = JSON.stringify(payload.action || {}, null, 2);
      }

      async function heuristicStep() {
        const response = await fetch('/baseline/step', { method: 'POST' });
        const payload = await response.json();
        const observation = payload.observation;
        if (payload.action) {
          appendLog(`[HEURISTIC] ${JSON.stringify(payload.action)} -> score=${observation.reward_breakdown.current_score.toFixed(2)}`);
        } else {
          appendLog('[HEURISTIC] no further action');
        }
        renderObservation(observation);
        return observation;
      }

      async function autoplayHeuristic() {
        if (!currentObservation) {
          await resetScenario();
        }
        stopAutoplay();
        autoplayHandle = setInterval(async () => {
          if (!currentObservation || currentObservation.done) {
            stopAutoplay();
            return;
          }
          const obs = await heuristicStep();
          if (obs.done) {
            stopAutoplay();
          }
        }, 600);
      }

      function stopAutoplay() {
        if (autoplayHandle) {
          clearInterval(autoplayHandle);
          autoplayHandle = null;
        }
      }

      function renderCompareCard(prefix, payload) {
        const summary = document.getElementById(`compare-${prefix}-summary`);
        const log = document.getElementById(`compare-${prefix}-log`);
        summary.innerHTML = `
          score <strong>${payload.score.toFixed(2)}</strong> |
          steps <strong>${payload.steps}</strong> |
          resolved <strong>${payload.resolved ? 'yes' : 'no'}</strong> |
          catastrophe <strong>${payload.catastrophe_triggered ? 'yes' : 'no'}</strong> |
          hospital failures <strong>${payload.hospital_failures}</strong>
        `;
        log.textContent = payload.log.map(
          item => `[${item.step}] ${item.action.action_type} -> reward=${item.reward.toFixed(2)} score=${item.score.toFixed(2)}`
        ).join('\\n');
      }

      async function runComparison() {
        const payload = {
          task_id: document.getElementById('task-select').value,
          seed: Number(document.getElementById('seed-input').value)
        };
        const response = await fetch('/compare', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await response.json();
        renderCompareCard('greedy', result.greedy);
        renderCompareCard('heuristic', result.heuristic);
        appendLog(`[COMPARE] greedy=${result.greedy.score.toFixed(2)} heuristic=${result.heuristic.score.toFixed(2)}`);
      }

      document.getElementById('reset-btn').addEventListener('click', resetScenario);
      document.getElementById('suggest-btn').addEventListener('click', suggestAction);
      document.getElementById('heuristic-btn').addEventListener('click', heuristicStep);
      document.getElementById('auto-btn').addEventListener('click', autoplayHeuristic);
      document.getElementById('compare-btn').addEventListener('click', runComparison);
      document.getElementById('step-btn').addEventListener('click', async () => {
        stopAutoplay();
        const raw = document.getElementById('action-json').value;
        try {
          const action = JSON.parse(raw);
          await submitAction(action);
        } catch (error) {
          appendLog(`[ERROR] invalid action JSON: ${error}`);
        }
      });

      resetScenario();
    </script>
  </body>
</html>
"""
