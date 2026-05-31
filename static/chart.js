/**
 * Web 互動 K 線圖（查價、週期切換）— 台股紅漲綠跌
 */
(function () {
  const UP = "#ef5350";
  const DOWN = "#26a69a";
  const BG = "#0b1520";
  const PANEL = "#111c28";
  const GRID = "#2a3a4a";
  const TEXT = "#b8c8d8";
  const CROSS = "#888888";
  const MA_COLORS = {
    MA5: "#ffeb3b",
    MA10: "#29b6f6",
    MA20: "#ab47bc",
    MA60: "#ffffff",
  };
  const PERIODS = [30, 90, 180];

  function fmt(v, digits = 2) {
    if (v == null || Number.isNaN(v)) return "--";
    return Number(v).toFixed(digits);
  }

  function fmtVol(v) {
    if (v == null) return "--";
    return Math.round(v).toLocaleString("zh-TW");
  }

  function kdStatus(k, d) {
    if (k == null || d == null) return "";
    if (k > 80 && d > 80) return " 高檔鈍化";
    if (k < 20 && d < 20) return " 低檔鈍化";
    return "";
  }

  function quickLevels(bars) {
    if (!bars.length) {
      return { supports: [], resistances: [], period_high: null, period_low: null };
    }
    const close = bars[bars.length - 1].close;
    const highs = bars.map((b) => b.high);
    const lows = bars.map((b) => b.low);
    const periodHigh = Math.max(...highs);
    const periodLow = Math.min(...lows);
    const supports = [...new Set(lows.filter((l) => l < close))]
      .sort((a, b) => b - a)
      .slice(0, 2);
    const resistances = [...new Set(highs.filter((h) => h > close))]
      .sort((a, b) => a - b)
      .slice(0, 2);
    return { supports, resistances, period_high: periodHigh, period_low: periodLow };
  }

  function mount(container, options) {
    const allBars = options.bars || [];
    if (!allBars.length) return null;

    let period = Math.min(options.displayDays || 90, allBars.length);
    let probeEnabled = true;
    let hoverIndex = -1;
    let levels = options.levels || {};
    let resizeObserver = null;
    let cachedLayout = null;

    container.innerHTML = "";
    container.classList.add("chart-interactive");

    const toolbar = document.createElement("div");
    toolbar.className = "chart-toolbar";

    const hint = document.createElement("span");
    hint.className = "chart-hint";
    hint.textContent = "滑鼠移入圖表可查價（開高低收 · 均線 · KD · MACD）";

    const periodGroup = document.createElement("div");
    periodGroup.className = "chart-period-group";

    const probeBtn = document.createElement("button");
    probeBtn.type = "button";
    probeBtn.className = "chart-btn chart-btn-active";
    probeBtn.textContent = "查價：開";

    const probeBar = document.createElement("div");
    probeBar.className = "chart-probe-bar";

    const canvasWrap = document.createElement("div");
    canvasWrap.className = "chart-canvas-wrap";
    const canvas = document.createElement("canvas");
    canvas.className = "chart-canvas";
    canvasWrap.appendChild(canvas);

    container.appendChild(toolbar);
    toolbar.appendChild(hint);
    toolbar.appendChild(periodGroup);
    toolbar.appendChild(probeBtn);
    container.appendChild(probeBar);
    container.appendChild(canvasWrap);

    const periodBtns = {};
    PERIODS.forEach((d) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chart-btn";
      btn.textContent = `${d}日`;
      btn.addEventListener("click", () => setPeriod(d));
      periodGroup.appendChild(btn);
      periodBtns[d] = btn;
    });

    probeBtn.addEventListener("click", () => {
      probeEnabled = !probeEnabled;
      probeBtn.textContent = probeEnabled ? "查價：開" : "查價：關";
      probeBtn.classList.toggle("chart-btn-active", probeEnabled);
      if (!probeEnabled) hoverIndex = -1;
      draw();
      updateProbeBar(activeIndex());
    });

    function visibleBars() {
      const n = Math.min(period, allBars.length);
      return allBars.slice(-n);
    }

    function activeIndex() {
      const bars = visibleBars();
      if (!bars.length) return 0;
      if (hoverIndex >= 0 && hoverIndex < bars.length) return hoverIndex;
      return bars.length - 1;
    }

    function setPeriod(d) {
      period = Math.min(d, allBars.length);
      PERIODS.forEach((p) => {
        periodBtns[p].classList.toggle("chart-btn-active", p === period);
      });
      levels = quickLevels(visibleBars());
      hoverIndex = -1;
      draw();
      updateProbeBar(activeIndex());
    }

    function updateProbeBar(idx) {
      const bars = visibleBars();
      const row = bars[idx];
      if (!row) {
        probeBar.textContent = "";
        return;
      }
      const up = row.close >= row.open;
      const volColor = up ? UP : DOWN;
      const cols = [
        ["開盤", row.open, "MA5", row.MA5, MA_COLORS.MA5],
        ["最高", row.high, "MA10", row.MA10, MA_COLORS.MA10],
        ["最低", row.low, "MA20", row.MA20, MA_COLORS.MA20],
        ["收盤", row.close, "MA60", row.MA60, MA_COLORS.MA60],
      ];
      probeBar.innerHTML = `
        <span class="probe-date">${row.date}</span>
        <span class="probe-vol" style="color:${volColor}">成交量 ${fmtVol(row.volume)}</span>
        ${cols
          .map(
            ([ol, ov, mk, mv, c]) =>
              `<span class="probe-col"><b style="color:${c}">${ol} ${fmt(ov)}</b> <span style="color:${c}">${mk} ${fmt(mv)}</span></span>`
          )
          .join("")}
        <span class="probe-kd">K:${fmt(row.K, 1)} D:${fmt(row.D, 1)}${kdStatus(row.K, row.D)}</span>
        <span class="probe-macd">DIF:${fmt(row.DIF)} DEA:${fmt(row.DEA)} MACD:${fmt(row.MACD_hist)}</span>
      `;
    }

    function measureWidth() {
      const cw = canvasWrap.clientWidth;
      if (cw > 0) return cw;
      const panel = container.closest(".panel");
      if (panel && panel.clientWidth > 0) return panel.clientWidth - 40;
      return Math.min(window.innerWidth - 48, 960);
    }

    function layout() {
      const w = measureWidth();
      const h = Math.min(Math.round(w * 0.72), 560);
      const dpr = window.devicePixelRatio || 1;
      const pixelW = Math.round(w * dpr);
      const pixelH = Math.round(h * dpr);
      if (canvas.width !== pixelW || canvas.height !== pixelH) {
        canvas.width = pixelW;
        canvas.height = pixelH;
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;
      }

      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const padL = 52;
      const padR = 12;
      const padT = 8;
      const padB = 8;
      const plotW = w - padL - padR;
      const innerH = h - padT - padB;
      const ratios = [0.52, 0.16, 0.16, 0.16];
      const gaps = 6;
      const totalGap = gaps * 3;
      const usable = innerH - totalGap;
      let y = padT;
      const panels = ratios.map((r) => {
        const ph = usable * r;
        const rect = { x: padL, y, w: plotW, h: ph };
        y += ph + gaps;
        return rect;
      });
      cachedLayout = { ctx, w, h, padL, plotW, panels };
      return cachedLayout;
    }

    function yScale(min, max, top, height, val) {
      if (max === min) return top + height / 2;
      return top + height - ((val - min) / (max - min)) * height;
    }

    function drawHLine(ctx, y, x0, x1, color, dash) {
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      if (dash) ctx.setLineDash(dash);
      ctx.beginPath();
      ctx.moveTo(x0, y);
      ctx.lineTo(x1, y);
      ctx.stroke();
      ctx.restore();
    }

    function draw() {
      const bars = visibleBars();
      if (!bars.length) return;
      const { ctx, w, h, panels, padL, plotW } = layout();
      const idx = activeIndex();
      const crossX =
        probeEnabled && hoverIndex >= 0
          ? padL + (hoverIndex + 0.5) * (plotW / bars.length)
          : null;

      ctx.fillStyle = BG;
      ctx.fillRect(0, 0, w, h);

      const pricePanel = panels[0];
      const volPanel = panels[1];
      const kdPanel = panels[2];
      const macdPanel = panels[3];

      [pricePanel, volPanel, kdPanel, macdPanel].forEach((p) => {
        ctx.fillStyle = PANEL;
        ctx.fillRect(p.x - 4, p.y, p.w + 8, p.h);
      });

      const highs = bars.map((b) => b.high);
      const lows = bars.map((b) => b.low);
      let pMin = Math.min(...lows);
      let pMax = Math.max(...highs);
      (levels.supports || []).forEach((s) => {
        pMin = Math.min(pMin, s);
        pMax = Math.max(pMax, s);
      });
      (levels.resistances || []).forEach((r) => {
        pMin = Math.min(pMin, r);
        pMax = Math.max(pMax, r);
      });
      const pad = (pMax - pMin) * 0.04 || 1;
      pMin -= pad;
      pMax += pad;

      const barW = plotW / bars.length;
      const candleW = Math.max(1, barW * 0.6);

      bars.forEach((b, i) => {
        const cx = padL + (i + 0.5) * barW;
        const up = b.close >= b.open;
        const color = up ? UP : DOWN;
        const yHigh = yScale(pMin, pMax, pricePanel.y, pricePanel.h, b.high);
        const yLow = yScale(pMin, pMax, pricePanel.y, pricePanel.h, b.low);
        const yOpen = yScale(pMin, pMax, pricePanel.y, pricePanel.h, b.open);
        const yClose = yScale(pMin, pMax, pricePanel.y, pricePanel.h, b.close);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(cx, yHigh);
        ctx.lineTo(cx, yLow);
        ctx.stroke();
        const top = Math.min(yOpen, yClose);
        const bodyH = Math.max(1, Math.abs(yClose - yOpen));
        ctx.fillStyle = color;
        ctx.fillRect(cx - candleW / 2, top, candleW, bodyH);
      });

      ["MA5", "MA10", "MA20", "MA60"].forEach((key) => {
        ctx.strokeStyle = MA_COLORS[key];
        ctx.lineWidth = 1;
        ctx.beginPath();
        let started = false;
        bars.forEach((b, i) => {
          const v = b[key];
          if (v == null) return;
          const cx = padL + (i + 0.5) * barW;
          const cy = yScale(pMin, pMax, pricePanel.y, pricePanel.h, v);
          if (!started) {
            ctx.moveTo(cx, cy);
            started = true;
          } else ctx.lineTo(cx, cy);
        });
        ctx.stroke();
      });

      (levels.supports || []).forEach((s, i) => {
        const y = yScale(pMin, pMax, pricePanel.y, pricePanel.h, s);
        drawHLine(ctx, y, padL, padL + plotW, DOWN, [4, 3]);
        ctx.fillStyle = DOWN;
        ctx.font = "10px sans-serif";
        ctx.fillText(`支撐${i + 1} ${fmt(s)}`, padL + 2, y - 2);
      });
      (levels.resistances || []).forEach((r, i) => {
        const y = yScale(pMin, pMax, pricePanel.y, pricePanel.h, r);
        drawHLine(ctx, y, padL, padL + plotW, UP, [4, 3]);
        ctx.fillStyle = UP;
        ctx.font = "10px sans-serif";
        ctx.fillText(`壓力${i + 1} ${fmt(r)}`, padL + plotW - 72, y - 2);
      });

      const volMax = Math.max(...bars.map((b) => b.volume || 0), 1);
      bars.forEach((b, i) => {
        const cx = padL + (i + 0.5) * barW;
        const up = b.close >= b.open;
        const color = up ? UP : DOWN;
        const vh = ((b.volume || 0) / volMax) * volPanel.h;
        ctx.fillStyle = color;
        ctx.fillRect(cx - candleW / 2, volPanel.y + volPanel.h - vh, candleW, vh);
      });

      let kdMin = 0;
      let kdMax = 100;
      ["K", "D"].forEach((key) => {
        ctx.strokeStyle = key === "K" ? "#29b6f6" : "#ff9800";
        ctx.lineWidth = 1;
        ctx.beginPath();
        let started = false;
        bars.forEach((b, i) => {
          const v = b[key];
          if (v == null) return;
          const cx = padL + (i + 0.5) * barW;
          const cy = yScale(kdMin, kdMax, kdPanel.y, kdPanel.h, v);
          if (!started) {
            ctx.moveTo(cx, cy);
            started = true;
          } else ctx.lineTo(cx, cy);
        });
        ctx.stroke();
      });
      drawHLine(ctx, yScale(kdMin, kdMax, kdPanel.y, kdPanel.h, 80), padL, padL + plotW, GRID);
      drawHLine(ctx, yScale(kdMin, kdMax, kdPanel.y, kdPanel.h, 20), padL, padL + plotW, GRID);

      const macdVals = bars.flatMap((b) => [b.DIF, b.DEA, b.MACD_hist].filter((v) => v != null));
      let mMin = macdVals.length ? Math.min(...macdVals) : -1;
      let mMax = macdVals.length ? Math.max(...macdVals) : 1;
      if (mMin === mMax) {
        mMin -= 1;
        mMax += 1;
      }
      ["DIF", "DEA"].forEach((key, ki) => {
        ctx.strokeStyle = ki === 0 ? "#29b6f6" : "#ff9800";
        ctx.lineWidth = 1;
        ctx.beginPath();
        let started = false;
        bars.forEach((b, i) => {
          const v = b[key];
          if (v == null) return;
          const cx = padL + (i + 0.5) * barW;
          const cy = yScale(mMin, mMax, macdPanel.y, macdPanel.h, v);
          if (!started) {
            ctx.moveTo(cx, cy);
            started = true;
          } else ctx.lineTo(cx, cy);
        });
        ctx.stroke();
      });
      bars.forEach((b, i) => {
        const v = b.MACD_hist;
        if (v == null) return;
        const cx = padL + (i + 0.5) * barW;
        const zeroY = yScale(mMin, mMax, macdPanel.y, macdPanel.h, 0);
        const cy = yScale(mMin, mMax, macdPanel.y, macdPanel.h, v);
        ctx.fillStyle = v >= 0 ? UP : DOWN;
        const top = Math.min(zeroY, cy);
        ctx.fillRect(cx - candleW / 2, top, candleW, Math.max(1, Math.abs(cy - zeroY)));
      });

      ctx.fillStyle = TEXT;
      ctx.font = "10px sans-serif";
      ctx.fillText(fmt(pMax), 4, pricePanel.y + 10);
      ctx.fillText(fmt(pMin), 4, pricePanel.y + pricePanel.h);

      if (crossX != null) {
        ctx.strokeStyle = CROSS;
        ctx.lineWidth = 0.9;
        ctx.setLineDash([4, 4]);
        panels.forEach((p) => {
          ctx.beginPath();
          ctx.moveTo(crossX, p.y);
          ctx.lineTo(crossX, p.y + p.h);
          ctx.stroke();
        });
        ctx.setLineDash([]);
      }

      updateProbeBar(idx);
    }

    function indexFromEvent(clientX) {
      const bars = visibleBars();
      if (!cachedLayout || !bars.length) return -1;
      const { padL, plotW } = cachedLayout;
      const rect = canvas.getBoundingClientRect();
      const x = clientX - rect.left;
      if (x < padL || x > padL + plotW) return -1;
      const i = Math.floor(((x - padL) / plotW) * bars.length);
      return Math.max(0, Math.min(bars.length - 1, i));
    }

    function onMove(clientX) {
      if (!probeEnabled) return;
      const i = indexFromEvent(clientX);
      if (i < 0) return;
      if (i !== hoverIndex) {
        hoverIndex = i;
        draw();
      }
    }

    canvas.addEventListener("mousemove", (e) => onMove(e.clientX));
    canvas.addEventListener("mouseleave", () => {
      hoverIndex = -1;
      draw();
    });
    canvas.addEventListener(
      "touchmove",
      (e) => {
        if (!probeEnabled || !e.touches.length) return;
        e.preventDefault();
        onMove(e.touches[0].clientX);
      },
      { passive: false }
    );
    canvas.addEventListener("touchend", () => {
      hoverIndex = -1;
      draw();
    });

    setPeriod(period);

    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => draw());
      resizeObserver.observe(canvasWrap);
    } else {
      window.addEventListener("resize", draw);
    }

    return {
      redraw: draw,
      destroy() {
        if (resizeObserver) resizeObserver.disconnect();
        container.innerHTML = "";
      },
    };
  }

  window.StockInteractiveChart = { mount };
})();
