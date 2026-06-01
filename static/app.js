const $ = (sel) => document.querySelector(sel);

function apiUrl(path) {
  const base = (window.STOCK_OBSERVER_API || "").replace(/\/$/, "");
  return `${base}${path}`;
}

function isNativeApp() {
  return Boolean(window.STOCK_OBSERVER_API);
}

const input = $("#stock-input");
const suggestions = $("#suggestions");
const statusEl = $("#status");
const results = $("#results");
const btnAnalyze = $("#btn-analyze");
const btnReport = $("#btn-report");
const tabSelect = $("#tab-select");

let selectedStockId = "";
let lastPayload = null;
let lastAdvice = null;
let debounceTimer = null;
let techChartInstance = null;
let fundamentalCache = null;
let revenueFilter = "24";
let epsFilter = "12";

const REVENUE_FILTER_PRESETS = [
  ["24", "近24個月"],
  ["12", "近12個月"],
  ["ytd", "今年"],
];

const EPS_FILTER_PRESETS = [
  ["12", "近12季"],
  ["8", "近8季"],
  ["ytd", "今年"],
];

function revenueYear(period) {
  const text = String(period || "").trim();
  if (!text.includes("/")) return null;
  const year = parseInt(text.split("/")[0], 10);
  return Number.isFinite(year) ? year : null;
}

function epsYear(period) {
  const text = String(period || "").trim();
  if (!text) return null;
  const year = parseInt(text.split(/\s+/)[0], 10);
  return Number.isFinite(year) ? year : null;
}

function revenueFilterOptions() {
  return [...REVENUE_FILTER_PRESETS];
}

function epsFilterOptions() {
  return [...EPS_FILTER_PRESETS];
}

function filterRevenueRecords(records, mode = "24") {
  if (!records?.length) return [];
  if (mode === "12") return records.slice(0, 12);
  if (mode === "24") return records.slice(0, 24);
  const currentYear = new Date().getFullYear();
  if (mode === "ytd") return records.filter((r) => revenueYear(r.期間) === currentYear);
  return records.slice(0, 24);
}

function filterEpsRecords(records, mode = "12") {
  if (!records?.length) return [];
  if (mode === "8") return records.slice(0, 8);
  if (mode === "12") return records.slice(0, 12);
  const currentYear = new Date().getFullYear();
  if (mode === "ytd") return records.filter((r) => epsYear(r.期間) === currentYear);
  return records.slice(0, 12);
}

function revenueFilterLabel(mode) {
  const match = REVENUE_FILTER_PRESETS.find(([key]) => key === mode);
  return match ? match[1] : mode;
}

function epsFilterLabel(mode) {
  const match = EPS_FILTER_PRESETS.find(([key]) => key === mode);
  return match ? match[1] : mode;
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function table(headers, rows) {
  if (!rows || !rows.length) return '<p class="panel-muted">無資料</p>';
  const head = headers.map((h) => `<th>${esc(h)}</th>`).join("");
  const body = rows
    .map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`)
    .join("");
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function setStatus(msg, isError = false) {
  statusEl.textContent = msg || "";
  statusEl.className = isError ? "status error" : "status";
}

function showPanel(name) {
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.querySelectorAll(".panel").forEach((p) => {
    p.classList.toggle("active", p.id === `panel-${name}`);
  });
  if (tabSelect && tabSelect.value !== name) {
    tabSelect.value = name;
  }
  if (name === "technical" && techChartInstance?.redraw) {
    requestAnimationFrame(() => techChartInstance.redraw());
  }
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => showPanel(tab.dataset.tab));
});

if (tabSelect) {
  tabSelect.addEventListener("change", () => showPanel(tabSelect.value));
}

input.addEventListener("input", () => {
  selectedStockId = "";
  clearTimeout(debounceTimer);
  const q = input.value.trim();
  if (q.length < 1) {
    suggestions.classList.add("hidden");
    return;
  }
  debounceTimer = setTimeout(async () => {
    try {
      const res = await fetch(apiUrl(`/api/stocks/search?q=${encodeURIComponent(q)}`));
      const data = await res.json();
      const items = data.results || [];
      if (!items.length) {
        suggestions.classList.add("hidden");
        return;
      }
      suggestions.innerHTML = items
        .map(
          (s) =>
            `<li data-id="${esc(s.stock_id)}" data-label="${esc(s.label)}">${esc(s.label)}</li>`
        )
        .join("");
      suggestions.classList.remove("hidden");
    } catch {
      suggestions.classList.add("hidden");
    }
  }, 250);
});

suggestions.addEventListener("click", (e) => {
  const li = e.target.closest("li");
  if (!li) return;
  selectedStockId = li.dataset.id;
  input.value = li.dataset.id;
  suggestions.classList.add("hidden");
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".search-wrap")) suggestions.classList.add("hidden");
});

function toRow(item) {
  if (Array.isArray(item)) return item;
  return [item];
}

const ADVICE_TONE_LABEL = {
  bull: "偏多",
  mild_bull: "中性偏多",
  neutral: "中性",
  mild_bear: "中性偏空",
  bear: "偏空",
};

const ADVICE_TONE_ARROW = {
  bull: "↑",
  mild_bull: "↗",
  neutral: "→",
  mild_bear: "↘",
  bear: "↓",
};

function ratioBarFill(name, value) {
  const num = parseFloat(String(value).replace(/,/g, ""));
  if (Number.isNaN(num)) return 50;
  if (name.includes("PE")) return Math.min(100, Math.max(12, (num / 40) * 100));
  return Math.min(100, Math.max(12, (num / 8) * 100));
}

function scoreArcOffset(score, min = -6, max = 12) {
  const pct = Math.min(1, Math.max(0, (score - min) / (max - min)));
  const circumference = 2 * Math.PI * 52;
  return circumference * (1 - pct);
}

function dimBarHeight(score) {
  return Math.min(100, Math.max(12, ((score + 4) / 12) * 100));
}

function dimStars(score) {
  if (score >= 4) return "★★★";
  if (score >= 2) return "★★";
  if (score >= 0) return "★";
  return "☆";
}

function renderValuationMetrics(indicators) {
  if (!indicators || !indicators.length) return "";
  return indicators
    .map((item) => {
      const fill = ratioBarFill(item.名稱, item.數值);
      const level = item.level || "neutral";
      return `
        <div class="ratio-row">
          <div class="ratio-head">
            <span class="ratio-name">${esc(item.名稱)}</span>
            <span class="ratio-value">${esc(item.數值)} <em class="ratio-status ${level}">(${esc(item.狀態)})</em></span>
          </div>
          <div class="ratio-track"><span class="ratio-fill ${level}" style="width:${fill}%"></span></div>
        </div>`;
    })
    .join("");
}

function renderDimBars(dimensions) {
  if (!dimensions || !dimensions.length) return "";
  return dimensions
    .map((d) => {
      const row = toRow(d);
      const name = row[0] || "";
      const score = Number(row[1]) || 0;
      return `
        <div class="dim-mini">
          <div class="dim-mini-bar"><span style="height:${dimBarHeight(score)}%"></span></div>
          <p class="dim-mini-name">${esc(name)}</p>
          <p class="dim-mini-stars">${dimStars(score)}</p>
        </div>`;
    })
    .join("");
}

function renderScoreRing(score) {
  const offset = scoreArcOffset(score);
  const circumference = 2 * Math.PI * 52;
  return `
    <svg class="score-ring" viewBox="0 0 120 120" aria-hidden="true">
      <defs>
        <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#4fd1ff"/>
          <stop offset="100%" stop-color="#ffd166"/>
        </linearGradient>
      </defs>
      <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="9"/>
      <circle cx="60" cy="60" r="52" fill="none" stroke="url(#scoreGrad)" stroke-width="9"
        stroke-linecap="round" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
        transform="rotate(-90 60 60)"/>
    </svg>`;
}

function panelPage(content) {
  return `<div class="panel-page">${content}</div>`;
}

function panelHeader(title, subtitle = "") {
  return `
    <header class="panel-header">
      <h2 class="panel-title">${esc(title)}</h2>
      ${subtitle ? `<p class="panel-subtitle">${esc(subtitle)}</p>` : ""}
    </header>`;
}

function panelSection(title, content) {
  return `
    <section class="panel-glass">
      <h3 class="panel-section-title">${esc(title)}</h3>
      ${content}
    </section>`;
}

function fundamentalHistorySection(sectionId, title, filterId, options, selectedKey, headers, rows) {
  const opts = options
    .map(
      ([key, label]) =>
        `<option value="${esc(key)}"${key === selectedKey ? " selected" : ""}>${esc(label)}</option>`
    )
    .join("");
  return `
    <section class="panel-glass" id="${sectionId}">
      <div class="panel-section-head">
        <h3 class="panel-section-title" id="${sectionId}-title">${esc(title)}</h3>
        <select class="fund-filter" id="${filterId}" aria-label="${esc(title)} 篩選">${opts}</select>
      </div>
      <div id="${filterId}-body">
        ${table(headers, rows)}
      </div>
    </section>`;
}

function bindFundamentalFilters() {
  const revSel = document.getElementById("revenue-filter");
  const epsSel = document.getElementById("eps-filter");
  revSel?.addEventListener("change", () => {
    revenueFilter = revSel.value;
    refreshRevenueTable();
  });
  epsSel?.addEventListener("change", () => {
    epsFilter = epsSel.value;
    refreshEpsTable();
  });
}

function refreshRevenueTable() {
  const f = fundamentalCache;
  if (!f) return;
  const records = f.revenue_history || [];
  const filtered = filterRevenueRecords(records, revenueFilter);
  const label = revenueFilterLabel(revenueFilter);
  const titleEl = document.getElementById("revenue-section-title");
  if (titleEl) titleEl.textContent = `每月營收（${label}）`;
  const body = document.getElementById("revenue-filter-body");
  if (body) {
    body.innerHTML = table(
      ["期間", "營收(億)", "月增率(%)", "年增率(%)"],
      filtered.map((r) => [r.期間, r["營收(億)"], r["月增率(%)"], r["年增率(%)"]])
    );
  }
}

function refreshEpsTable() {
  const f = fundamentalCache;
  if (!f) return;
  const records = f.eps_history || [];
  const filtered = filterEpsRecords(records, epsFilter);
  const label = epsFilterLabel(epsFilter);
  const titleEl = document.getElementById("eps-section-title");
  if (titleEl) titleEl.textContent = `季 EPS（${label}）`;
  const body = document.getElementById("eps-filter-body");
  if (body) {
    body.innerHTML = table(
      ["期間", "EPS(元)", "季增率(%)", "年增率(%)"],
      filtered.map((r) => [r.期間, r["EPS(元)"], r["季增率(%)"], r["年增率(%)"]])
    );
  }
}

function panelError(msg) {
  return panelPage(`<p class="panel-error">${esc(msg)}</p>`);
}

function formatAdviceTitle(display, code) {
  if (!code || display.includes(code)) return display;
  return `${display} (${code})`;
}

function renderEntryProbability(prob) {
  if (!prob || !prob.綜合) return "";
  const overall = prob.綜合;
  const win = Number(overall.賺錢機率) || 50;
  const loss = Number(overall.賠錢機率) || 50;
  const intervals = prob.區間 || [];

  const intervalCards = intervals
    .map((row) => {
      const w = Number(row.賺錢機率) || 50;
      const l = Number(row.賠錢機率) || 50;
      const avg =
        row.平均報酬率 != null
          ? `<span class="prob-avg">平均報酬 ${row.平均報酬率 > 0 ? "+" : ""}${esc(String(row.平均報酬率))}%</span>`
          : "";
      const sample =
        row.樣本數 > 0
          ? `<span class="prob-sample">樣本 ${esc(String(row.樣本數))} 次</span>`
          : "";
      return `<article class="prob-card">
        <div class="prob-card-head">
          <span class="prob-card-label">${esc(row.標籤 || "")}</span>
          ${sample}
        </div>
        <div class="prob-bar-row">
          <span class="prob-bar-label win">賺 ${w}%</span>
          <div class="prob-bar"><span class="prob-bar-win" style="width:${w}%"></span></div>
        </div>
        <div class="prob-bar-row">
          <span class="prob-bar-label loss">賠 ${l}%</span>
          <div class="prob-bar"><span class="prob-bar-loss" style="width:${l}%"></span></div>
        </div>
        <div class="prob-card-meta">${avg}<span class="prob-source">${esc(row.資料來源 || "")}</span></div>
      </article>`;
    })
    .join("");

  return `
    <section class="panel-glass advice-probability">
      <h3 class="panel-section-title">以現價入手 · 賺賠參考機率</h3>
      <div class="prob-overall">
        <div class="prob-overall-item win">
          <span class="prob-overall-num">${win}%</span>
          <span class="prob-overall-label">賺錢機率</span>
        </div>
        <div class="prob-overall-divider">/</div>
        <div class="prob-overall-item loss">
          <span class="prob-overall-num">${loss}%</span>
          <span class="prob-overall-label">賠錢機率</span>
        </div>
      </div>
      <div class="prob-intervals">${intervalCards}</div>
      <p class="prob-note">${esc(prob.說明 || "")}</p>
    </section>`;
}

function renderAdvice(advice) {
  const tone = advice.tone || "neutral";
  const priceTone = advice.價位tone || "neutral";
  const display = advice.顯示名稱 || advice.公司名稱 || "—";
  const code = advice.公司代號 || "";
  const sub = advice.副標名稱 || "";
  const title = formatAdviceTitle(display, code);
  const priceRaw = advice.目前股價顯示 ? advice.目前股價顯示.replace(/\s*元$/, "") : "";
  const priceHero = priceRaw ? `NT$ ${priceRaw}` : "";
  const priceUnit = priceRaw ? "元" : "";
  const valLabel = advice.價位評估 && advice.價位評估 !== "無法判定" ? advice.價位評估 : "";
  const valSummary = advice.估值摘要 || "";
  const valMetrics = renderValuationMetrics(advice.估值指標);
  const verdict = advice.評等 || ADVICE_TONE_LABEL[tone] || "—";
  const verdictArrow = ADVICE_TONE_ARROW[tone] || "→";
  const totalScore = advice.綜合得分 ?? "—";
  const suggestion = advice.入手參考 || "";
  const buyRange = advice.建議買入區間 || "—";
  const buyRangeNote = advice.買入區間說明 || "";
  const scoreNote = advice.評分說明 || "（基本面 + 技術面 + 籌碼面）";
  const dimRows = (advice.dimensions || []).map((d) => toRow(d));
  const detailRows = (advice.details || []).map((d) => toRow(d));
  const candleSignals = advice.關鍵K棒 || [];
  const probabilityBlock = renderEntryProbability(advice.入手機率);
  const candleBlock =
    candleSignals.length > 0
      ? `
    <section class="panel-glass advice-candles">
      <h3 class="panel-section-title">關鍵 K 棒訊號（最新交易日）</h3>
      <div class="candle-signals">
        ${candleSignals
          .map(
            (s) =>
              `<div class="candle-signal ${esc(s.tone || "neutral")}">
                <span class="candle-signal-name">${esc(s.名稱 || "")}</span>
                <span class="candle-signal-date">${esc(s.日期 || "")}</span>
                <span class="candle-signal-desc">${esc(s.說明 || "")}</span>
              </div>`
          )
          .join("")}
      </div>
    </section>`
      : "";

  const valuationBlock =
    valLabel || valSummary || valMetrics
      ? `
    <section class="panel-glass advice-valuation">
      <h3 class="panel-section-title">估值評估</h3>
      ${
        valLabel
          ? `<p class="advice-price-tag">目前價位：<span class="price-tag ${priceTone}">${esc(valLabel)}</span></p>`
          : ""
      }
      ${valSummary ? `<p class="advice-val-summary">${esc(valSummary)}</p>` : ""}
      ${valMetrics}
    </section>`
      : "";

  $("#panel-advice").innerHTML = panelPage(`
    <div class="advice-dashboard tone-${tone}">
      ${panelHeader(title, sub)}

      <div class="advice-grid">
        <div class="advice-col advice-col-left">
          ${valuationBlock}
          <section class="panel-glass advice-entry">
            <h3 class="panel-section-title">入手參考</h3>
            <span class="verdict-badge ${tone}">${esc(verdict)} ${verdictArrow}</span>
            <p class="advice-buy-range">建議買入區間：<strong>${esc(buyRange)}</strong>${buyRangeNote ? `<span class="advice-buy-note">（${esc(buyRangeNote)}）</span>` : ""}</p>
          </section>
          <section class="panel-glass advice-strategy">
            <h3 class="panel-section-title">操作策略</h3>
            <p class="panel-intro">${esc(suggestion)}</p>
          </section>
          ${probabilityBlock}
        </div>

        <div class="advice-col advice-col-right">
          <section class="panel-glass advice-hero">
            ${priceHero ? `<p class="hero-price-label">目前股價</p><p class="hero-price">${esc(priceHero)} <span>${esc(priceUnit)}</span></p>` : ""}
            <div class="hero-score-wrap">
              ${renderScoreRing(Number(totalScore) || 0)}
              <div class="hero-score-text">
                <span class="hero-score-num">${esc(String(totalScore))}</span>
                <span class="hero-score-label">綜合得分</span>
              </div>
            </div>
            <p class="hero-score-note">${esc(scoreNote)}</p>
            <div class="dim-mini-row">${renderDimBars(advice.dimensions)}</div>
          </section>
        </div>
      </div>

      ${candleBlock}

      <div class="panel-details">
        ${panelSection("各面向得分", table(["面向", "得分", "說明"], dimRows))}
        ${panelSection("評估細項", table(["項目", "評語", "加減"], detailRows))}
        <p class="panel-disclaimer">${esc(advice.免責聲明 || "")}</p>
      </div>
    </div>
  `);
}

function renderProfile(p) {
  if (p.錯誤) {
    $("#panel-profile").innerHTML = panelError(p.錯誤);
    return;
  }
  const title = `${p.公司名稱 || ""}（${p.公司代號 || ""}）`;
  const meta = `${p.交易市場 || ""} ｜ ${p.產業分類 || ""}`;
  const themes = (p.themes || []).map((t) => `<span class="panel-tag">${esc(t)}</span>`).join("");
  $("#panel-profile").innerHTML = panelPage(`
    ${panelHeader(title, meta)}
    ${panelSection(
      "基本資訊",
      table(
        ["項目", "內容"],
        [
          ["員工人數", p.員工人數],
          ["總部", p.總部],
          ["官網", p.官網],
        ]
      )
    )}
    ${panelSection(
      "投資題材",
      `<div class="panel-tags">${themes || '<span class="panel-muted">待觀察</span>'}</div>`
    )}
    ${panelSection("中文概況", `<p class="panel-intro">${esc(p.中文概況 || "")}</p>`)}
    ${
      p.原文摘要
        ? panelSection("原文摘要", `<p class="panel-intro">${esc(p.原文摘要)}</p>`)
        : ""
    }
  `);
}

function renderFundamental(f) {
  if (f.錯誤) {
    fundamentalCache = null;
    $("#panel-fundamental").innerHTML = panelError(f.錯誤);
    return;
  }
  fundamentalCache = f;
  const m = f.metrics || {};
  const title = formatAdviceTitle(m.顯示名稱 || m.公司名稱 || "基本面分析", m.公司代號 || "");
  const sub = m.副標名稱 || m.英文名稱 || "";
  const header = [
    ["公司名稱", m.公司名稱],
    ["公司代號", m.公司代號],
    ["英文名稱", m.英文名稱],
    ["目前股價", m.目前股價],
    ["價位評估", m.價位評估],
  ];
  const valKeys = ["價位說明", "市值 (億)", "本益比 (PE)", "股價淨值比 (PB)", "每股盈餘 (EPS)", "股利殖利率 (%)"];
  const valRows = valKeys.filter((k) => m[k] != null).map((k) => [k, m[k]]);

  const revenueRecords = f.revenue_history || [];
  const epsRecords = f.eps_history || [];
  const revOptions = revenueFilterOptions(revenueRecords);
  const epsOptions = epsFilterOptions(epsRecords);
  if (!revOptions.some(([key]) => key === revenueFilter)) revenueFilter = "24";
  if (!epsOptions.some(([key]) => key === epsFilter)) epsFilter = "12";

  const revLabel = revenueFilterLabel(revenueFilter);
  const epsLabel = epsFilterLabel(epsFilter);
  const revRows = filterRevenueRecords(revenueRecords, revenueFilter).map((r) => [
    r.期間, r["營收(億)"], r["月增率(%)"], r["年增率(%)"],
  ]);
  const epsRows = filterEpsRecords(epsRecords, epsFilter).map((r) => [
    r.期間, r["EPS(元)"], r["季增率(%)"], r["年增率(%)"],
  ]);

  $("#panel-fundamental").innerHTML = panelPage(`
    ${panelHeader(title, sub)}
    ${panelSection("基本資料", table(["指標", "數值"], header))}
    ${panelSection("估值指標", table(["指標", "數值"], valRows))}
    ${fundamentalHistorySection(
      "revenue-section",
      `每月營收（${revLabel}）`,
      "revenue-filter",
      revOptions,
      revenueFilter,
      ["期間", "營收(億)", "月增率(%)", "年增率(%)"],
      revRows
    )}
    ${fundamentalHistorySection(
      "eps-section",
      `季 EPS（${epsLabel}）`,
      "eps-filter",
      epsOptions,
      epsFilter,
      ["期間", "EPS(元)", "季增率(%)", "年增率(%)"],
      epsRows
    )}
  `);
  bindFundamentalFilters();
}

function renderTechnical(t, chartB64) {
  if (t.error) {
    $("#panel-technical").innerHTML = panelError(t.error);
    return;
  }
  const sumRows = Object.entries(t.summary || {}).map(([k, v]) => [k, v]);
  const lv = t.levels || {};
  const srRows = [];
  (lv.supports || []).forEach((p, i) => srRows.push([`支撐 ${i + 1}`, p]));
  (lv.resistances || []).forEach((p, i) => srRows.push([`壓力 ${i + 1}`, p]));

  if (techChartInstance?.destroy) techChartInstance.destroy();
  techChartInstance = null;

  const hasBars = Array.isArray(t.bars) && t.bars.length > 0;
  const chartBlock = hasBars
    ? '<div id="tech-chart-host" class="chart-interactive-wrap"></div>'
    : chartB64
      ? `<img class="chart-img" src="data:image/png;base64,${chartB64}" alt="K線圖">`
      : '<p class="panel-muted">無法產生 K 線圖</p>';

  $("#panel-technical").innerHTML = panelPage(`
    ${panelHeader("技術面分析", "均線 · KD · MACD · 支撐壓力 · 查價")}
    ${panelSection("技術摘要", table(["指標", "數值"], sumRows))}
    ${panelSection("支撐 / 壓力", table(["價位", "數值"], srRows))}
    ${panelSection("K 線圖", chartBlock)}
  `);

  const host = document.getElementById("tech-chart-host");
  if (hasBars && window.StockInteractiveChart && host) {
    techChartInstance = window.StockInteractiveChart.mount(host, {
      bars: t.bars,
      levels: t.levels || {},
      stockName: t.stock_name || "",
      displayDays: t.display_days || 90,
    });
  } else if (chartB64 && host) {
    host.innerHTML = `<img class="chart-img" src="data:image/png;base64,${chartB64}" alt="K線圖">`;
  }
}

function renderChips(c) {
  const records = c.records || [];
  const summary = c.summary || {};
  if (!records.length || records[0].錯誤) {
    $("#panel-chips").innerHTML = panelError(records[0]?.錯誤 || "查無籌碼資料");
    return;
  }
  const sumRows = Object.entries(summary).map(([k, v]) => [k, v]);
  const dailyRows = records.map((r) => [
    r.日期,
    r["外資買賣超(張)"],
    r["投信買賣超(張)"],
    r["自營商買賣超(張)"],
    r["三大法人合計(張)"],
  ]);
  $("#panel-chips").innerHTML = panelPage(`
    ${panelHeader("籌碼面分析", "三大法人 · 外資 · 投信 · 自營商")}
    ${panelSection("法人摘要", table(["項目", "狀態"], sumRows))}
    ${panelSection("每日明細", table(["日期", "外資", "投信", "自營商", "合計"], dailyRows))}
  `);
}

function renderNews(list) {
  if (!list || !list.length) {
    $("#panel-news").innerHTML = panelPage('<p class="panel-muted">查無新聞</p>');
    return;
  }
  const cards = list
    .map((n, i) => {
      const link = n.連結
        ? `<a class="news-link" href="${esc(n.連結)}" target="_blank" rel="noopener">閱讀全文</a>`
        : "";
      return `<article class="news-card">
        <span class="news-index">${i + 1}</span>
        <div class="news-body">
          <h4 class="news-title">${esc(n.標題)}</h4>
          <p class="news-meta">${esc(n.來源)} · ${esc(n.發布時間)}</p>
          ${link}
        </div>
      </article>`;
    })
    .join("");
  $("#panel-news").innerHTML = panelPage(`
    ${panelHeader("消息面", "最新相關新聞與公告")}
    <section class="panel-glass">
      <div class="news-list">${cards}</div>
    </section>
  `);
}

function renderAll(data) {
  renderAdvice(data.advice || {});
  renderProfile(data.sections?.profile || {});
  renderFundamental(data.sections?.fundamental || {});
  renderTechnical(data.sections?.technical || {}, data.chart_base64);
  renderChips(data.sections?.chips || {});
  renderNews(data.sections?.news || []);
  results.classList.remove("hidden");
  showPanel("advice");
}

async function analyze() {
  const query = input.value.trim();
  if (!query) {
    setStatus("請先輸入股票代號或名稱", true);
    return;
  }
  btnAnalyze.disabled = true;
  btnReport.disabled = true;
  setStatus("正在連線資料源，分析中…（約 10～30 秒）");
  results.classList.add("hidden");

  try {
    const res = await fetch(apiUrl("/api/analyze"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stock_id: selectedStockId, query }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "分析失敗");

    lastPayload = { stock_id: selectedStockId, query: data.stock_id || query };
    lastAdvice = data.advice || null;
    renderAll(data);
    input.value = data.stock_id || query;
    selectedStockId = data.stock_id || "";

    let status = "分析完成";
    if (data.errors?.length) status += `（部分資料未能載入：${data.errors.join("、")}）`;
    setStatus(status);
    btnReport.disabled = false;
  } catch (err) {
    setStatus(err.message || "分析失敗", true);
  } finally {
    btnAnalyze.disabled = false;
  }
}

function parseDownloadFilename(res, fallback) {
  const cd = res.headers.get("Content-Disposition") || "";
  const utf8 = cd.match(/filename\*=UTF-8''([^;\s]+)/i);
  if (utf8) {
    try {
      return decodeURIComponent(utf8[1]);
    } catch {
      /* ignore */
    }
  }
  const plain = cd.match(/filename="([^"]+)"/i);
  if (plain) return plain[1];
  return fallback;
}

function reportFilenameFromAdvice(stockId, advice) {
  const sid = String(stockId || "").trim();
  let name = String(advice?.公司名稱 || "").trim();
  if (!name) {
    let display = String(advice?.顯示名稱 || "").trim();
    for (const token of [`（${sid}）`, `(${sid})`, sid]) {
      display = display.replaceAll(token, "");
    }
    name = display.replace(/^[（(]|[）)]$/g, "").trim();
  }
  if (!name) name = sid;
  const safe = (s) => String(s).replace(/[\\/:*?"<>|\n\r\t]/g, "");
  return `${safe(sid)}${safe(name)}報告.pdf`;
}

async function downloadReport() {
  if (!lastPayload) return;
  btnReport.disabled = true;
  setStatus("正在產生報告…");
  try {
    const res = await fetch(apiUrl("/api/report"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...lastPayload,
        revenue_filter: revenueFilter,
        eps_filter: epsFilter,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "報告失敗");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const fallback = reportFilenameFromAdvice(
      lastPayload.stock_id || lastPayload.query,
      lastAdvice,
    );
    a.download = parseDownloadFilename(res, fallback);
    a.click();
    URL.revokeObjectURL(url);
    setStatus("報告已下載");
  } catch (err) {
    setStatus(err.message || "報告失敗", true);
  } finally {
    btnReport.disabled = false;
  }
}

btnAnalyze.addEventListener("click", analyze);
btnReport.addEventListener("click", downloadReport);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") analyze();
});

(function initApp() {
  const sub = $("#app-subtitle");
  if (sub && isNativeApp()) {
    sub.textContent = "Android 版 · 基本面 · 技術面 · 籌碼面 · 綜合評估";
  }
  if (isNativeApp()) {
    fetch(apiUrl("/api/health"))
      .then((r) => (r.ok ? setStatus("就緒 — 輸入股號或名稱開始分析") : Promise.reject()))
      .catch(() =>
        setStatus("無法連線分析伺服器，請確認網路或 API 設定", true)
      );
  } else {
    setStatus("就緒 — 輸入股號或名稱開始分析");
  }
})();
