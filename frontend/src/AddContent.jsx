import { useEffect, useRef, useState } from "react";
import { addGames, getJob } from "./api";
import { parseUpload } from "./parseUpload";

const EMPTY_FORM = { title: "", description: "", genres: "", price: "", releaseYear: "" };
const splitList = (text) => text.split(",").map((item) => item.trim()).filter(Boolean);

export default function AddContent() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [state, setState] = useState({ phase: "idle", message: "" });
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  function pollJob(jobId, count) {
    getJob(jobId)
      .then((job) => {
        if (job.status === "done") {
          setState({ phase: "done", message: `Added ${job.added} game${job.added === 1 ? "" : "s"}. ${job.added === 1 ? "It is" : "They are"} searchable now.` });
        } else if (job.status === "error") {
          setState({ phase: "error", message: job.error || "Indexing failed." });
        } else {
          timer.current = setTimeout(() => pollJob(jobId, count), 800);
        }
      })
      .catch((error) => setState({ phase: "error", message: error.message }));
  }

  async function submit(games) {
    setState({ phase: "working", message: "Indexing…" });
    try {
      const job = await addGames(games);
      pollJob(job.job_id, games.length);
      return true;
    } catch (error) {
      setState({ phase: "error", message: error.message });
      return false;
    }
  }

  function handleManual(event) {
    event.preventDefault();
    const game = { title: form.title.trim(), description: form.description.trim() };
    if (!game.title || !game.description) {
      setState({ phase: "error", message: "Please enter a title and a description." });
      return;
    }
    if (form.genres.trim()) game.genres = splitList(form.genres);
    if (form.price !== "") game.price = Number(form.price);
    if (form.releaseYear !== "") game.release_year = Number(form.releaseYear);
    submit([game]).then((queued) => queued && setForm(EMPTY_FORM));
  }

  async function handleFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      submit(parseUpload(file.name, await file.text()));
    } catch (error) {
      setState({ phase: "error", message: error.message });
    }
  }

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const working = state.phase === "working";
  return (
    <section className="add-content" aria-labelledby="add-title">
      <h2 id="add-title">Add games to the index</h2>
      <p className="hint">New games become searchable within seconds, without interrupting searches.</p>

      <form onSubmit={handleManual} className="add-form">
        <label>Title<input value={form.title} onChange={set("title")} maxLength={200} required /></label>
        <label>Description<textarea value={form.description} onChange={set("description")} rows={5} required /></label>
        <div className="row">
          <label>Genres (comma separated)<input value={form.genres} onChange={set("genres")} placeholder="Strategy, Indie" /></label>
          <label>Price (USD)<input type="number" min="0" step="0.01" value={form.price} onChange={set("price")} /></label>
          <label>Release year<input type="number" min="1970" max="2100" value={form.releaseYear} onChange={set("releaseYear")} /></label>
        </div>
        <button type="submit" disabled={working}>Add game</button>
      </form>

      <div className="upload">
        <label className="file-button">
          Upload a JSON or text file
          <input type="file" accept=".json,.txt,text/plain,application/json" onChange={handleFile} disabled={working} />
        </label>
        <p className="hint">
          JSON: one game object or a list of up to 200 (fields: title, description, genres, tags, price, release_year).
          Text: first line is the title, the rest is the description.
        </p>
      </div>

      <p className={state.phase === "error" ? "error" : "status"} role={state.phase === "error" ? "alert" : "status"}>
        {state.message}
      </p>
    </section>
  );
}
