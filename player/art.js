/* Theme-aware inline illustration for the course picker. */
(function () {
  const PIXEL = `
    <svg class="art art-pixel" viewBox="0 0 320 180" aria-hidden="true" focusable="false" shape-rendering="crispEdges">
      <g class="twinkle" fill="var(--amber)">
        <rect x="38" y="30" width="4" height="4"/>
        <rect x="270" y="24" width="4" height="4"/>
        <rect x="240" y="60" width="3" height="3"/>
        <rect x="60" y="70" width="3" height="3"/>
      </g>
      <rect x="48" y="148" width="224" height="4" fill="var(--border-strong)"/>
      <rect x="70" y="118" width="180" height="6" fill="var(--panel-2)" stroke="var(--border-strong)" stroke-width="2"/>
      <rect x="78" y="124" width="6" height="24" fill="var(--panel-2)"/>
      <rect x="236" y="124" width="6" height="24" fill="var(--panel-2)"/>
      <rect x="106" y="46" width="108" height="68" fill="var(--panel-inset)" stroke="var(--accent)" stroke-width="3"/>
      <rect x="114" y="54" width="92" height="52" fill="var(--code-bg)"/>
      <rect x="122" y="64" width="52" height="4" fill="var(--accent)"/>
      <rect x="122" y="74" width="70" height="4" fill="var(--accent-strong)"/>
      <rect x="122" y="84" width="40" height="4" fill="var(--accent)"/>
      <rect x="122" y="94" width="60" height="4" fill="var(--accent-strong)"/>
      <rect x="150" y="114" width="20" height="5" fill="var(--border-strong)"/>
      <rect x="132" y="119" width="56" height="4" fill="var(--border-strong)"/>
      <rect x="66" y="102" width="30" height="18" fill="var(--amber)" stroke="var(--border-strong)" stroke-width="2"/>
      <rect x="70" y="106" width="22" height="2" fill="var(--bg)"/>
      <rect x="70" y="111" width="22" height="2" fill="var(--bg)"/>
      <rect x="232" y="106" width="18" height="16" fill="var(--panel-2)" stroke="var(--border-strong)" stroke-width="2"/>
      <path d="M250 110 h5 v8 h-5" fill="none" stroke="var(--border-strong)" stroke-width="2"/>
      <rect x="198" y="94" width="18" height="16" fill="var(--panel-2)" stroke="var(--accent)" stroke-width="2"/>
      <rect x="203" y="99" width="3" height="3" fill="var(--accent)"/>
      <rect x="209" y="99" width="3" height="3" fill="var(--accent)"/>
      <rect x="205" y="88" width="4" height="6" fill="var(--border-strong)"/>
      <rect x="203" y="84" width="8" height="4" fill="var(--amber)"/>
    </svg>`;

  const STORYBOOK = `
    <svg class="art art-storybook" viewBox="0 0 320 180" aria-hidden="true" focusable="false">
      <defs>
        <radialGradient id="art-glow" cx="50%" cy="45%" r="55%">
          <stop offset="0" stop-color="var(--amber)" stop-opacity=".30"/>
          <stop offset="1" stop-color="var(--amber)" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <circle cx="160" cy="82" r="82" fill="url(#art-glow)"/>
      <g class="float">
        <rect x="52" y="132" width="216" height="12" rx="6" fill="var(--panel-2)" stroke="var(--border-strong)" stroke-width="2"/>
        <path d="M105 96 q28 -12 55 0 q27 -12 55 0 v30 q-28 -10 -55 2 q-27 -12 -55 -2 z" fill="var(--panel)" stroke="var(--border-strong)" stroke-width="2"/>
        <path d="M160 96 v32" stroke="var(--border-strong)" stroke-width="2"/>
        <path d="M120 105 q18 -6 32 0 M120 113 q18 -6 32 0 M168 105 q18 -6 32 0 M168 113 q18 -6 32 0" fill="none" stroke="var(--dim)" stroke-width="2" stroke-linecap="round"/>
        <rect x="232" y="106" width="22" height="20" rx="5" fill="var(--panel)" stroke="var(--border-strong)" stroke-width="2"/>
        <path d="M254 111 q10 2 0 10" fill="none" stroke="var(--border-strong)" stroke-width="2"/>
        <path class="steam" d="M238 100 q-4 -8 2 -14 M246 100 q-4 -8 2 -14" fill="none" stroke="var(--muted)" stroke-width="2" stroke-linecap="round"/>
        <rect x="66" y="92" width="4" height="40" fill="var(--border-strong)"/>
        <path d="M46 92 h44 l-8 -20 h-28 z" fill="var(--amber)" opacity=".9"/>
        <circle cx="68" cy="70" r="8" fill="var(--amber)" opacity=".35"/>
        <path d="M278 132 q-14 -18 -2 -30 q10 10 2 30 M278 132 q14 -16 4 -28 q-12 8 -4 28" fill="var(--accent)" opacity=".8"/>
        <rect x="272" y="126" width="16" height="10" rx="3" fill="var(--panel-2)" stroke="var(--border-strong)" stroke-width="2"/>
      </g>
      <g fill="var(--amber)" class="twinkle">
        <circle cx="42" cy="42" r="2.5"/>
        <circle cx="284" cy="52" r="2"/>
        <circle cx="250" cy="28" r="1.6"/>
      </g>
    </svg>`;

  const INK = `
    <svg class="art art-ink" viewBox="0 0 320 180" aria-hidden="true" focusable="false">
      <circle cx="160" cy="86" r="58" fill="none" stroke="var(--border-strong)" stroke-width="2"/>
      <path d="M112 106 q48 -16 96 0 v28 q-48 -12 -96 0 z" fill="var(--panel)" stroke="var(--border-strong)" stroke-width="2"/>
      <path d="M160 106 v28" stroke="var(--border-strong)" stroke-width="2"/>
      <path d="M126 114 q18 -4 28 0 M126 120 q18 -4 28 0 M166 114 q18 -4 28 0 M166 120 q18 -4 28 0" fill="none" stroke="var(--dim)" stroke-width="2" stroke-linecap="round"/>
      <g fill="var(--accent)" class="twinkle">
        <path d="M92 52 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 z"/>
        <path d="M238 70 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2 z"/>
      </g>
    </svg>`;

  window.LorekeeperArt = {
    picker() {
      return `<div class="picker-art" aria-hidden="true">${PIXEL}${STORYBOOK}${INK}</div>`;
    },
    skinName(theme) {
      return { pixel: "Pixel", storybook: "Storybook", ink: "Ink" }[theme] || "Ink";
    },
  };
})();
