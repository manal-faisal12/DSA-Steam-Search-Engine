const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function searchGames(query) {
  const params = new URLSearchParams({ query, limit: "10" });
  const response = await fetch(`${API_BASE_URL}/search?${params}`);
  if (!response.ok) {
    throw new Error("Search is unavailable. Please try again shortly.");
  }
  return response.json();
}
