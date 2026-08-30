import test from "node:test";
import assert from "node:assert";

// Pure formatting logic testing
function formatDuration(minutes) {
  if (!minutes || minutes <= 0) return "N/A";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}min`;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatDate(dateStr) {
  if (!dateStr) return "N/A";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const MAX_ACTIVE_SUBSCRIPTIONS = 10;

function canAddActiveSubscription(currentActiveCount) {
  return currentActiveCount < MAX_ACTIVE_SUBSCRIPTIONS;
}

test("formatDuration handles exact hours and combinations", () => {
  assert.strictEqual(formatDuration(60), "1h");
  assert.strictEqual(formatDuration(120), "2h");
  assert.strictEqual(formatDuration(135), "2h 15m");
  assert.strictEqual(formatDuration(45), "45min");
  assert.strictEqual(formatDuration(0), "N/A");
  assert.strictEqual(formatDuration(-10), "N/A");
});

test("formatDate formats ISO dates gracefully", () => {
  const formatted = formatDate("2026-08-28");
  assert.match(formatted, /28.*Aug.*2026/i);
  assert.strictEqual(formatDate(""), "N/A");
  assert.strictEqual(formatDate(null), "N/A");
});

test("Safety Net: Maximum 10 active tasks limit rule", () => {
  assert.strictEqual(canAddActiveSubscription(0), true);
  assert.strictEqual(canAddActiveSubscription(9), true);
  assert.strictEqual(canAddActiveSubscription(10), false);
  assert.strictEqual(canAddActiveSubscription(15), false);
});

test("Admin Scraper duration and status message formatting", () => {
  const formatScrapeResult = (durationMs, flushedCount) => {
    const durationSec = durationMs ? ` in ${(durationMs / 1000).toFixed(1)}s` : "";
    const cacheNote = flushedCount !== undefined ? ` (${flushedCount} cache keys cleared)` : "";
    return `✓ Catalog refetch completed successfully${durationSec}!${cacheNote}`;
  };

  assert.strictEqual(
    formatScrapeResult(3500, 12),
    "✓ Catalog refetch completed successfully in 3.5s! (12 cache keys cleared)"
  );
  assert.strictEqual(
    formatScrapeResult(null, undefined),
    "✓ Catalog refetch completed successfully!"
  );
});

