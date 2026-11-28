import { useCallback, useEffect, useRef, useState } from "react";
import { PAGE_SIZE, searchGames } from "./api";
import Filters, { EMPTY_FILTERS, toApiFilters } from "./Filters";
import AddContent from "./AddContent";
import SearchBox from "./SearchBox";

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

function Pagination({ page, total, onPage }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Result pages">
      <button type="button" className="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
      <span>Page {page} of {pages}</span>
      <button type="button" className="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
    </nav>
  );
}

function Footer() {
  return (
    <footer className="site-footer">
      <p>
        Game data from the{" "}
        <a href="https://huggingface.co/datasets/FronkonGames/steam-games-dataset">Fronkon Games Steam Games Dataset</a>,
        licensed under{" "}
        <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
        Collected from the <a href="https://store.steampowered.com/">Steam Store API</a> and{" "}
        <a href="https://steamspy.com/">SteamSpy</a>.
      </p>
      <p>CS-250 Data Structures &amp; Algorithms · NUST SEECS · BESE-2025. Not affiliated with Valve or Steam.</p>
    </footer>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [submitted, setSubmitted] = useState("");
  const [search, setSearch] = useState({ status: "idle", results: [], total: 0, tookMs: 0, message: "" });
  const [view, setView] = useState("search");
  const resultsRef = useRef(null);

  useEffect(() => {
    if (!submitted) return undefined;
    const controller = new AbortController();
    setSearch((current) => ({ ...current, status: "loading", message: "" }));
    searchGames(submitted, { filters: toApiFilters(filters), page, signal: controller.signal })
      .then((payload) => setSearch({
        status: "success", results: payload.results, total: payload.total, tookMs: payload.took_ms, message: "",
      }))
      .catch((error) => {
        if (error.name === "AbortError") return;
        setSearch({ status: "error", results: [], total: 0, tookMs: 0, message: error.message });
      });
    return () => controller.abort();
  }, [submitted, filters, page]);

  const handleSubmit = useCallback((text) => {
    const trimmed = text.trim();
    if (!trimmed) {
      setSubmitted("");
      setSearch({ status: "error", results: [], total: 0, tookMs: 0, message: "Enter a game, genre, or keyword to search." });
      return;
    }
    setPage(1);
    setSubmitted(trimmed);
  }, []);

  function changePage(next) {
    setPage(next);
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function changeFilters(next) {
    setFilters(next);
    setPage(1);
  }

  const loading = search.status === "loading";
  return (
    <>
      <header className="top-nav">
        <nav aria-label="Main">
          <button type="button" className={view === "search" ? "tab current" : "tab"} aria-current={view === "search" ? "page" : undefined} onClick={() => setView("search")}>Search</button>
          <button type="button" className={view === "add" ? "tab current" : "tab"} aria-current={view === "add" ? "page" : undefined} onClick={() => setView("add")}>Add games</button>
        </nav>
      </header>
      <main className="page-shell">
        {view === "add" ? <AddContent /> : (<>
        <section className="hero" aria-labelledby="page-title">
          <p className="eyebrow">CS-250 · DSA Semester Project</p>
          <h1 id="page-title">Find your next Steam game</h1>
          <p>Search tens of thousands of Steam games by title, description, genre or tag.</p>
          <SearchBox value={query} onChange={setQuery} onSubmit={handleSubmit} busy={loading} />
          <Filters filters={filters} onChange={changeFilters} />
        </section>

        <section className="results" ref={resultsRef} aria-live="polite" aria-busy={loading}>
          {search.status === "idle" && <p className="hint">Results will appear here after you search.</p>}
          {loading && search.results.length === 0 && <p>Searching the catalogue…</p>}
          {search.status === "error" && <p className="error" role="alert">{search.message}</p>}
          {search.status === "success" && search.total === 0 && (
            <p>No games matched “{submitted}”. Try fewer words or clear the filters.</p>
          )}
          {search.status === "success" && search.total > 0 && (
            <p className="summary">
              {search.total.toLocaleString()} result{search.total === 1 ? "" : "s"} in {Math.round(search.tookMs)} ms
            </p>
          )}
          {search.results.map((game) => <GameCard game={game} key={game.id} />)}
          <Pagination page={page} total={search.total} onPage={changePage} />
        </section>
        </>)}
      </main>
      <Footer />
    </>
  );
}
