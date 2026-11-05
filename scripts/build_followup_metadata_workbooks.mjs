// Review-only workbook authoring. Use the bundled artifact-tool runtime.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';

const output = path.resolve(process.argv[2]);
// Resolve from the output's junction to the bundled runtime, never repo deps.
const bundledRequire = createRequire(path.join(output, 'artifact-runtime.cjs'));
const {Workbook, SpreadsheetFile} = await import(pathToFileURL(bundledRequire.resolve('@oai/artifact-tool')).href);
const layouts = JSON.parse(await fs.readFile(path.join(output, 'workbook-layouts.json'), 'utf8'));
const exportDir = path.join(output, 'candidates');
await fs.mkdir(exportDir, {recursive: true});
const manifests = [];
function sourceRowRanges(values) {
  const sorted = [...new Set(values)].sort((a,b)=>a-b);
  const ranges = [];
  for(let i=0;i<sorted.length;i++) {
    const start=sorted[i]; let end=start;
    while(i+1<sorted.length && sorted[i+1]===end+1) end=sorted[++i];
    ranges.push(start===end?String(start):`${start}-${end}`);
  }
  return ranges.join(', ');
}
for (const layout of layouts) {
  const wb = Workbook.create();
  for (const data of layout.sheets) {
    const sheet = wb.worksheets.add(data.name);
    const matrix = data.matrix.map((row,ri) => row.map((v,ci) =>
      ri>0 && data.matrix[0][ci]==='source_excel_rows' && Array.isArray(v) ? sourceRowRanges(v)
      : typeof v === 'object' && v !== null ? JSON.stringify(v) : v ?? null));
    const cols = Math.max(...matrix.map(r => r.length));
    const padded = matrix.map(r => [...r, ...Array(cols-r.length).fill(null)]);
    const used = sheet.getRangeByIndexes(0,0,padded.length,cols);
    used.values = padded;
    used.format.font = {name:'Arial',size:10};
    used.format.columnWidth = 20;
    used.format.rowHeight = 22;
    sheet.showGridLines = false;
    const header = sheet.getRangeByIndexes(0,0,1,cols);
    header.format = {fill:'#1F4E78',font:{bold:true,color:'#FFFFFF',name:'Arial',size:10},
      wrapText:true,rowHeight:44};
    sheet.freezePanes.freezeRows(1);
    if (data.name === 'Capabilities' || data.name === 'Review Guide') {
      sheet.getRangeByIndexes(0,0,padded.length,1).format.columnWidth = 23;
      sheet.getRangeByIndexes(0,1,padded.length,1).format.columnWidth = 105;
      used.format.wrapText = true;
      used.format.rowHeight = 38;
    }
    if (data.name === 'Decisions') {
      sheet.getRangeByIndexes(0,3,padded.length,1).format.columnWidth = 82;
      used.format.wrapText = true;
      used.format.rowHeight = 44;
    }
    if (data.name === 'Source provenance') {
      sheet.getRangeByIndexes(0,0,padded.length,1).format.columnWidth = 100;
      sheet.getRangeByIndexes(0,1,padded.length,1).format.columnWidth = 72;
      used.format.wrapText = true;
      used.format.rowHeight = 48;
    }
    for (let col=0;col<cols;col++) {
      const name = String(padded[0][col] ?? '');
      if (/sha256|source_bracket|unit_policy|path|source_excel_rows/.test(name) && data.name !== 'Source provenance') {
        sheet.getRangeByIndexes(0,col,padded.length,1).format.columnWidth = 42;
        sheet.getRangeByIndexes(0,col,padded.length,1).format.wrapText = true;
        if(padded.length>1) sheet.getRangeByIndexes(1,0,padded.length-1,cols).format.rowHeight = 42;
      }
      if (name === 'remark') {
        sheet.getRangeByIndexes(0,col,padded.length,1).format.columnWidth = 55;
        sheet.getRangeByIndexes(0,col,padded.length,1).format.wrapText = true;
        if(padded.length>1) sheet.getRangeByIndexes(1,0,padded.length-1,cols).format.rowHeight = 36;
      }
      if (name === 'gaps') {
        sheet.getRangeByIndexes(0,col,padded.length,1).format.columnWidth = 75;
        sheet.getRangeByIndexes(0,col,padded.length,1).format.wrapText = true;
        if(padded.length>1) sheet.getRangeByIndexes(1,0,padded.length-1,cols).format.rowHeight = 52;
      }
      if (name === 'contact_boundary_positions_m')
        sheet.getRangeByIndexes(0,col,padded.length,1).format.columnWidth = 32;
      if (/approved_/.test(name) && padded.length>1)
        sheet.getRangeByIndexes(1,col,padded.length-1,1).format.fill = '#FFF2CC';
      if (/FromM|ToM|_m$/.test(name) && padded.length>1)
        sheet.getRangeByIndexes(1,col,padded.length-1,1).setNumberFormat('0.0000');
    }
  }
  wb.recalculate();
  const inspection = await wb.inspect({kind:'match', searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',
    options:{useRegex:true,maxResults:20},summary:'review workbook error scan'});
  await fs.writeFile(path.join(output,layout.filename+'.inspect.txt'),inspection.ndjson);
  const file = path.join(exportDir,layout.filename);
  await (await SpreadsheetFile.exportXlsx(wb)).save(file);
  for (const data of layout.sheets) {
    const rows = Math.min(data.matrix.length,6);
    const cols = Math.min(data.matrix[0].length,6);
    const lastCol = String.fromCharCode(64+cols);
    const preview = await wb.render({sheetName:data.name, range:`A1:${lastCol}${rows}`,scale:1,format:'png'});
    await fs.writeFile(path.join(output,layout.filename.replace('.xlsx','')+'-'+data.name.replace(/[^a-zA-Z0-9 ]/g,'_')+'.png'),
      new Uint8Array(await preview.arrayBuffer()));
    const detailRange = data.name === 'DRL UT' || data.name === 'DRL PL' ? 'H1:J6'
      : data.name === 'Boundary Review' ? `G1:${layout.filename.startsWith('Contact')?'P':'N'}6` : null;
    if (detailRange) {
      const detail = await wb.render({sheetName:data.name,range:detailRange,scale:1,format:'png'});
      await fs.writeFile(path.join(output,layout.filename.replace('.xlsx','')+'-'+data.name+'-detail.png'),
        new Uint8Array(await detail.arrayBuffer()));
    }
  }
  manifests.push({file,status:'review-only; no approved interval promotion',
    sheets:layout.sheets.map(s=>({name:s.name,rows:s.matrix.length-1}))});
}
await fs.writeFile(path.join(output,'workbook-build-manifest.json'),JSON.stringify(manifests,null,2));
console.log(JSON.stringify({workbooks:manifests.length,output:exportDir}));
