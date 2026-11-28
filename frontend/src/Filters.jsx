export const GENRES = [
  "Action", "Adventure", "Casual", "Indie", "Massively Multiplayer", "Racing",
  "RPG", "Simulation", "Sports", "Strategy", "Free To Play", "Early Access",
];

export const PRICE_OPTIONS = [
  { value: "any", label: "Any price", filters: {} },
  { value: "free", label: "Free", filters: { max_price: 0 } },
  { value: "u10", label: "Under $10", filters: { max_price: 10 } },
  { value: "u20", label: "Under $20", filters: { max_price: 20 } },
  { value: "o20", label: "Over $20", filters: { min_price: 20 } },
];

const FIRST_YEAR = 2006;
const LAST_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: LAST_YEAR - FIRST_YEAR + 1 }, (_, i) => LAST_YEAR - i);

export const EMPTY_FILTERS = { genre: "", price: "any", yearFrom: "", yearTo: "" };

export function toApiFilters(filters) {
  const price = PRICE_OPTIONS.find((option) => option.value === filters.price)?.filters ?? {};
  return {
    genre: filters.genre,
    ...price,
    year_from: filters.yearFrom,
    year_to: filters.yearTo,
  };
}

export function hasActiveFilters(filters) {
  return Object.keys(EMPTY_FILTERS).some((key) => filters[key] !== EMPTY_FILTERS[key]);
}

export default function Filters({ filters, onChange }) {
  const set = (key) => (event) => onChange({ ...filters, [key]: event.target.value });
  return (
    <fieldset className="filters">
      <legend>Filter results</legend>
      <label>
        Genre
        <select value={filters.genre} onChange={set("genre")}>
          <option value="">All genres</option>
          {GENRES.map((genre) => <option key={genre} value={genre}>{genre}</option>)}
        </select>
      </label>
      <label>
        Price
        <select value={filters.price} onChange={set("price")}>
          {PRICE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </label>
      <label>
        Released from
        <select value={filters.yearFrom} onChange={set("yearFrom")}>
          <option value="">Any year</option>
          {YEARS.map((year) => <option key={year} value={year}>{year}</option>)}
        </select>
      </label>
      <label>
        Released to
        <select value={filters.yearTo} onChange={set("yearTo")}>
          <option value="">Any year</option>
          {YEARS.map((year) => <option key={year} value={year}>{year}</option>)}
        </select>
      </label>
      {hasActiveFilters(filters) && (
        <button type="button" className="secondary" onClick={() => onChange(EMPTY_FILTERS)}>Clear filters</button>
      )}
    </fieldset>
  );
}
