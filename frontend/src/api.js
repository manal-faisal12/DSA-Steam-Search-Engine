const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export const PAGE_SIZE = 10;

async function getJson(path, params, signal, failureMessage) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}?${params}`, { signal });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Cannot reach the search server. Please try again shortly.");
  }
  if (!response.ok) throw new Error(failureMessage);
  return response.json();
}

export function searchGames(query, { filters = {}, page = 1, signal } = {}) {
  const params = new URLSearchParams({
    query,
    limit: String(PAGE_SIZE),
    offset: String((page - 1) * PAGE_SIZE),
  });
  for (const [key, value] of Object.entries(filters)) {
    if (value !== "" && value !== null && value !== undefined) params.set(key, String(value));
  }
  return getJson("/search", params, signal, "Search is unavailable. Please try again shortly.");
}

export async function fetchSuggestions(prefix, signal) {
  const params = new URLSearchParams({ q: prefix, limit: "5" });
  const payload = await getJson("/suggest", params, signal, "Suggestions are unavailable.");
  return payload.suggestions;
}
