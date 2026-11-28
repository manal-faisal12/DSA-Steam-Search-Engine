// Turns the contents of an uploaded file into a list of games for POST /games.

export const MAX_GAMES_PER_UPLOAD = 200;

const GAME_FIELDS = ["title", "description", "short_description", "release_year", "price", "genres", "tags", "id"];

function pickFields(raw) {
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    throw new Error("Each game must be a JSON object.");
  }
  const game = {};
  for (const key of GAME_FIELDS) {
    if (raw[key] !== undefined && raw[key] !== null && raw[key] !== "") game[key] = raw[key];
  }
  if (game.id !== undefined) game.id = String(game.id);
  if (typeof game.price === "string") game.price = Number.parseFloat(game.price) || 0;
  if (typeof game.release_year === "string") game.release_year = Number.parseInt(game.release_year, 10) || undefined;
  if (!game.title || !game.description) throw new Error("Every game needs a title and a description.");
  return game;
}

export function parseJsonUpload(text) {
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error("That file is not valid JSON.");
  }
  const list = Array.isArray(data) ? data : Array.isArray(data?.games) ? data.games : [data];
  if (list.length === 0) throw new Error("The file does not contain any games.");
  if (list.length > MAX_GAMES_PER_UPLOAD) throw new Error(`Upload at most ${MAX_GAMES_PER_UPLOAD} games at a time.`);
  return list.map(pickFields);
}

// Plain text: the first non-empty line is the title, everything after it is the description.
export function parseTextUpload(text, fileName = "") {
  const lines = text.replace(/\r/g, "").split("\n");
  const first = lines.findIndex((line) => line.trim() !== "");
  if (first === -1) throw new Error("The text file is empty.");
  const title = lines[first].trim();
  const description = lines.slice(first + 1).join(" ").replace(/\s+/g, " ").trim();
  if (!description) throw new Error(`"${fileName || "The text file"}" needs a title line followed by a description.`);
  return [{ title, description }];
}

export function parseUpload(fileName, text) {
  return fileName.toLowerCase().endsWith(".json") ? parseJsonUpload(text) : parseTextUpload(text, fileName);
}
