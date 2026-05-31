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
let debounceTimer = null;

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

function panelError(msg) {
  return panelPage(`<p class="panel-error">${esc(msg)}</p>`);
}

function formatAdviceTitle(display, code) {
  if (!code || display.includes(code)) return display;
  return `${display} (${code})`;
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
  const dimRows = (advice.dimensions || []).map((d) => toRow(d));
  const detailRows = (advice.details || []).map((d) => toRow(d));

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
          </section>
          <section class="panel-glass advice-strategy">
            <h3 class="panel-section-title">操作策略</h3>
            <p class="panel-intro">${esc(suggestion)}</p>
          </section>
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
            <p class="hero-score-note">（基本面 + 技術面 + 籌碼面）</p>
            <div class="dim-mini-row">${renderDimBars(advice.dimensions)}</div>
          </section>
        </div>
      </div>

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
    $("#panel-fundamental").innerHTML = panelError(f.錯誤);
    return;
  }
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

  const revRows = (f.revenue_history || []).map((r) => [
    r.期間, r["營收(億)"], r["月增率(%)"], r["年增率(%)"],
  ]);
  const epsRows = (f.eps_history || []).map((r) => [
    r.期間, r["EPS(元)"], r["季增率(%)"], r["年增率(%)"],
  ]);

  $("#panel-fundamental").innerHTML = panelPage(`
    ${panelHeader(title, sub)}
    ${panelSection("基本資料", table(["指標", "數值"], header))}
    ${panelSection("估值指標", table(["指標", "數值"], valRows))}
    ${panelSection("每月營收", table(["期間", "營收(億)", "月增率(%)", "年增率(%)"], revRows))}
    ${panelSection("季 EPS", table(["期間", "EPS(元)", "季增率(%)", "年增率(%)"], epsRows))}
  `);
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

  const chartBlock = chartB64
    ? `<img class="chart-img" src="data:image/png;base64,${chartB64}" alt="K線圖">`
    : '<p class="panel-muted">無法產生 K 線圖</p>';

  $("#panel-technical").innerHTML = panelPage(`
    ${panelHeader("技術面分析", "均線 · KD · MACD · 支撐壓力")}
    ${panelSection("技術摘要", table(["指標", "數值"], sumRows))}
    ${panelSection("支撐 / 壓力", table(["價位", "數值"], srRows))}
    ${panelSection("K 線圖", chartBlock)}
  `);
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

async function downloadReport() {
  if (!lastPayload) return;
  btnReport.disabled = true;
  setStatus("正在產生報告…");
  try {
    const res = await fetch(apiUrl("/api/report"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lastPayload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "報告失敗");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${lastPayload.query || lastPayload.stock_id}_report.pdf`;
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
