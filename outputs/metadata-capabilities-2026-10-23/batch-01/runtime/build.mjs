// Use the bundled @oai/artifact-tool runtime. Input is the read-only audit JSON.
import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const output = path.resolve(process.argv[2]);
const layouts = JSON.parse(await fs.readFile(path.join(output, 'compatibility-layouts.json'), 'utf8'));
const exportDir = path.join(output, 'candidates');
await fs.mkdir(exportDir, { recursive: true });
const manifests = [];
for (const layout of layouts) {
  const workbook = Workbook.create();
  // Put the explicit review gate first. Data headers stay on row 1 for adapters.
  const sheets = [...layout.sheets.filter(s => s.name === 'Capabilities'), ...layout.sheets.filter(s => s.name !== 'Capabilities')];
  for (const data of sheets) {
    const sheet = workbook.worksheets.add(data.name);
    const matrix = [data.columns, ...data.rows.map(row => data.columns.map(key => row[key] ?? null))];
    sheet.getRangeByIndexes(0, 0, matrix.length, data.columns.length).values = matrix;
    const used = sheet.getRangeByIndexes(0, 0, matrix.length, data.columns.length);
    used.format.font = { name: 'Calibri', size: 11 };
    used.format.columnWidth = 22;
    sheet.getRangeByIndexes(0, 0, 1, data.columns.length).format = {
      fill: '#1F4E78', font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 44,
    };
    sheet.freezePanes.freezeRows(1);
    if (data.name === 'Capabilities') {
      used.format.columnWidth = 40;
      used.format.wrapText = true;
      used.format.rowHeight = 60;
    }
    if (data.name.endsWith('Brackets')) {
      // Long provenance is preserved as cell values; do not widen the whole sheet.
      sheet.getRangeByIndexes(1, 0, Math.max(1,matrix.length-1), 1).setNumberFormat('0.000000');
    }
  }
  workbook.recalculate();
  const file = path.join(exportDir, layout.filename);
  await (await SpreadsheetFile.exportXlsx(workbook)).save(file);
  const preview = await workbook.render({ sheetName: 'Capabilities', range: 'A1:D2', scale: 1, format: 'png' });
  await fs.writeFile(path.join(output, layout.filename.replace('.xlsx','.png')), new Uint8Array(await preview.arrayBuffer()));
  manifests.push({file, status:'review-only; unavailable intervals stay blank', sheets:sheets.map(s=>({name:s.name,rows:s.rows.length}))});
}
await fs.writeFile(path.join(output,'workbook-build-manifest.json'),JSON.stringify(manifests,null,2));
console.log(JSON.stringify({workbooks:manifests.length,output:exportDir}));
