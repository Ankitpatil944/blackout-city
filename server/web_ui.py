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
        --border: #1e293b;
        --text: #e2e8f0;
        --muted: #94a3b8;
        --accent: #f59e0b;
        --danger: #ef4444;
        --safe: #22c55e;
        --warn: #eab308;
      }
      *, *::before, *::after { box-sizing: border-box; }
      body {
        font-family: system-ui, -apple-system, "Segoe UI", Arial, sans-serif;
        margin: 0;
        padding: 1.75rem 2rem;
        background:
          radial-gradient(ellipse at top, rgba(245,158,11,0.09), transparent 40%),
          linear-gradient(180deg, #020617 0%, var(--bg) 100%);
        color: var(--text);
        min-height: 100vh;
      }
      .hero {
        display: grid;
        grid-template-columns: 1.15fr 0.85fr;
        gap: 1.25rem;
        margin-bottom: 1.25rem;
      }
      .card {
        background: linear-gradient(160deg, rgba(17,24,39,0.97), rgba(15,23,42,0.97));
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 4px 28px rgba(2,6,23,0.55), inset 0 1px 0 rgba(255,255,255,0.025);
      }
      h1, h2, h3 { margin: 0 0 0.7rem; letter-spacing: -0.01em; }
      h1 { font-size: 1.6rem; }
      h2 { font-size: 1.12rem; color: #cbd5e1; }
      h3 { font-size: 0.98rem; color: #94a3b8; }
      p { color: var(--muted); line-height: 1.6; margin: 0 0 0.5rem; }
      code { color: var(--accent); font-family: "Cascadia Code","Consolas",monospace; font-size: 0.88em; }
      ul { line-height: 1.75; margin: 0; padding-left: 1.2rem; }
      li { color: var(--muted); }
      .grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1.1rem;
      }
      .stats {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.6rem;
        margin-top: 0.85rem;
      }
      .stat {
        border: 1px solid rgba(148,163,184,0.12);
        border-radius: 10px;
        padding: 0.7rem 0.85rem;
        background: rgba(7,17,31,0.7);
        transition: border-color 0.18s;
      }
      .stat:hover { border-color: rgba(148,163,184,0.28); }
      .stat strong {
        display: block;
        font-size: 1.15rem;
        color: white;
        margin-top: 0.18rem;
        font-variant-numeric: tabular-nums;
      }
      .badge {
        display: inline-block;
        font-size: 0.74rem;
        padding: 0.16rem 0.52rem;
        border-radius: 999px;
        border: 1px solid rgba(245,158,11,0.3);
        color: var(--accent);
        margin-right: 0.4rem;
        margin-bottom: 0.5rem;
        letter-spacing: 0.04em;
      }
      .map-wrap {
        background: #030d1a;
        border-radius: 12px;
        border: 1px solid rgba(30,41,59,0.7);
        overflow: hidden;
      }
      svg { width: 100%; height: auto; display: block; }
      .legend {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-top: 0.6rem;
        color: var(--muted);
        font-size: 0.84rem;
        padding: 0 0.2rem;
      }
      .dot {
        width: 0.7rem; height: 0.7rem;
        border-radius: 999px;
        display: inline-block;
        margin-right: 0.28rem;
        vertical-align: middle;
      }
      .small { font-size: 0.87rem; color: var(--muted); }
      .controls {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        align-items: center;
      }
      button, select, input, textarea {
        background: #0b1728;
        color: var(--text);
        border: 1px solid rgba(148,163,184,0.18);
        border-radius: 8px;
        padding: 0.58rem 0.85rem;
        font: inherit;
        font-size: 0.9rem;
        outline: none;
        transition: border-color 0.14s, box-shadow 0.14s;
      }
      button:focus, select:focus, input:focus, textarea:focus {
        border-color: rgba(96,165,250,0.45);
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
      }
      button {
        cursor: pointer;
        background: linear-gradient(180deg, #2563eb, #1e40af);
        border-color: rgba(96,165,250,0.3);
        font-weight: 500;
      }
      button:hover { background: linear-gradient(180deg, #3b82f6, #2563eb); }
      button.secondary {
        background: linear-gradient(180deg, #374151, #1f2937);
        border-color: rgba(148,163,184,0.18);
      }
      button.secondary:hover { background: linear-gradient(180deg, #4b5563, #374151); }
      button.warn {
        background: linear-gradient(180deg, #b45309, #92400e);
        border-color: rgba(251,191,36,0.25);
      }
      button.warn:hover { background: linear-gradient(180deg, #d97706, #b45309); }
      textarea {
        width: 100%;
        min-height: 132px;
        resize: vertical;
        font-family: "Cascadia Code","Consolas",monospace;
        font-size: 0.87rem;
        line-height: 1.5;
      }
      .data-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }
      .list { display: grid; gap: 0.48rem; }
      .item {
        border: 1px solid rgba(148,163,184,0.1);
        border-radius: 10px;
        padding: 0.68rem 0.85rem;
        background: rgba(2,6,23,0.5);
        transition: border-color 0.14s;
      }
      .item:hover { border-color: rgba(148,163,184,0.22); }
      .item strong { color: white; }
      .item-line {
        display: flex;
        justify-content: space-between;
        gap: 0.7rem;
        flex-wrap: wrap;
        align-items: center;
      }
      .tag {
        display: inline-block;
        border-radius: 999px;
        padding: 0.12rem 0.48rem;
        font-size: 0.74rem;
        font-weight: 500;
        margin-right: 0.28rem;
        letter-spacing: 0.02em;
      }
      .tag.safe   { background: rgba(34,197,94,0.13);  color: #86efac; border: 1px solid rgba(34,197,94,0.2); }
      .tag.warn   { background: rgba(234,179,8,0.13);  color: #fde047; border: 1px solid rgba(234,179,8,0.2); }
      .tag.danger { background: rgba(239,68,68,0.13);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.2); }
      .mono { font-family: "Cascadia Code","Consolas",monospace; color: #94a3b8; font-size: 0.87em; }
      .warning-list li { color: #fcd34d; }
      .log {
        max-height: 280px;
        overflow: auto;
        font-family: "Cascadia Code","Consolas",monospace;
        font-size: 0.84rem;
        line-height: 1.55;
        white-space: pre-wrap;
        color: #94a3b8;
        padding: 0.4rem 0.2rem;
      }
      .log::-webkit-scrollbar { width: 5px; }
      .log::-webkit-scrollbar-track { background: transparent; }
      .log::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
      .footer-note { color: var(--muted); font-size: 0.84rem; margin-top: 0.5rem; line-height: 1.5; }
      .compare-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }
      .compare-card {
        border: 1px solid rgba(148,163,184,0.12);
        border-radius: 12px;
        padding: 0.9rem;
        background: rgba(2,6,23,0.38);
      }
      .objective-box {
        border: 1px solid rgba(148,163,184,0.12);
        border-radius: 12px;
        padding: 0.85rem 0.95rem;
        background: rgba(2,6,23,0.32);
        margin-bottom: 0.85rem;
      }
      .objective-box strong { color: white; }
      .overlay-banner {
        border-radius: 9px;
        padding: 0.48rem 0.7rem;
        margin-top: 0.48rem;
        font-size: 0.87rem;
        border: 1px solid rgba(148,163,184,0.12);
        background: rgba(2,6,23,0.32);
      }
      .overlay-banner.safe   { color: #86efac; border-color: rgba(34,197,94,0.28); }
      .overlay-banner.warn   { color: #fde047; border-color: rgba(234,179,8,0.28); }
      .overlay-banner.danger { color: #fca5a5; border-color: rgba(239,68,68,0.28); }
      .reward-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(128px, 1fr));
        gap: 0.5rem;
        margin-top: 0.55rem;
      }
      .reward-item {
        background: rgba(7,17,31,0.65);
        border: 1px solid rgba(148,163,184,0.09);
        border-radius: 8px;
        padding: 0.48rem;
        text-align: center;
      }
      .reward-item .val {
        display: block;
        font-weight: 700;
        font-size: 0.98rem;
        margin-top: 0.18rem;
        font-family: "Cascadia Code","Consolas",monospace;
        font-variant-numeric: tabular-nums;
      }
      .reward-item.plus .val  { color: #86efac; }
      .reward-item.minus .val { color: #fca5a5; }

      @keyframes flow        { to { stroke-dashoffset: -24; } }
      @keyframes pulse-ring  { 0%,100% { opacity: 0.3; } 50% { opacity: 0.65; } }
      @keyframes ticker-blink{ 0%,100% { opacity: 1;   } 50% { opacity: 0.55; } }

      @media (max-width: 980px) {
        .hero, .grid, .stats, .data-grid, .compare-grid { grid-template-columns: 1fr; }
        body { padding: 1rem; }
      }
    </style>
  </head>
  <body>

    <!-- ═══════════════════  HERO  ═══════════════════ -->
    <div class="hero">
      <div class="card">
        <div>
          <span class="badge">OpenEnv</span>
          <span class="badge">Wild Card</span>
          <span class="badge">Long-Horizon</span>
        </div>
        <h1>Blackstart City</h1>
        <p>An AI command team must bring a dark city back to life before hospitals exhaust backup power, telecom towers fail, water pressure collapses, public trust breaks down, and one unsafe reconnection triggers a second blackout.</p>
        <div class="stats">
          <div class="stat"><span class="small">Task Families</span><strong>3</strong></div>
          <div class="stat"><span class="small">Critical Systems</span><strong>4</strong></div>
          <div class="stat"><span class="small">Score Range</span><strong>0.01–0.99</strong></div>
          <div class="stat"><span class="small">Main Failure</span><strong>2nd Collapse</strong></div>
        </div>
      </div>
      <div class="card">
        <h2>Demo Narrative</h2>
        <ul>
          <li>Hospitals start on backup power and lose minutes every step.</li>
          <li>Telecom outages reduce visibility and destabilize recovery.</li>
          <li>Water plants create city-scale penalties if left dark.</li>
          <li>Grid, emergency, public-information, and dispatch roles must stay aligned.</li>
        </ul>
      </div>
    </div>

    <!-- ═══════════════════  CITY MAP + TASKS  ═══════════════════ -->
    <div class="grid">
      <div class="card">
        <h2>City Infrastructure Map</h2>
        <div class="map-wrap">
          <!--
            ╔══════════════════════════════════════════════════════════╗
            ║  BLACKSTART CITY — CONTROL-ROOM INFRASTRUCTURE VIEW     ║
            ║  All IDs are referenced by JavaScript below.            ║
            ╚══════════════════════════════════════════════════════════╝
            Node positions:
              South Gen  → (155, 220)
              Core bus   → (330, 115)
              Medical bus→ (330, 335)
              East bus   → (528, 232)
            Critical nodes:
              Hospital   → rect (16,  94) 102×56
              Telecom    → rect (626, 48) 118×56
              Water      → rect (626,382) 118×56
            Status banners: y=454
          -->
          <svg viewBox="0 0 760 560" aria-label="Blackstart City infrastructure map">
            <defs>
              <!-- Arrow markers for transmission lines -->
              <marker id="arr-green" viewBox="0 0 10 10" refX="8" refY="5"
                      markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M2 1L8 5L2 9" fill="none" stroke="#22c55e"
                      stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </marker>
              <marker id="arr-red" viewBox="0 0 10 10" refX="8" refY="5"
                      markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M2 1L8 5L2 9" fill="none" stroke="#ef4444"
                      stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </marker>
              <marker id="arr-amber" viewBox="0 0 10 10" refX="8" refY="5"
                      markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M2 1L8 5L2 9" fill="none" stroke="#f59e0b"
                      stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </marker>
              <!-- Glow filters -->
              <filter id="glow-sm" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="5" result="b"/>
                <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
              <!-- Scanline overlay -->
              <pattern id="scan" width="1" height="4" patternUnits="userSpaceOnUse">
                <rect width="1" height="2" fill="rgba(0,0,0,0.06)"/>
              </pattern>
            </defs>

            <!-- ══ BASE ════════════════════════════════════════════════ -->
            <rect width="760" height="560" fill="#030c18"/>

            <!-- ══ STREET GRID ════════════════════════════════════════ -->
            <line x1="0"   y1="200" x2="760" y2="200" stroke="#0a1d2f" stroke-width="8"/>
            <line x1="0"   y1="390" x2="760" y2="390" stroke="#0a1d2f" stroke-width="8"/>
            <line x1="270" y1="0"   x2="270" y2="560" stroke="#0a1d2f" stroke-width="8"/>
            <line x1="490" y1="0"   x2="490" y2="560" stroke="#0a1d2f" stroke-width="8"/>
            <line x1="0"   y1="100" x2="760" y2="100" stroke="#060f1c" stroke-width="2"/>
            <line x1="0"   y1="295" x2="760" y2="295" stroke="#060f1c" stroke-width="2"/>
            <line x1="0"   y1="490" x2="760" y2="490" stroke="#060f1c" stroke-width="2"/>
            <line x1="152" y1="0"   x2="152" y2="560" stroke="#060f1c" stroke-width="2"/>
            <line x1="378" y1="0"   x2="378" y2="560" stroke="#060f1c" stroke-width="2"/>
            <line x1="626" y1="0"   x2="626" y2="560" stroke="#060f1c" stroke-width="2"/>

            <!-- ══ DISTRICT ZONES ══════════════════════════════════════ -->
            <!-- Generation / West -->
            <rect x="16" y="148" width="224" height="228" rx="10"
                  fill="rgba(34,197,94,0.03)" stroke="rgba(34,197,94,0.22)"
                  stroke-width="1" stroke-dasharray="10 6"/>
            <text x="28" y="168" fill="rgba(34,197,94,0.45)"
                  font-size="10" font-family="monospace" letter-spacing="2.5">GENERATION</text>
            <!-- Core / North-Center -->
            <rect x="248" y="28" width="216" height="212" rx="10"
                  fill="rgba(14,165,233,0.03)" stroke="rgba(14,165,233,0.22)"
                  stroke-width="1" stroke-dasharray="10 6"/>
            <text x="260" y="48" fill="rgba(14,165,233,0.45)"
                  font-size="10" font-family="monospace" letter-spacing="2.5">CORE DISTRICT</text>
            <!-- Medical / South-Center -->
            <rect x="248" y="308" width="216" height="208" rx="10"
                  fill="rgba(239,68,68,0.03)" stroke="rgba(239,68,68,0.22)"
                  stroke-width="1" stroke-dasharray="10 6"/>
            <text x="260" y="328" fill="rgba(239,68,68,0.45)"
                  font-size="10" font-family="monospace" letter-spacing="2.5">MEDICAL</text>
            <!-- East Grid — tall zone that contains hospital/telecom/water -->
            <rect x="472" y="56" width="282" height="400" rx="10"
                  fill="rgba(245,158,11,0.03)" stroke="rgba(245,158,11,0.22)"
                  stroke-width="1" stroke-dasharray="10 6"/>
            <text x="484" y="76" fill="rgba(245,158,11,0.45)"
                  font-size="10" font-family="monospace" letter-spacing="2.5">EAST GRID</text>

            <!-- ══ CITY BUILDING BLOCKS (texture) ═════════════════════ -->
            <rect x="30"  y="180" width="22" height="15" rx="2" fill="#060f1c"/>
            <rect x="58"  y="177" width="16" height="19" rx="2" fill="#060f1c"/>
            <rect x="80"  y="183" width="24" height="13" rx="2" fill="#060f1c"/>
            <rect x="30"  y="322" width="18" height="14" rx="2" fill="#060f1c"/>
            <rect x="54"  y="318" width="24" height="17" rx="2" fill="#060f1c"/>
            <rect x="82"  y="324" width="16" height="13" rx="2" fill="#060f1c"/>
            <rect x="264" y="68"  width="23" height="17" rx="2" fill="#050e1b"/>
            <rect x="293" y="65"  width="15" height="21" rx="2" fill="#050e1b"/>
            <rect x="316" y="70"  width="19" height="15" rx="2" fill="#050e1b"/>
            <rect x="396" y="68"  width="17" height="14" rx="2" fill="#050e1b"/>
            <rect x="418" y="66"  width="13" height="18" rx="2" fill="#050e1b"/>
            <rect x="264" y="348" width="20" height="14" rx="2" fill="#08090e"/>
            <rect x="290" y="344" width="24" height="17" rx="2" fill="#08090e"/>
            <rect x="320" y="350" width="16" height="13" rx="2" fill="#08090e"/>
            <rect x="506" y="192" width="18" height="15" rx="2" fill="#06100a"/>
            <rect x="530" y="189" width="14" height="18" rx="2" fill="#06100a"/>
            <rect x="612" y="228" width="20" height="15" rx="2" fill="#06100a"/>
            <rect x="638" y="225" width="15" height="19" rx="2" fill="#06100a"/>
            <rect x="608" y="342" width="20" height="14" rx="2" fill="#06100a"/>
            <rect x="634" y="339" width="15" height="17" rx="2" fill="#06100a"/>

            <!-- ══ TRANSMISSION CORRIDOR SHADOWS ══════════════════════ -->
            <line x1="130" y1="272" x2="356" y2="138" stroke="#0a1828" stroke-width="18" stroke-linecap="round"/>
            <line x1="130" y1="272" x2="356" y2="390" stroke="#0a1828" stroke-width="18" stroke-linecap="round"/>
            <line x1="356" y1="390" x2="556" y2="262" stroke="#0a1828" stroke-width="18" stroke-linecap="round"/>
            <line x1="356" y1="138" x2="556" y2="262" stroke="#0a1828" stroke-width="18" stroke-linecap="round"/>

            <!-- ══ MAIN TRANSMISSION LINES — JS controls stroke + dasharray ══ -->
            <line id="map-line-south-core"    x1="130" y1="272" x2="356" y2="138"
                  stroke="#ef4444" stroke-width="3" stroke-dasharray="12 8" stroke-linecap="round"
                  marker-end="url(#arr-red)"/>
            <line id="map-line-south-medical" x1="130" y1="272" x2="356" y2="390"
                  stroke="#22c55e" stroke-width="3" stroke-linecap="round"
                  marker-end="url(#arr-green)"/>
            <line id="map-line-medical-east"  x1="356" y1="390" x2="556" y2="262"
                  stroke="#f59e0b" stroke-width="3" stroke-dasharray="8 6" stroke-linecap="round"
                  marker-end="url(#arr-amber)"/>
            <line id="map-line-core-east"     x1="356" y1="138" x2="556" y2="262"
                  stroke="#ef4444" stroke-width="3" stroke-dasharray="12 8" stroke-linecap="round"
                  marker-end="url(#arr-red)"/>
            <!-- Animated power-flow overlay on energized line -->
            <line x1="130" y1="272" x2="356" y2="390"
                  stroke="rgba(34,197,94,0.45)" stroke-width="2"
                  stroke-dasharray="6 14"
                  style="animation:flow 0.95s linear infinite"/>

            <!-- ══ LINE LABEL PILLS ═══════════════════════════════════ -->
            <!-- south-core label -->
            <rect x="196" y="188" width="100" height="22" rx="11"
                  fill="#3f0f0f" stroke="rgba(239,68,68,0.35)" stroke-width="1"/>
            <text id="map-line-label-a" x="246" y="203" text-anchor="middle"
                  fill="#fca5a5" font-size="11" font-family="monospace">damaged tie-line</text>
            <!-- south-medical label -->
            <rect x="182" y="314" width="96" height="22" rx="11"
                  fill="#052a0f" stroke="rgba(34,197,94,0.35)" stroke-width="1"/>
            <text id="map-line-label-c" x="230" y="329" text-anchor="middle"
                  fill="#86efac" font-size="11" font-family="monospace">energized path</text>
            <!-- core-east label -->
            <rect x="442" y="186" width="80" height="22" rx="11"
                  fill="#3f0f0f" stroke="rgba(239,68,68,0.35)" stroke-width="1"/>
            <text id="map-line-label-b" x="482" y="201" text-anchor="middle"
                  fill="#fca5a5" font-size="11" font-family="monospace">unsafe corridor</text>

            <!-- ══ PYLON ICONS ══════════════════════════════════════════ -->
            <!-- south-medical midpoint ~(243,331) -->
            <g transform="translate(243,331)">
              <line x1="0" y1="9" x2="0" y2="-7" stroke="#162c42" stroke-width="2.5"/>
              <line x1="-8" y1="-1" x2="8" y2="-1" stroke="#162c42" stroke-width="1.5"/>
              <line x1="-5" y1="3" x2="5" y2="3" stroke="#162c42" stroke-width="1"/>
              <circle cy="9" r="2.5" fill="#162c42"/>
            </g>
            <!-- core-east midpoint ~(456,200) -->
            <g transform="translate(456,200)">
              <line x1="0" y1="9" x2="0" y2="-7" stroke="#162c42" stroke-width="2.5"/>
              <line x1="-8" y1="-1" x2="8" y2="-1" stroke="#162c42" stroke-width="1.5"/>
              <line x1="-5" y1="3" x2="5" y2="3" stroke="#162c42" stroke-width="1"/>
              <circle cy="9" r="2.5" fill="#162c42"/>
            </g>
            <!-- medical-east midpoint ~(456,326) -->
            <g transform="translate(456,326)">
              <line x1="0" y1="9" x2="0" y2="-7" stroke="#162c42" stroke-width="2.5"/>
              <line x1="-8" y1="-1" x2="8" y2="-1" stroke="#162c42" stroke-width="1.5"/>
              <line x1="-5" y1="3" x2="5" y2="3" stroke="#162c42" stroke-width="1"/>
              <circle cy="9" r="2.5" fill="#162c42"/>
            </g>

            <!-- ══ EAST SUB → CRITICAL NODE CONNECTORS ════════════════ -->
            <!-- East → Hospital (top-right) -->
            <line x1="558" y1="238" x2="594" y2="134"
                  stroke="#374151" stroke-width="1.5" stroke-dasharray="5 5"/>
            <!-- East → Telecom (middle-right) -->
            <line x1="576" y1="250" x2="634" y2="198"
                  stroke="#374151" stroke-width="1.5" stroke-dasharray="5 5"/>
            <!-- East → Water (bottom-right) -->
            <line x1="578" y1="280" x2="636" y2="402"
                  stroke="#374151" stroke-width="1.5" stroke-dasharray="5 5"/>

            <!-- ══ CRITICAL NODE: HOSPITAL ══════════════════════════════ -->
            <rect id="map-critical-hospital" x="534" y="82" width="122" height="54" rx="10"
                  fill="#450a0a" stroke="#ef4444" stroke-width="2"/>
            <!-- Red cross icon -->
            <rect x="556" y="92"  width="16" height="5"  rx="1" fill="#ef4444" opacity="0.8"/>
            <rect x="561" y="87"  width="6"  height="15" rx="1" fill="#ef4444" opacity="0.8"/>
            <text id="map-label-hospital" x="618" y="107" text-anchor="middle"
                  fill="#fecaca" font-size="13" font-weight="600">Hospital</text>
            <text id="map-timer-hospital" x="618" y="125" text-anchor="middle"
                  fill="#fca5a5" font-size="12" font-weight="700"
                  style="animation:ticker-blink 2s ease-in-out infinite">24 min</text>

            <!-- ══ CRITICAL NODE: TELECOM ════════════════════════════════ -->
            <rect id="map-critical-telecom" x="634" y="178" width="118" height="54" rx="10"
                  fill="#3a1f00" stroke="#eab308" stroke-width="2"/>
            <!-- Antenna icon -->
            <line x1="654" y1="188" x2="654" y2="204" stroke="#f59e0b" stroke-width="2.5"/>
            <line x1="646" y1="194" x2="662" y2="194" stroke="#f59e0b" stroke-width="2"/>
            <line x1="644" y1="190" x2="664" y2="190" stroke="#f59e0b" stroke-width="1" opacity="0.5"/>
            <circle cx="654" cy="188" r="2.5" fill="#f59e0b" opacity="0.7"/>
            <text id="map-label-telecom" x="706" y="201" text-anchor="middle"
                  fill="#fef3c7" font-size="13" font-weight="600">Telecom</text>
            <text id="map-timer-telecom" x="706" y="220" text-anchor="middle"
                  fill="#fde047" font-size="11" font-family="monospace">15 min</text>

            <!-- ══ CRITICAL NODE: WATER ══════════════════════════════════ -->
            <rect id="map-critical-water" x="634" y="382" width="118" height="54" rx="10"
                  fill="#0f172a" stroke="#0ea5e9" stroke-width="2"/>
            <!-- Water droplet icon -->
            <path d="M654,392 Q658,386 662,392 Q666,398 662,404 Q658,408 654,404 Q650,398 654,392 Z"
                  fill="#38bdf8" opacity="0.65"/>
            <text id="map-label-water" x="706" y="406" text-anchor="middle"
                  fill="#bae6fd" font-size="13" font-weight="600">Water Plant</text>
            <text id="map-timer-water" x="706" y="424" text-anchor="middle"
                  fill="#7dd3fc" font-size="11" font-family="monospace">22 min</text>

            <!-- ══ NODE GLOW HALOS ══════════════════════════════════════ -->
            <!-- South Gen pulse ring -->
            <circle cx="130" cy="272" r="52"
                    fill="none" stroke="rgba(34,197,94,0.10)" stroke-width="22"/>
            <circle cx="130" cy="272" r="38"
                    fill="none" stroke="rgba(34,197,94,0.14)" stroke-width="8"/>
            <!-- East Sub warning halo -->
            <circle cx="556" cy="262" r="40"
                    fill="none" stroke="rgba(245,158,11,0.11)" stroke-width="18"/>
            <!-- Hospital critical blink -->
            <circle cx="595" cy="109" r="38"
                    fill="none" stroke="rgba(239,68,68,0.13)" stroke-width="12"
                    style="animation:pulse-ring 2s ease-in-out infinite"/>

            <!-- ══ BUS NODES — JS controls fill ════════════════════════ -->

            <!-- South Gen — blackstart generator -->
            <circle id="map-bus-south" cx="130" cy="272" r="30"
                    fill="#166534" filter="url(#glow-sm)"/>
            <path d="M136,258 L124,276 L132,276 L126,288 L141,267 L133,267 Z"
                  fill="#052e16" opacity="0.88"/>
            <text id="map-bus-label-south" x="130" y="315" text-anchor="middle"
                  fill="#86efac" font-size="12" font-weight="700">South Gen</text>
            <text x="130" y="329" text-anchor="middle"
                  fill="rgba(134,239,172,0.48)" font-size="10" font-family="monospace">online · blackstart</text>

            <!-- Core substation -->
            <circle id="map-bus-core" cx="356" cy="138" r="27" fill="#075985"/>
            <rect x="343" y="126" width="13" height="13" rx="2"
                  fill="none" stroke="#7dd3fc" stroke-width="1.5"/>
            <rect x="359" y="126" width="13" height="13" rx="2"
                  fill="none" stroke="#7dd3fc" stroke-width="1.5"/>
            <line x1="356" y1="126" x2="356" y2="139" stroke="#7dd3fc" stroke-width="1" opacity="0.5"/>
            <text id="map-bus-label-core" x="356" y="180" text-anchor="middle"
                  fill="#7dd3fc" font-size="12" font-weight="700">Core</text>
            <text x="356" y="194" text-anchor="middle"
                  fill="rgba(125,211,252,0.48)" font-size="10" font-family="monospace">substation · bus A</text>

            <!-- Medical substation -->
            <circle id="map-bus-medical" cx="356" cy="392" r="27" fill="#075985"/>
            <rect x="343" y="380" width="13" height="13" rx="2"
                  fill="none" stroke="#7dd3fc" stroke-width="1.5"/>
            <rect x="359" y="380" width="13" height="13" rx="2"
                  fill="none" stroke="#7dd3fc" stroke-width="1.5"/>
            <line x1="356" y1="380" x2="356" y2="393" stroke="#7dd3fc" stroke-width="1" opacity="0.5"/>
            <text id="map-bus-label-medical" x="356" y="434" text-anchor="middle"
                  fill="#7dd3fc" font-size="12" font-weight="700">Medical</text>
            <text x="356" y="448" text-anchor="middle"
                  fill="rgba(125,211,252,0.48)" font-size="10" font-family="monospace">substation · bus B</text>

            <!-- East substation -->
            <circle id="map-bus-east" cx="556" cy="262" r="28" fill="#92400e"/>
            <rect x="545" y="251" width="14" height="14" rx="2"
                  fill="none" stroke="#fde047" stroke-width="1.5"/>
            <line x1="552" y1="251" x2="552" y2="265" stroke="#fde047" stroke-width="1" opacity="0.5"/>
            <text id="map-bus-label-east" x="556" y="305" text-anchor="middle"
                  fill="#fcd34d" font-size="12" font-weight="700">East Sub</text>
            <text x="556" y="319" text-anchor="middle"
                  fill="rgba(252,211,77,0.48)" font-size="10" font-family="monospace">backup power</text>

            <!-- ══ ACTION SEQUENCE PANEL (bottom-left) ═════════════════ -->
            <rect x="16" y="460" width="218" height="84" rx="10"
                  fill="#040e1c" stroke="#1a2e42" stroke-width="1"/>
            <text x="30" y="478" fill="#f59e0b"
                  font-size="11" font-weight="700" font-family="monospace" letter-spacing="1">ACTION SEQUENCE</text>
            <text x="30" y="494" fill="#475569" font-size="11" font-family="monospace">1) start_generator</text>
            <text x="30" y="508" fill="#475569" font-size="11" font-family="monospace">2) energize_substation</text>
            <text x="30" y="522" fill="#475569" font-size="11" font-family="monospace">3) inspect_line -&gt; restore_critical</text>
            <text x="30" y="536" fill="#475569" font-size="11" font-family="monospace">4) restore_zone + publish_status</text>

            <!-- ══ STATUS BANNERS (bottom, right of action panel) ══════ -->
            <rect x="248" y="524" width="152" height="28" rx="8"
                  fill="#040e1c" stroke="#1a2e42" stroke-width="1"/>
            <text x="258" y="535" fill="#334155" font-size="10" font-family="monospace">⚡ FREQUENCY</text>
            <text id="map-banner-frequency" x="258" y="549"
                  fill="#86efac" font-size="12" font-family="monospace" font-weight="600">Frequency stable</text>

            <rect x="412" y="524" width="160" height="28" rx="8"
                  fill="#040e1c" stroke="#1a2e42" stroke-width="1"/>
            <text x="422" y="535" fill="#334155" font-size="10" font-family="monospace">◈ RESERVE</text>
            <text id="map-banner-reserve" x="422" y="549"
                  fill="#86efac" font-size="12" font-family="monospace" font-weight="600">Reserve healthy</text>

            <rect x="584" y="524" width="164" height="28" rx="8"
                  fill="#040e1c" stroke="#1a2e42" stroke-width="1"/>
            <text x="594" y="535" fill="#334155" font-size="10" font-family="monospace">▲ RISK</text>
            <text id="map-banner-risk" x="594" y="549"
                  fill="#86efac" font-size="12" font-family="monospace" font-weight="600">No collapse risk</text>

            <!-- ══ HUD TITLE BAR ════════════════════════════════════════ -->
            <rect x="10" y="10" width="196" height="30" rx="6"
                  fill="rgba(4,14,28,0.92)" stroke="#1a2e42" stroke-width="1"/>
            <text x="22" y="30" fill="#f59e0b"
                  font-size="13" font-weight="700" font-family="monospace" letter-spacing="1">BLACKSTART CITY</text>
            <rect x="216" y="12" width="124" height="26" rx="6"
                  fill="rgba(4,14,28,0.82)" stroke="#1a2e42" stroke-width="1"/>
            <text x="226" y="29" fill="#2d4258"
                  font-size="10" font-family="monospace" letter-spacing="1">CTRL-ROOM VIEW</text>

            <!-- Scanline overlay -->
            <rect width="760" height="560" fill="url(#scan)" opacity="0.6"/>
          </svg>
        </div>
        <div class="legend">
          <span><span class="dot" style="background:#22c55e"></span>online / energized</span>
          <span><span class="dot" style="background:#0ea5e9"></span>substation / bus</span>
          <span><span class="dot" style="background:#f59e0b"></span>on backup power</span>
          <span><span class="dot" style="background:#ef4444"></span>damaged / critical</span>
          <span><span class="dot" style="background:#475569"></span>offline / open</span>
          <span><span class="dot" style="background:#f59e0b; border-radius:2px;"></span>inspected / pending</span>
        </div>
      </div>

      <div class="card">
        <h2>Primary Tasks</h2>
        <ul>
          <li><code>local_blackstart</code>: restore one district hospital and a telecom node before backup expires</li>
          <li><code>island_rejoin</code>: inspect a hidden-damage tie-line and safely reconnect islands</li>
          <li><code>city_cascade_recovery</code>: restore city-scale critical services while avoiding a second collapse</li>
        </ul>
        <h3 style="margin-top:1rem;">Command Roles</h3>
        <ul>
          <li><code>grid_operator</code>: energizes feeders and keeps the grid stable</li>
          <li><code>emergency_coordinator</code>: triages hospitals, telecom, water, and emergency load</li>
          <li><code>public_information_officer</code>: preserves public trust with truthful updates</li>
          <li><code>resource_dispatcher</code>: allocates scarce repair crews and support units</li>
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

    <!-- ═══════════════════  INTERACTIVE ROLLOUT  ═══════════════════ -->
    <div class="card" style="margin-top:1.1rem;">
      <h2>Interactive Rollout</h2>
      <div class="controls" style="margin-bottom:0.85rem;">
        <label>Task
          <select id="task-select">
            <option value="local_blackstart">local_blackstart (easy)</option>
            <option value="island_rejoin">island_rejoin (medium)</option>
            <option value="city_cascade_recovery">city_cascade_recovery (hard)</option>
            <option value="mega_cascade">mega_cascade (extreme)</option>
          </select>
        </label>
        <label>Seed <input id="seed-input" type="number" value="0" min="0" style="width:88px"></label>
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
          <div class="stats" style="grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top:0.7rem;">
            <div class="stat"><span class="small">Generation</span><strong id="metric-gen">-</strong></div>
            <div class="stat"><span class="small">Served Load</span><strong id="metric-load">-</strong></div>
            <div class="stat"><span class="small">Unstable Islands</span><strong id="metric-islands">-</strong></div>
            <div class="stat"><span class="small">Done</span><strong id="metric-done">-</strong></div>
          </div>
          <div class="footer-note" id="last-result">No rollout yet.</div>
          <div id="overlay-frequency" class="overlay-banner safe">Grid frequency stable.</div>
          <div id="overlay-reserve"   class="overlay-banner safe">Reserve margin healthy.</div>
          <div id="overlay-risk"      class="overlay-banner safe">No immediate second-collapse risk.</div>

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

    <!-- ═══════════════════  COMMAND CENTER  ═══════════════════ -->
    <div class="grid" style="margin-top:1.1rem;">
      <div class="card">
        <h2>Command Center</h2>
        <div class="stats">
          <div class="stat"><span class="small">Public Trust</span><strong id="metric-trust">-</strong></div>
          <div class="stat"><span class="small">Coordination</span><strong id="metric-coordination">-</strong></div>
          <div class="stat"><span class="small">Phase</span><strong id="metric-phase">-</strong></div>
          <div class="stat"><span class="small">Dispatch Pressure</span><strong id="metric-dispatch">-</strong></div>
        </div>
        <div id="resource-list" class="list" style="margin-top:0.9rem;"></div>
      </div>

      <div class="card">
        <h2>Role Recommendations</h2>
        <div id="role-list" class="list"></div>
        <h3 style="margin-top:1rem;">Coordination Messages</h3>
        <div id="message-list" class="list"></div>
      </div>
    </div>

    <!-- ═══════════════════  ASSETS  ═══════════════════ -->
    <div class="grid" style="margin-top:1.1rem;">
      <div class="card">
        <h2>Critical Nodes</h2>
        <div id="critical-list" class="list"></div>
      </div>

      <div class="card">
        <h2>Grid Assets</h2>
        <div id="asset-list" class="list"></div>
      </div>
    </div>

    <!-- ═══════════════════  WARNINGS + LOG  ═══════════════════ -->
    <div class="grid" style="margin-top:1.1rem;">
      <div class="card">
        <h2>Warnings</h2>
        <ul id="warning-list" class="warning-list"></ul>
      </div>

      <div class="card">
        <h2>Rollout Log</h2>
        <div id="rollout-log" class="log"></div>
      </div>
    </div>

    <!-- ═══════════════════  CONSTRAINTS + NEWS  ═══════════════════ -->
    <div class="grid" style="margin-top:1.1rem;">
      <div class="card">
        <h2>Active Constraints</h2>
        <div id="constraint-list" class="list">
          <div class="small" style="color:var(--muted);">No scenario loaded.</div>
        </div>
      </div>

      <div class="card">
        <h2>News Feed</h2>
        <div id="news-list" class="list">
          <div class="small" style="color:var(--muted);">No events yet.</div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════  POLICY COMPARISON  ═══════════════════ -->
    <div class="card" style="margin-top:1.1rem;">
      <h2>Policy Comparison</h2>
      <div class="controls" style="margin-bottom:0.85rem;">
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

    <!-- ═══════════════════  API  ═══════════════════ -->
    <div class="card" style="margin-top:1.1rem;">
      <h2>API</h2>
      <ul>
        <li><code>POST /reset</code> with <code>{ "task_id": ..., "seed": ... }</code></li>
        <li><code>POST /step</code> with a typed <code>BlackstartAction</code></li>
        <li><code>GET /state</code>, <code>/tasks</code>, <code>/grader</code>, <code>/schema</code></li>
        <li><code>GET /command/brief</code> for the multi-agent command snapshot</li>
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

      function actionSummary(action) {
        if (!action) return 'hold current coordination posture';
        const parts = [action.action_type];
        if (action.target_id) parts.push(action.target_id);
        if (action.requested_mw !== undefined && action.requested_mw !== null) parts.push(`${action.requested_mw} MW`);
        return parts.join(' · ');
      }

      function renderCommandCenter(commandCenter) {
        setText('metric-trust', `${Math.round(commandCenter.public_trust * 100)}%`);
        setText('metric-coordination', `${Math.round(commandCenter.coordination_score * 100)}%`);
        setText('metric-phase', commandCenter.command_phase);
        setText('metric-dispatch', `${Math.round(commandCenter.resource_state.dispatch_pressure * 100)}%`);

        const resources = [
          ['Repair Crews', commandCenter.resource_state.repair_crews_available, commandCenter.resource_state.repair_crews_total],
          ['Mobile Batteries', commandCenter.resource_state.mobile_battery_units_available, commandCenter.resource_state.mobile_battery_units_total],
          ['Telecom Support', commandCenter.resource_state.telecom_support_units_available, commandCenter.resource_state.telecom_support_units_total],
        ];
        const resourceContainer = document.getElementById('resource-list');
        resourceContainer.innerHTML = resources.map(item => `
          <div class="item">
            <div class="item-line">
              <strong>${item[0]}</strong>
              <span class="mono">${item[1]} / ${item[2]}</span>
            </div>
            <div class="small">Operational availability for the command network.</div>
          </div>
        `).join('');

        const roleContainer = document.getElementById('role-list');
        roleContainer.innerHTML = commandCenter.role_recommendations.map(item => `
          <div class="item">
            <div class="item-line">
              <strong>${item.role.replaceAll('_', ' ')}</strong>
              <span class="tag ${item.urgency === 'critical' ? 'danger' : item.urgency === 'high' ? 'warn' : 'safe'}">${item.urgency}</span>
            </div>
            <div class="small"><strong>${item.objective}</strong></div>
            <div class="small">${item.rationale}</div>
            <div class="small" style="margin-top:0.4rem;">Proposed action: <span class="mono">${actionSummary(item.proposed_action)}</span></div>
          </div>
        `).join('');

        const messageContainer = document.getElementById('message-list');
        messageContainer.innerHTML = commandCenter.coordination_messages.map(item => `
          <div class="item">
            <div class="item-line">
              <strong>${item.role.replaceAll('_', ' ')}</strong>
              <span class="tag ${item.urgency === 'critical' ? 'danger' : item.urgency === 'high' ? 'warn' : 'safe'}">${item.urgency}</span>
            </div>
            <div class="small">To ${item.recipient.replaceAll('_', ' ')}</div>
            <div class="small">${item.summary}</div>
          </div>
        `).join('');
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
        renderCommandCenter(observation.command_center);
        renderCriticalNodes(observation.critical_nodes);
        renderAssets(observation);
        renderWarnings(observation.warnings);
        updateMap(observation);
        updateOverlays(observation);
        renderRewardBreakdown(observation.reward_breakdown);
        renderConstraints(observation.active_constraints || []);
        renderNewsFeed(observation.news_feed || []);
      }

      function renderConstraints(constraints) {
        const container = document.getElementById('constraint-list');
        if (!constraints || constraints.length === 0) {
          container.innerHTML = '<div class="small" style="color:var(--muted);">No constraints for this scenario.</div>';
          return;
        }
        container.innerHTML = constraints.map(c => {
          const active = c.active;
          const violated = c.violated;
          const kind = violated ? 'danger' : active ? 'warn' : 'safe';
          const statusLabel = violated ? 'VIOLATED' : active ? 'active' : 'inactive';
          let detail = '';
          if (c.constraint_type === 'forbidden_target') {
            detail = `Forbidden: ${c.forbidden_action_type} on <code>${c.forbidden_target_id}</code>`;
          } else if (c.constraint_type === 'priority_order') {
            detail = `Must restore <code>${c.must_restore_first}</code> before <code>${c.before_restoring}</code>`;
          } else if (c.constraint_type === 'conditional_limit') {
            detail = `<code>${c.limit_target_id}</code> ≤ ${c.limit_mw} MW until ${c.condition_field} > ${c.condition_threshold}`;
          }
          return \`
            <div class="item">
              <div class="item-line">
                <strong>\${c.id}</strong>
                <span class="tag \${kind}">\${statusLabel}</span>
              </div>
              <div class="small">\${c.text}</div>
              <div class="small mono" style="margin-top:0.3rem;">\${detail}</div>
            </div>
          \`;
        }).join('');
      }

      function renderNewsFeed(events) {
        const container = document.getElementById('news-list');
        if (!events || events.length === 0) {
          container.innerHTML = '<div class="small" style="color:var(--muted);">No events revealed yet.</div>';
          return;
        }
        container.innerHTML = events.map(ev => {
          const kind = ev.impact_level === 'critical' ? 'danger' : ev.impact_level === 'warning' ? 'warn' : 'safe';
          const extras = [];
          if (ev.reduces_backup_node) extras.push(\`Backup drain: \${ev.reduces_backup_node} -\${ev.reduces_backup_by} min\`);
          if (ev.activates_constraint_id) extras.push(\`Activates constraint: \${ev.activates_constraint_id}\`);
          if (ev.public_trust_delta && ev.public_trust_delta !== 0) extras.push(\`Public trust: \${ev.public_trust_delta > 0 ? '+' : ''}\${ev.public_trust_delta.toFixed(2)}\`);
          return \`
            <div class="item">
              <div class="item-line">
                <strong>\${ev.headline}</strong>
                <span class="tag \${kind}">\${ev.impact_level}</span>
              </div>
              <div class="small">\${ev.detail}</div>
              \${extras.length ? \`<div class="small mono" style="margin-top:0.3rem;">\${extras.join(' | ')}</div>\` : ''}
            </div>
          \`;
        }).join('');
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
          hospital failures <strong>${payload.hospital_failures}</strong> |
          trust <strong>${Math.round(payload.public_trust * 100)}%</strong> |
          coordination <strong>${Math.round(payload.coordination_score * 100)}%</strong>
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
