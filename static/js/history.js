const historyRows = document.querySelector("#historyRows");
const historyCount = document.querySelector("#historyCount");
const coinSelect = document.querySelector("#coinSelect");
const chartEmpty = document.querySelector("#chartEmpty");
const chartCanvas = document.querySelector("#trendChart");
let historyRecords = [];
let trendChart;

function formatPrice(value) {
  const amount = Number(value);
  return `$${amount.toLocaleString("en-US", {
    minimumFractionDigits: amount > 0 && amount < 1 ? 6 : 2,
    maximumFractionDigits: amount > 0 && amount < 1 ? 6 : 2,
  })}`;
}

function formatMarketCap(value) {
  return `$${Number(value).toLocaleString("en-US", { notation: "compact", maximumFractionDigits: 2 })}`;
}

function renderHistoryTable() {
  historyRows.replaceChildren();
  [...historyRecords].reverse().slice(0, 200).forEach((record) => {
    const row = document.createElement("tr");
    const fields = [
      [record.timestamp, "timestamp-cell"],
      [`${record.name} (${record.symbol})`, "history-asset"],
      [formatPrice(record.price_usd), "number-cell"],
      [`${Number(record.change_24h).toFixed(2)}%`, "number-cell"],
      [formatMarketCap(record.market_cap_usd), "number-cell"],
    ];
    fields.forEach(([value, className], index) => {
      const cell = document.createElement("td");
      cell.className = className;
      if (index > 1) cell.classList.add("numeric");
      cell.textContent = value;
      row.append(cell);
    });
    historyRows.append(row);
  });
  historyCount.textContent = `${historyRecords.length.toLocaleString()} records`;
}

function renderChart() {
  const selectedName = coinSelect.value;
  const records = historyRecords
    .filter((record) => record.name === selectedName)
    .sort((left, right) => String(left.timestamp).localeCompare(String(right.timestamp)));

  if (!records.length || typeof Chart === "undefined") {
    chartEmpty.hidden = false;
    chartCanvas.hidden = true;
    return;
  }

  chartEmpty.hidden = true;
  chartCanvas.hidden = false;
  const config = {
    type: "line",
    data: {
      labels: records.map((record) => record.timestamp),
      datasets: [{
        label: `${selectedName} (USD)`,
        data: records.map((record) => Number(record.price_usd)),
        borderColor: "#146c50",
        backgroundColor: "rgba(20, 108, 80, .10)",
        fill: true,
        tension: .24,
        pointRadius: records.length > 40 ? 0 : 3,
        pointHoverRadius: 5,
        borderWidth: 2,
      }],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (item) => formatPrice(item.raw) } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 7, maxRotation: 0 } },
        y: { grid: { color: "#e8eeea" }, ticks: { callback: (value) => formatPrice(value) } },
      },
    },
  };

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(chartCanvas, config);
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    if (!response.ok) throw new Error("History could not be loaded.");
    const result = await response.json();
    historyRecords = result.records || [];
    renderHistoryTable();

    const names = [...new Set(historyRecords.map((record) => record.name))];
    coinSelect.replaceChildren();
    names.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      coinSelect.append(option);
    });
    if (!names.length) {
      chartEmpty.hidden = false;
      chartCanvas.hidden = true;
      return;
    }
    coinSelect.addEventListener("change", renderChart);
    renderChart();
  } catch (error) {
    historyCount.textContent = error.message;
    chartEmpty.hidden = false;
    chartCanvas.hidden = true;
  }
}

loadHistory();
