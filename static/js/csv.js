const rowsElement = document.querySelector("#csvRows");
const searchInput = document.querySelector("#csvSearch");
const recordCount = document.querySelector("#recordCount");
const pageLabel = document.querySelector("#pageLabel");
const previousButton = document.querySelector("#previousPage");
const nextButton = document.querySelector("#nextPage");
const emptyElement = document.querySelector("#csvEmpty");
const emptyMessage = document.querySelector("#csvEmptyMessage");
const pageSize = 50;
let records = [];
let currentPage = 0;

function cellValue(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

function formatPrice(value) {
  const amount = Number(value);
  const digits = Math.abs(amount) < 1 ? 8 : 2;
  return `$${amount.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

function formatMarketCap(value) {
  return `$${Number(value).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function renderTable() {
  const query = searchInput.value.trim().toLocaleLowerCase();
  const filtered = records.filter((record) =>
    `${record.name ?? ""} ${record.symbol ?? ""}`.toLocaleLowerCase().includes(query),
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  currentPage = Math.min(currentPage, pageCount - 1);
  const start = currentPage * pageSize;
  const visible = filtered.slice(start, start + pageSize);

  rowsElement.replaceChildren();
  visible.forEach((record) => {
    const row = document.createElement("tr");
    const values = [
      [record.timestamp, "timestamp-cell"],
      [record.rank, "number-cell numeric"],
      [record.name, "history-asset"],
      [record.symbol, "symbol-cell"],
      [formatPrice(record.price_usd), "number-cell numeric"],
      [`${Number(record.change_24h).toFixed(2)}%`, "number-cell numeric"],
      [formatMarketCap(record.market_cap_usd), "number-cell numeric"],
      [record.source, "source-cell"],
    ];

    values.forEach(([value, className]) => {
      const cell = document.createElement("td");
      cell.className = className;
      cell.textContent = cellValue(value);
      row.append(cell);
    });
    rowsElement.append(row);
  });

  recordCount.textContent = `${filtered.length.toLocaleString()} records`;
  pageLabel.textContent = `Page ${currentPage + 1} of ${pageCount}`;
  previousButton.disabled = currentPage === 0;
  nextButton.disabled = currentPage >= pageCount - 1;
  emptyElement.hidden = filtered.length > 0;
  emptyMessage.textContent = records.length
    ? "No records match this search."
    : "No CSV records have been saved yet.";
}

async function loadCsvRecords() {
  try {
    const response = await fetch("/api/history");
    if (!response.ok) throw new Error("Could not load CSV records.");
    const result = await response.json();
    records = (result.records || []).sort((left, right) => {
      const timestampOrder = String(right.timestamp).localeCompare(String(left.timestamp));
      return timestampOrder || Number(left.rank) - Number(right.rank);
    });
    renderTable();
  } catch (error) {
    recordCount.textContent = error.message;
    emptyElement.hidden = false;
    emptyMessage.textContent = error.message;
  }
}

searchInput.addEventListener("input", () => {
  currentPage = 0;
  renderTable();
});
previousButton.addEventListener("click", () => {
  currentPage -= 1;
  renderTable();
});
nextButton.addEventListener("click", () => {
  currentPage += 1;
  renderTable();
});

loadCsvRecords();
