import { useEffect, useId, useRef, useState } from "react";
import { fetchSuggestions } from "./api";
import { useDebouncedValue } from "./useDebouncedValue";

export default function SearchBox({ value, onChange, onSubmit, busy }) {
  const listId = useId();
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const justPicked = useRef(false);
  const debounced = useDebouncedValue(value.trim(), 120);

  useEffect(() => {
    if (justPicked.current) {
      justPicked.current = false;
      return undefined;
    }
    if (!debounced) {
      setSuggestions([]);
      return undefined;
    }
    const controller = new AbortController();
    fetchSuggestions(debounced, controller.signal)
      .then((rows) => {
        setSuggestions(rows);
        setActive(-1);
        setOpen(rows.length > 0);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [debounced]);

  function pick(text) {
    justPicked.current = true;
    setOpen(false);
    setSuggestions([]);
    onChange(text);
    onSubmit(text);
  }

  function handleKeyDown(event) {
    if (!open || suggestions.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => (index + 1) % suggestions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => (index <= 0 ? suggestions.length - 1 : index - 1));
    } else if (event.key === "Enter" && active >= 0) {
      event.preventDefault();
      pick(suggestions[active].text);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  const expanded = open && suggestions.length > 0;
  return (
    <form
      className="search-form"
      role="search"
      onSubmit={(event) => {
        event.preventDefault();
        setOpen(false);
        onSubmit(value);
      }}
    >
      <div className="combo">
        <label className="sr-only" htmlFor="search-input">Search Steam games</label>
        <input
          id="search-input"
          value={value}
          onChange={(event) => {
            onChange(event.target.value);
            setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder="Try: space strategy"
          autoComplete="off"
          role="combobox"
          aria-expanded={expanded}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={expanded && active >= 0 ? `${listId}-${active}` : undefined}
        />
        {expanded && (
          <ul className="suggestions" id={listId} role="listbox" aria-label="Search suggestions">
            {suggestions.map((row, index) => (
              <li
                key={`${row.kind}-${row.text}`}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={index === active}
                className={index === active ? "active" : undefined}
                onMouseDown={(event) => {
                  event.preventDefault();
                  pick(row.text);
                }}
                onMouseEnter={() => setActive(index)}
              >
                <span>{row.text}</span>
                <small>{row.kind === "tag" ? "tag" : "game"}</small>
              </li>
            ))}
          </ul>
        )}
      </div>
      <button type="submit" disabled={busy}>{busy ? "Searching…" : "Search"}</button>
    </form>
  );
}
