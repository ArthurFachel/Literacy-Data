/**
 * Brazil Literacy Data Explorer - Frontend (v2)
 * Dimensao atual + clique no mapa
 */

const API_URL = 'http://localhost:5000';

let currentDim = 'escolas';
let selectedRegions = new Set();
let isCompareMode = false;
let lastRegionData = null;
let lastExtremesData = null;
let currentSort = { col: 'taxa_alfabetizacao', dir: 'desc' };

const regiaoCor = {
  'Norte': '#4ade80',
  'Nordeste': '#f87171',
  'Centro-Oeste': '#fbbf24',
  'Sudeste': '#60a5fa',
  'Sul': '#a78bfa'
};

const dimLabels = {
  escolas: 'Escolas (INEP)',
  saneamento: 'Saneamento (SINISA)',
  correlacoes: 'Correlações',
  alfabetizacao: 'Alfabetização Geral'
};

// DOM refs
const welcomeMsg     = document.getElementById('welcome-msg');
const dataDisplay    = document.getElementById('data-display');
const compareDisplay = document.getElementById('compare-display');
const mapWrapper     = document.getElementById('brazil-map');
const compareCheckbox = document.getElementById('compare-mode');
const btnCompare     = document.getElementById('btn-compare');
const btnClear       = document.getElementById('btn-clear');
const mapLabel       = document.getElementById('map-label');

document.addEventListener('DOMContentLoaded', initApp);

function initApp() {
  initDimensionTabs();
  initMapInteractive();
  initCompareControls();
}

/* -------------------------------------------------- */
/*  Dimension Tabs (top)                               */
/* -------------------------------------------------- */
function initDimensionTabs() {
  document.querySelectorAll('.dim-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const dim = btn.getAttribute('data-dim');
      switchDimension(dim);
    });
  });
  updateMapLabel();
}

function switchDimension(dim) {
  currentDim = dim;
  document.querySelectorAll('.dim-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.dim-btn[data-dim="${dim}"]`)?.classList.add('active');

  // Clear display but keep selection
  if (isCompareMode) {
    showCompare();
  } else {
    hideAll();
    welcomeMsg.classList.remove('hidden');
  }
  updateMapLabel();
}

function updateMapLabel() {
  mapLabel.textContent = isCompareMode ? 'Selecione regiões para comparar' : `Selecione uma região em "${dimLabels[currentDim]}"`;
}

/* -------------------------------------------------- */
/*  Map Interaction                                    */
/* -------------------------------------------------- */
function initMapInteractive() {
  const regioes = mapWrapper.querySelectorAll('.regiao');
  regioes.forEach(el => {
    const regiao = el.getAttribute('data-regiao');
    if (!regiao) return;
    el.style.cursor = 'pointer';

    el.addEventListener('click', (e) => {
      e.stopPropagation();
      handleRegionClick(regiao, el);
    });

    el.addEventListener('mouseenter', () => {
      const paths = el.querySelectorAll('path');
      if (!el.classList.contains('active') && !el.classList.contains('selected')) {
        paths.forEach(p => p.style.filter = 'brightness(1.12)');
      }
    });
    el.addEventListener('mouseleave', () => {
      el.querySelectorAll('path').forEach(p => p.style.filter = '');
    });
  });

  document.querySelectorAll('.regiao text').forEach(lbl => {
    const g = lbl.closest('g');
    if (!g) return;
    const regiao = g.getAttribute('data-regiao');
    if (!regiao) return;
    lbl.style.cursor = 'pointer';
    lbl.style.pointerEvents = 'auto';
    lbl.addEventListener('click', (e) => {
      e.stopPropagation();
      const el = mapWrapper.querySelector(`.regiao[data-regiao="${regiao}"]`);
      if (el) handleRegionClick(regiao, el);
    });
  });
}

async function handleRegionClick(regiao, svgEl) {
  if (isCompareMode) {
    toggleRegionSelection(regiao, svgEl);
    return;
  }

  clearAllHighlights();
  highlightRegion(regiao, false);
  hideAll();
  dataDisplay.classList.remove('hidden');
  dataDisplay.innerHTML = '<div class="loading"><div class="spinner"></div>Carregando...</div>';

  try {
    await renderDimensionData(regiao);
  } catch (err) {
    dataDisplay.innerHTML = `<p class="loading">Erro: ${err.message}</p>`;
  }
}

async function renderDimensionData(regiao) {
  if (currentDim === 'escolas') await renderDimEscolas(regiao);
  else if (currentDim === 'saneamento') await renderDimSaneamento(regiao);
  else if (currentDim === 'correlacoes') await renderDimCorrelacoes(regiao);
  else if (currentDim === 'alfabetizacao') await renderDimAlfabetizacao(regiao);
}

/* -------------------------------------------------- */
/*  Compare Mode                                       */
/* -------------------------------------------------- */
function initCompareControls() {
  compareCheckbox.addEventListener('change', (e) => {
    isCompareMode = e.target.checked;
    updateMapLabel();
    if (!isCompareMode) {
      selectedRegions.clear();
      clearAllHighlights();
      btnCompare.disabled = true;
      hideAll();
      welcomeMsg.classList.remove('hidden');
    } else {
      hideAll();
      compareDisplay.classList.remove('hidden');
      compareDisplay.innerHTML = '<p style="text-align:center;padding:40px;color:#94a3b8;">Selecione pelo menos 2 regiões no mapa e clique em "Comparar Selecionadas".</p>';
    }
  });

  btnCompare.addEventListener('click', doCompare);
  btnClear.addEventListener('click', () => {
    selectedRegions.clear();
    clearAllHighlights();
    btnCompare.disabled = true;
    if (isCompareMode) {
      hideAll();
      compareDisplay.classList.remove('hidden');
      compareDisplay.innerHTML = '<p style="text-align:center;padding:40px;color:#94a3b8;">Selecione pelo menos 2 regiões no mapa e clique em "Comparar Selecionadas".</p>';
    } else {
      hideAll();
      welcomeMsg.classList.remove('hidden');
    }
  });
}

function toggleRegionSelection(regiao, svgEl) {
  if (selectedRegions.has(regiao)) {
    selectedRegions.delete(regiao);
    unhighlightRegion(regiao);
  } else {
    selectedRegions.add(regiao);
    highlightRegion(regiao, true);
  }
  btnCompare.disabled = selectedRegions.size < 2;
}

async function doCompare() {
  if (selectedRegions.size < 2) return;
  hideAll();
  compareDisplay.classList.remove('hidden');
  compareDisplay.innerHTML = '<div class="loading"><div class="spinner"></div>Carregando comparação...</div>';

  try {
    const res = await fetch(`${API_URL}/regions/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ regions: Array.from(selectedRegions) })
    });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    renderCompareData(data.comparison);
  } catch (err) {
    compareDisplay.innerHTML = `<p class="loading">Erro: ${err}</p>`;
  }
}

/* -------------------------------------------------- */
/*  Dimension: Alfabetização Geral                     */
/* -------------------------------------------------- */
async function renderDimAlfabetizacao(regiao) {
  const [regionRes, extremesRes] = await Promise.all([
    fetch(`${API_URL}/regions/${encodeURIComponent(regiao)}`),
    fetch(`${API_URL}/regions/${encodeURIComponent(regiao)}/extremes`)
  ]);
  if (!regionRes.ok) throw new Error(regionRes.status);
  if (!extremesRes.ok) throw new Error(extremesRes.status);
  const regionData = await regionRes.json();
  const extremesData = await extremesRes.json();
  lastRegionData = regionData;
  lastExtremesData = extremesData;

  computeRanks(regionData);
  const sorted = sortData(regionData, currentSort.col, currentSort.dir);

  function arrow(col) {
    if (currentSort.col !== col) return '';
    return currentSort.dir === 'asc' ? ' ▲' : ' ▼';
  }

  dataDisplay.innerHTML = `
    <div class="region-header">
      <h2>${regiao}</h2>
      <span>${regionData.total} municípios</span>
    </div>
    <div class="cards">
      <div class="card best">
        <h3>Melhor Município</h3>
        <p class="municipio">${extremesData.best.municipio}</p>
        <p class="rate">${extremesData.best.taxa_alfabetizacao}%</p>
      </div>
      <div class="card worst">
        <h3>Pior Município</h3>
        <p class="municipio">${extremesData.worst.municipio}</p>
        <p class="rate">${extremesData.worst.taxa_alfabetizacao}%</p>
      </div>
    </div>
    <h3>Todos os Municípios</h3>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="sortable" data-sort="rank">Rank</th>
            <th class="sortable" data-sort="municipio">Município${arrow('municipio')}</th>
            <th class="sortable" data-sort="taxa_alfabetizacao">Taxa Alf.${arrow('taxa_alfabetizacao')}</th>
            <th class="sortable" data-sort="pop_total">População${arrow('pop_total')}</th>
          </tr>
        </thead>
        <tbody>
          ${sorted.map((m) => `
            <tr>
              <td>${m.rank}</td>
              <td>${m.municipio}</td>
              <td>${m.taxa_alfabetizacao}</td>
              <td>${typeof m.pop_total === 'number' ? m.pop_total.toLocaleString() : m.pop_total}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
  addSortListeners(regiao, regionData, extremesData);
}

/* -------------------------------------------------- */
/*  Dimension: Escolas (INEP)                          */
/* -------------------------------------------------- */
async function renderDimEscolas(regiao) {
  const res = await fetch(`${API_URL}/regions/${encodeURIComponent(regiao)}/school-infra`);
  if (!res.ok) throw new Error(res.status);
  const data = await res.json();

  const infraMetrics = [
    { key: 'refeitorio_publica_pct', label: 'Refeitório (% escolas públicas)', color: '#4ade80' },
    { key: 'refeitorio_privada_pct', label: 'Refeitório (% escolas privadas)', color: '#60a5fa' },
    { key: 'cozinha_publica_pct', label: 'Cozinha (% escolas públicas)', color: '#fbbf24' },
    { key: 'cozinha_privada_pct', label: 'Cozinha (% escolas privadas)', color: '#a78bfa' },
  ];

  let html = `
    <div class="region-header">
      <h2>${data.regiao}</h2>
      <span>${data.municipios} municípios</span>
    </div>
    <div class="section-desc">Infraestrutura escolar por região (INEP)</div>
  `;

  html += '<div class="region-info">';
  html += `<div class="region-stat"><span class="region-stat-label">Municípios com dados INEP</span><span class="region-stat-value">${data.municipios}</span></div>`;
  html += `<div class="region-stat"><span class="region-stat-label">Alfabetização média</span><span class="region-stat-value">${data.alfabetizacao_media}%</span></div>`;
  html += '</div>';

  html += '<h3 style="margin-top:20px;">Métricas de Infraestrutura</h3>';
  html += '<div class="table-wrap"><table><tbody>';
  for (const m of infraMetrics) {
    const val = data[m.key] || 0;
    html += `<tr><td style="width:220px;">${m.label}</td><td>
      <div class="bar-cell">
        <div class="bar-track"><div class="bar-fill" style="width:${val}%;background:${m.color};"></div></div>
        <span class="bar-value">${val}%</span>
      </div>
    </td></tr>`;
  }
  html += '</tbody></table></div>';

  dataDisplay.innerHTML = html;
}

/* -------------------------------------------------- */
/*  Dimension: Saneamento (SINISA)                     */
/* -------------------------------------------------- */
async function renderDimSaneamento(regiao) {
  const res = await fetch(`${API_URL}/regions/${encodeURIComponent(regiao)}/sanitation-provider`);
  if (!res.ok) throw new Error(res.status);
  const data = await res.json();

  let html = `
    <div class="region-header">
      <h2>${data.regiao}</h2>
      <span>${data.total_municipios} municípios</span>
    </div>
    <div class="section-desc">Saneamento por natureza do prestador (SINISA)</div>
  `;

  html += '<div class="region-info">';
  if (data.total_municipios > 0) {
    html += `<div class="region-stat"><span class="region-stat-label">Total com dados SINISA</span><span class="region-stat-value">${data.total_municipios}</span></div>`;
    html += `<div class="region-stat"><span class="region-stat-label">% Prestador Público</span><span class="region-stat-value">${data.pct_saneamento_publico}%</span></div>`;
    html += `<div class="region-stat"><span class="region-stat-label">% Prestador Privado</span><span class="region-stat-value">${data.pct_saneamento_privado}%</span></div>`;
    if (data.alf_publico !== null) {
      html += `<div class="region-stat"><span class="region-stat-label">Alf. (público)</span><span class="region-stat-value">${data.alf_publico}%</span></div>`;
    }
    if (data.alf_privado !== null) {
      html += `<div class="region-stat"><span class="region-stat-label">Alf. (privado)</span><span class="region-stat-value">${data.alf_privado}%</span></div>`;
    }
    if (data.cobertura_publico !== null) {
      html += `<div class="region-stat"><span class="region-stat-label">Cobertura água (público)</span><span class="region-stat-value">${data.cobertura_publico}%</span></div>`;
    }
    if (data.cobertura_privado !== null) {
      html += `<div class="region-stat"><span class="region-stat-label">Cobertura água (privado)</span><span class="region-stat-value">${data.cobertura_privado}%</span></div>`;
    }
  } else {
    html += '<p style="color:#94a3b8;">Sem dados SINISA para esta região.</p>';
  }
  html += '</div>';

  if (data.total_municipios > 0) {
    html += '<h3 style="margin-top:20px;">Distribuição: Público vs Privado</h3>';
    html += '<div class="bar-cell">';
    html += '<div class="dual-bar-track">';
    html += `<div class="dual-bar-fill" style="width:${data.pct_saneamento_publico}%;background:#4ade80;"></div>`;
    html += `<div class="dual-bar-fill" style="width:${data.pct_saneamento_privado}%;background:#60a5fa;"></div>`;
    html += '</div>';
    html += '<span class="bar-value">' + data.pct_saneamento_publico + '% / ' + data.pct_saneamento_privado + '%</span>';
    html += '</div>';
  }

  dataDisplay.innerHTML = html;
}

/* -------------------------------------------------- */
/*  Dimension: Correlações                              */
/* -------------------------------------------------- */
async function renderDimCorrelacoes(regiao) {
  // Correlations are global, but we highlight that this is for the selected region context
  const res = await fetch(`${API_URL}/correlations`);
  if (!res.ok) throw new Error(res.status);
  const data = await res.json();

  const labelMap = {
    refeitorio_publica: 'Refeitório em escolas PÚBLICAS',
    refeitorio_privada: 'Refeitório em escolas PRIVADAS',
    cozinha_publica: 'Cozinha em escolas PÚBLICAS',
    cozinha_privada: 'Cozinha em escolas PRIVADAS',
    cobertura_agua: 'Cobertura de água (SINISA)',
    saneamento_privado_dummy: 'Saneamento PRIVADO (dummy)',
  };

  let html = `
    <div class="region-header">
      <h2>${regiao}</h2>
    </div>
    <div class="section-desc">Correlações gerais (Pearson r) - mesma amostra para todas as regiões</div>
    <div class="comparison-note">Clique em outras dimensões para ver dados específicos da região.</div>
  `;

  html += '<div class="corr-grid">';
  for (const [key, vals] of Object.entries(data.correlations)) {
    const label = labelMap[key] || key;
    const sig = vals.p < 0.05 ? ' *' : '';
    html += `
      <div class="corr-card">
        <h4>${label}</h4>
        <div class="r-val">r = ${vals.r > 0 ? '+' : ''}${vals.r}${sig}</div>
        <div class="p-val">p = ${vals.p} (n=${vals.n})</div>
      </div>`;
  }
  html += '</div>';

  dataDisplay.innerHTML = html;
}

/* -------------------------------------------------- */
/*  Helpers                                            */
/* -------------------------------------------------- */
function sortData(data, col, dir) {
  const sorted = [...data.municipalities];
  sorted.sort((a, b) => {
    let av, bv;
    if (col === 'municipio') { av = a.municipio; bv = b.municipio; return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av); }
    else if (col === 'pop_total') { av = a.pop_total; bv = b.pop_total; }
    else { av = parseFloat(a.taxa_alfabetizacao); bv = parseFloat(b.taxa_alfabetizacao); }
    if (av < bv) return dir === 'asc' ? -1 : 1;
    if (av > bv) return dir === 'asc' ? 1 : -1;
    return 0;
  });
  return sorted;
}

function computeRanks(data) {
  const arr = [...data.municipalities].sort((a, b) => parseFloat(b.taxa_alfabetizacao) - parseFloat(a.taxa_alfabetizacao));
  arr.forEach((m, i) => { m.rank = i + 1; });
}

function addSortListeners(regiao, regionData, extremesData) {
  dataDisplay.querySelectorAll('.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.getAttribute('data-sort');
      if (col === 'rank') return;
      if (currentSort.col === col) {
        currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
      } else {
        currentSort.col = col;
        currentSort.dir = 'asc';
      }
      renderDimAlfabetizacao(regiao);
    });
  });
}

function renderCompareData(rows) {
  compareDisplay.innerHTML = `
    <h2 style="margin-bottom:16px;">Comparação entre Regiões</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Região</th><th>Municípios</th><th>Média</th><th>Mediana</th><th>Min</th><th>Max</th><th>Desvio Padrão</th></tr>
        </thead>
        <tbody>
          ${rows.map(r => `
            <tr>
              <td><span class="dot" style="background:${regiaoCor[r.regiao]||'#94a3b8'};display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;"></span><strong>${r.regiao}</strong></td>
              <td>${r.municipios}</td>
              <td>${r.media}%</td>
              <td>${r.mediana}%</td>
              <td>${r.minimo}%</td>
              <td>${r.maximo}%</td>
              <td>${r.desvio_padrao}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function hideAll() {
  welcomeMsg.classList.add('hidden');
  dataDisplay.classList.add('hidden');
  compareDisplay.classList.add('hidden');
}

function showCompare() {
  hideAll();
  compareDisplay.classList.remove('hidden');
}

function highlightRegion(regiao, selectedMode = false) {
  const cls = selectedMode ? 'selected' : 'active';
  mapWrapper.querySelectorAll(`.regiao[data-regiao="${regiao}"]`).forEach(el => {
    el.classList.add(cls);
    el.classList.remove(selectedMode ? 'active' : 'selected');
  });
}

function unhighlightRegion(regiao) {
  mapWrapper.querySelectorAll(`.regiao[data-regiao="${regiao}"]`).forEach(el => {
    el.classList.remove('active', 'selected');
  });
}

function clearAllHighlights() {
  mapWrapper.querySelectorAll('.regiao').forEach(el => {
    el.classList.remove('active', 'selected');
  });
}
