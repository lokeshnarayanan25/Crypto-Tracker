const rowsElement = document.querySelector("#coinRows");
const emptyElement = document.querySelector("#emptyState");
const emptyMessage = document.querySelector("#emptyMessage");
const statusText = document.querySelector("#statusText");
const statusIndicator = document.querySelector("#statusIndicator");
const updatedTime = document.querySelector("#updatedTime");
const resultCount = document.querySelector("#resultCount");
const refreshButton = document.querySelector("#refreshButton");
const minimumPrice = document.querySelector("#minimumPrice");
const maximumPrice = document.querySelector("#maximumPrice");
const gainersButton = document.querySelector("#gainersButton");

let coins = [];
let showGainers = false;
let refreshBusy = false;
let lastAutomaticRefresh = 0;

function formatPrice(value) {
  const amount = Number(value);
  const digits = amount > 0 && amount < 1 ? 6 : 2;
  return `$${amount.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

function formatMarketCap(value) {
  const amount = Number(value);
  return `$${amount.toLocaleString("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  })}`;
}

function addCell(row, text, className, title = "") {
  const cell = document.createElement("td");
  cell.className = className;
  cell.textContent = text;
  if (title) cell.title = title;
  row.append(cell);
  return cell;
}

function renderRows() {
  let visible = [...coins];
  const min = minimumPrice.value === "" ? null : Number(minimumPrice.value);
  const max = maximumPrice.value === "" ? null : Number(maximumPrice.value);

  if (min !== null) visible = visible.filter((coin) => Number(coin.price_usd) >= min);
  if (max !== null) visible = visible.filter((coin) => Number(coin.price_usd) <= max);
  if (showGainers) visible.sort((left, right) => Number(right.change_24h) - Number(left.change_24h));

  rowsElement.replaceChildren();
  visible.forEach((coin, index) => {
    const row = document.createElement("tr");
    row.style.animationDelay = `${Math.min(index * 25, 200)}ms`;
    addCell(row, String(coin.rank ?? index + 1), "rank-cell");

    const asset = document.createElement("td");
    asset.className = "asset-cell";
    const name = document.createElement("span");
    name.className = "asset-name";
    name.textContent = coin.name ?? "Unknown";
    const symbol = document.createElement("span");
    symbol.className = "asset-symbol";
    symbol.textContent = coin.symbol ?? "";
    asset.append(name, symbol);
    row.append(asset);

    addCell(row, formatPrice(coin.price_usd), "number-cell");
    const change = Number(coin.change_24h);
    addCell(
      row,
      `${change > 0 ? "+" : ""}${change.toFixed(2)}%`,
      `number-cell ${change >= 0 ? "change-positive" : "change-negative"}`,
    );
    addCell(
      row,
      formatMarketCap(coin.market_cap_usd),
      "number-cell",
      `$${Number(coin.market_cap_usd).toLocaleString("en-US", { maximumFractionDigits: 0 })}`,
    );
    rowsElement.append(row);
  });

  resultCount.textContent = `${visible.length} ${visible.length === 1 ? "coin" : "coins"}`;
  emptyElement.hidden = visible.length > 0;
  if (!visible.length && coins.length) emptyMessage.textContent = "No coins match these filters";
  else if (!visible.length) emptyMessage.textContent = "No saved prices yet. Refresh to try again.";
}

function updateState(state) {
  coins = Array.isArray(state.coins) ? state.coins : [];
  renderRows();
  updatedTime.textContent = state.updated || "--";
  statusIndicator.classList.toggle("is-live", coins.length > 0 && !state.error && !state.cached);
  statusIndicator.classList.toggle("is-error", Boolean(state.error));

  if (state.loading) statusText.textContent = "Refreshing market data";
  else if (state.error && coins.length) statusText.textContent = "Refresh failed; showing last saved snapshot";
  else if (state.error) statusText.textContent = state.error;
  else if (state.cached) statusText.textContent = "Showing last saved snapshot";
  else if (coins.length) statusText.textContent = "Market data loaded";
  else statusText.textContent = "Waiting for market data";
}

async function getState() {
  const response = await fetch("/api/prices");
  if (!response.ok) throw new Error("Could not load market data.");
  const state = await response.json();
  updateState(state);
  return state;
}

function updateRefreshButton() {
  refreshButton.disabled = false;
  refreshButton.classList.toggle("is-loading", refreshBusy);
}

async function refreshPrices(manual = false) {
  if (!manual && (refreshBusy || Date.now() - lastAutomaticRefresh < 10000)) return;

  if (!manual) lastAutomaticRefresh = Date.now();
  if (refreshBusy && manual) {
    try {
      const response = await fetch("/api/refresh?manual=1", { method: "POST" });
      const state = await response.json();
      statusText.textContent = state.queued_refresh
        ? "Manual refresh queued; it will run next"
        : state.refresh_started
          ? "Manual refresh started"
          : "A refresh is already running";
    } catch (error) {
      statusText.textContent = error.message;
    }
    return;
  }

  refreshBusy = true;
  updateRefreshButton();

  try {
    const url = manual ? "/api/refresh?manual=1" : "/api/refresh";
    const response = await fetch(url, { method: "POST" });
    if (!response.ok) throw new Error("Could not start a refresh.");
    let state = await response.json();
    updateState(state);
    if (!state.refresh_started && !state.loading && !state.queued_refresh) return;
    while (state.loading) {
      await new Promise((resolve) => setTimeout(resolve, 10000));
      state = await getState();
    }
  } catch (error) {
    statusText.textContent = error.message;
    statusIndicator.classList.add("is-error");
  } finally {
    refreshBusy = false;
    updateRefreshButton();
  }
}

refreshButton.addEventListener("click", () => refreshPrices(true));
document.querySelector("#applyPriceFilter").addEventListener("click", () => {
  showGainers = false;
  gainersButton.setAttribute("aria-pressed", "false");
  renderRows();
});
gainersButton.setAttribute("aria-pressed", "false");
gainersButton.addEventListener("click", () => {
  showGainers = !showGainers;
  gainersButton.setAttribute("aria-pressed", String(showGainers));
  renderRows();
});
document.querySelector("#clearFilters").addEventListener("click", () => {
  minimumPrice.value = "";
  maximumPrice.value = "";
  showGainers = false;
  gainersButton.setAttribute("aria-pressed", "false");
  renderRows();
});

getState()
  .then(() => refreshPrices())
  .catch(() => {
    statusText.textContent = "Could not reach the local tracker server.";
    statusIndicator.classList.add("is-error");
  });

window.setInterval(() => {
  if (!document.hidden) refreshPrices();
}, 10000);
