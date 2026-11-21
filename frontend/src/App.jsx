import { useState } from "react";
import { searchGames } from "./api";

function GameCard({ game }) {
  const metadata = [
    game.release_year ? String(game.release_year) : null,
    game.price === 0 ? "Free to play" : `$${game.price.toFixed(2)}`,
  ].filter(Boolean);

  return (
    <article className="game-card">
      <h2>{game.title}</h2>
      <p className="game-meta">{metadata.join(" · ")}</p>
      <p>{game.short_description || "No short description available."}</p>
      {game.genres.length > 0 && <p className="tags">{game.genres.join(" · ")}</p>}
    </article>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState({ status: "idle", results: [], message: "" });

  async function handleSubmit(event) {
    event.preventDefault();
    const submittedQuery = query.trim();
    if (!submittedQuery) {
      setSearch({ status: "error", results: [], message: "Enter a game, genre, or keyword to search." });
      return;
    }
    setSearch({ status: "loading", results: [], message: "" });
    try {
      const payload = await searchGames(submittedQuery);
      setSearch({ status: "success", results: payload.results, message: "" });
    } catch (error) {
      setSearch({ status: "error", results: [], message: error.message });
    }
  }

  return (
    <main className="page-shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">CS-250 · DSA Semester Project</p>
        <h1 id="page-title">Find your next Steam game</h1>
        <p>Search the project’s cleaned Steam catalogue by title or keywords.</p>
        <form className="search-form" onSubmit={handleSubmit} role="search">
          <label className="sr-only" htmlFor="search-input">Search Steam games</label>
          <input
            id="search-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Try: space strategy"
            autoComplete="off"
          />
          <button type="submit" disabled={search.status === "loading"}>
            {search.status === "loading" ? "Searching…" : "Search"}
          </button>
        </form>
      </section>

      <section className="results" aria-live="polite" aria-busy={search.status === "loading"}>
        {search.status === "idle" && <p className="hint">Results will appear here after you search.</p>}
        {search.status === "loading" && <p>Searching the catalogue…</p>}
        {search.status === "error" && <p className="error" role="alert">{search.message}</p>}
        {search.status === "success" && search.results.length === 0 && <p>No games matched that search.</p>}
        {search.status === "success" && search.results.map((game) => <GameCard game={game} key={game.id} />)}
      </section>
    </main>
  );
}
