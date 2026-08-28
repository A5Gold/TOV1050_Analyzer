import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const frontendRequire = createRequire(path.resolve("frontend/package.json"));
const XLSX = frontendRequire("xlsx");

const SOURCE_DIR = "docs/1 year database record";
const OUTPUT_DIR = "config/database-records";
const SOURCE_FILES = [
  { line: "EAL", source: "2025-2026 EAL Exception Database Record.xlsx", output: "EAL-1-year-database-record.xlsx", excludedSheets: new Set() },
  { line: "TML", source: "2025-2026 TML Exception Database Record.xlsx", output: "TML-1-year-database-record.xlsx", excludedSheets: new Set(["Sheet1"]) },
];
const HEADER_MAP = new Map([
  ["RUN DATE", "Run Date"], ["LINE", "Line"], ["TRACK", "Track"], ["SECTION", "Section"],
  ["TASK NO", "Task Number"], ["STATION START", "Station Start"], ["STATION END", "Station End"],
  ["ID", "ID"], ["FromM", "FromM"], ["ToM", "ToM"], ["Length", "Length"],
  ["Exception Type", "Exception Type"], ["MaxValue", "MaxValue"], ["MaxLocation", "MaxLocation"],
  ["Overlap", "Overlap"], ["Tension Length", "Tension Length"], ["Track Type", "Track Type"],
  ["Level", "Level"], ["Previous 1", "Previous 1"], ["Previous 2", "Previous 2"],
  ["Reoccurrence ID", "Reoccurrence ID"], ["Remarks", "Remarks"], ["ACTION", "ACTION"],
  ["CHECK DATE", "CHECK DATE"], ["CHECKED BY", "CHECKED BY"], ["CHECK RESULT", "CHECK RESULT"],
  ["VERIFY DEADLINE", "VERIFY DEADLINE"], ["VERIFY DATE", "VERIFY DATE"],
  ["VERIFY RESULT", "VERIFY RESULT"], ["VERIFIED BY", "VERIFIED BY"],
  ["ADJUST DEADLINE", "ADJUST DEADLINE"], ["ADJUST DATE", "ADJUST DATE"],
  ["ADJUST RESULT", "ADJUST RESULT"], ["ADJUSTED BY", "ADJUSTED BY"],
]);
const HEADERS = [...HEADER_MAP.values()];
const DATE_HEADERS = new Set(["Run Date", "CHECK DATE", "VERIFY DEADLINE", "VERIFY DATE", "ADJUST DEADLINE", "ADJUST DATE"]);
const CONFLICT_ID = "20250814_TML_TUM-HUH_DN_SL74";
const MISSING_LOCATION_ID = "20251127_TML_TUM-KSR_DN_SL37";

function compactDate(value) {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) {
    // SheetJS may represent an Excel date-only cell a few seconds before
    // local midnight. Shift to UTC noon before extracting the calendar day.
    return new Date(value.getTime() + 12 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10)
      .replaceAll("-", "");
  }
  if (typeof value === "number" && value >= 30000 && value <= 80000) {
    const date = new Date(Date.UTC(1899, 11, 30) + Math.round(value) * 86400000);
    return date.toISOString().slice(0, 10).replaceAll("-", "");
  }
  const text = String(value).trim();
  const compact = text.replaceAll("-", "").replaceAll("/", "");
  return /^\d{8}$/.test(compact) ? compact : text;
}

function normalizedValue(header, value) {
  if (value === null || value === undefined || value === "") return null;
  if (DATE_HEADERS.has(header) || value instanceof Date) return compactDate(value);
  return typeof value === "string" ? value.trim() : value;
}

function businessKey(record) {
  return [record.ID, record.Line, record.Track, record["Run Date"]].join("|");
}

function comparableRecord(record) {
  return JSON.stringify(HEADERS.map((header) => record[header] ?? null));
}

function nonEmptyCount(record) {
  return HEADERS.filter((header) => record[header] !== null && record[header] !== "").length;
}

async function readSources() {
  const records = [];
  const sourceHashes = {};
  for (const source of SOURCE_FILES) {
    const sourcePath = path.join(SOURCE_DIR, source.source);
    const bytes = await fs.readFile(sourcePath);
    sourceHashes[source.source] = crypto.createHash("sha256").update(bytes).digest("hex");
    const workbook = XLSX.read(bytes, { type: "buffer", cellDates: true, raw: true });
    for (const sheetName of workbook.SheetNames) {
      if (source.excludedSheets.has(sheetName)) continue;
      const values = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], {
        header: 1,
        defval: null,
        raw: true,
      });
      if (values.length < 3) continue;
      const sourceHeaders = values[1].map((value) => String(value ?? "").trim());
      for (let rowIndex = 2; rowIndex < values.length; rowIndex += 1) {
        const row = values[rowIndex];
        if (!row.some((value) => value !== null && value !== "")) continue;
        const record = Object.fromEntries(HEADERS.map((header) => [header, null]));
        sourceHeaders.forEach((sourceHeader, columnIndex) => {
          const header = HEADER_MAP.get(sourceHeader);
          if (header) record[header] = normalizedValue(header, row[columnIndex]);
        });
        records.push({ ...record, _source: { file: source.source, sheet: sheetName, row: rowIndex + 1 } });
      }
    }
  }
  return { records, sourceHashes };
}

function cleanRecords(records) {
  const groups = new Map();
  for (const record of records) {
    const key = businessKey(record);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(record);
  }
  const kept = [];
  const exclusions = [];
  for (const [key, group] of groups) {
    if (group[0].ID === CONFLICT_ID) {
      exclusions.push({ rule: "conflicting_duplicate_key", key, excluded_count: group.length, conflict_field: "Overlap", values: group.map((record) => record.Overlap), sources: group.map((record) => record._source) });
      continue;
    }
    if (group[0].ID === MISSING_LOCATION_ID) {
      exclusions.push({ rule: "missing_max_location", key, excluded_count: group.length, sources: group.map((record) => record._source) });
      continue;
    }
    if (group.length === 1) {
      kept.push(group[0]);
      continue;
    }
    const unique = new Set(group.map(comparableRecord));
    const sorted = [...group].sort((left, right) => nonEmptyCount(right) - nonEmptyCount(left));
    kept.push(sorted[0]);
    exclusions.push({
      rule: unique.size === 1 ? "exact_duplicate" : "prefer_more_complete_duplicate",
      key,
      excluded_count: group.length - 1,
      kept_source: sorted[0]._source,
      excluded_sources: sorted.slice(1).map((record) => record._source),
      non_empty_counts: sorted.map(nonEmptyCount),
    });
  }
  kept.sort((left, right) => left.Line.localeCompare(right.Line) || left["Run Date"].localeCompare(right["Run Date"]) || left.Track.localeCompare(right.Track) || left.ID.localeCompare(right.ID));
  return { kept, exclusions };
}

async function writeWorkbook(line, records, outputPath) {
  const matrix = [HEADERS, ...records.map((record) => HEADERS.map((header) => record[header] ?? null))];
  const sheet = XLSX.utils.aoa_to_sheet(matrix, { cellDates: false });
  const widths = [12, 9, 9, 12, 12, 15, 15, 39, 12, 12, 11, 18, 12, 14, 12, 18, 14, 9, 26, 26, 28, 28, 36, 13, 14, 15, 16, 13, 16, 14, 16, 13, 16, 14];
  sheet["!cols"] = widths.map((wch) => ({ wch }));
  sheet["!autofilter"] = { ref: "A1:AH" + matrix.length };
  const workbook = XLSX.utils.book_new();
  workbook.Props = { Title: line + " 1 Year Database Records", Author: "TOV640 Analyzer" };
  XLSX.utils.book_append_sheet(workbook, sheet, "Database Records");
  XLSX.writeFile(workbook, outputPath, { compression: true });
}

await fs.mkdir(OUTPUT_DIR, { recursive: true });
const sourceData = await readSources();
const cleaned = cleanRecords(sourceData.records);
if (sourceData.records.length !== 2715 || cleaned.kept.length !== 2706) {
  throw new Error("Unexpected record counts: source=" + sourceData.records.length + ", kept=" + cleaned.kept.length);
}
if (cleaned.kept.some((record) => !record.ID || record.MaxLocation === null || !record.Line || !record.Track || !record.Section || !/^\d{8}$/.test(record["Run Date"]))) {
  throw new Error("Cleaned records contain missing matching fields");
}
const outputHashes = {};
for (const source of SOURCE_FILES) {
  const lineRecords = cleaned.kept.filter((record) => record.Line === source.line);
  const outputPath = path.join(OUTPUT_DIR, source.output);
  await writeWorkbook(source.line, lineRecords, outputPath);
  outputHashes[source.output] = crypto.createHash("sha256").update(await fs.readFile(outputPath)).digest("hex");
  await fs.rm(outputPath + ".inspect.ndjson", { force: true });
}
const report = {
  schema: "database-record-seed-quality-v1",
  seed_version: "2025-2026-v1",
  source_record_count: sourceData.records.length,
  retained_record_count: cleaned.kept.length,
  retained_by_line: Object.fromEntries(SOURCE_FILES.map(({ line }) => [line, cleaned.kept.filter((record) => record.Line === line).length])),
  excluded_record_count: sourceData.records.length - cleaned.kept.length,
  source_sha256: sourceData.sourceHashes,
  output_sha256: outputHashes,
  rules: [
    "Remove normalized exact duplicates by ID + Line + Track + Run Date.",
    "For non-conflicting duplicate keys, retain the row with the most populated import fields.",
    "Exclude both " + CONFLICT_ID + " rows because Overlap values conflict.",
    "Exclude " + MISSING_LOCATION_ID + " because MaxLocation is blank.",
    "Convert Excel date-formatted cells in any field to YYYYMMDD text without moving columns.",
  ],
  exclusions: cleaned.exclusions,
};
await fs.writeFile(path.join(OUTPUT_DIR, "database-record-seed-quality.json"), JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({ retained: cleaned.kept.length, byLine: report.retained_by_line, exclusions: report.excluded_record_count }, null, 2));
