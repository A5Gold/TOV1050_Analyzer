// Author the approved DRL wide candidate using only the bundled artifact runtime.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const output = path.resolve(process.argv[2]);
const requireRuntime = createRequire(path.join(output,'artifact-runtime.cjs'));
const {Workbook,SpreadsheetFile} = await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href);
const [layout] = JSON.parse(await fs.readFile(path.join(output,'workbook-layouts.json'),'utf8'));
const wb = Workbook.create();
for (const data of layout.sheets) {
  const sheet = wb.worksheets.add(data.name);
  const cols = Math.max(...data.matrix.map(row=>row.length));
  const matrix = data.matrix.map(row=>[...row,...Array(cols-row.length).fill(null)]);
  const used = sheet.getRangeByIndexes(0,0,matrix.length,cols);
  used.values = matrix;
  used.format.font = {name:'Arial',size:10};
  used.format.columnWidth = 19;
  used.format.rowHeight = 23;
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.getRangeByIndexes(0,0,1,cols).format = {fill:'#1F4E78',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:46};
  for(let c=0;c<cols;c++) {
    const label=String(matrix[0][c]);
    if (/FromM|ToM|FromM$|ToM$/.test(label)) sheet.getRangeByIndexes(1,c,matrix.length-1,1).setNumberFormat('0.0###');
    if (/source_sha256|SHA256/.test(label)) sheet.getRangeByIndexes(0,c,matrix.length,1).format.columnWidth=72;
  }
  if (data.name==='threshold') {
    sheet.getRange('C1:C41').format.columnWidth=24;
    sheet.getRange('D2:O41').setNumberFormat('0.0#');
  }
  if(data.name==='Review Guide') {
    used.format.wrapText=true; used.format.rowHeight=43;
    sheet.getRangeByIndexes(0,0,matrix.length,1).format.columnWidth=23;
    sheet.getRangeByIndexes(0,1,matrix.length,1).format.columnWidth=110;
  }
  if(data.name==='TL Boundaries') {
    sheet.getRange('C2:D10').setNumberFormat('0.0###');
    sheet.getRange('F1:G10').format.columnWidth=34;
    sheet.getRange('H1:H10').format.columnWidth=70;
    sheet.getRange('H1:H10').format.wrapText=true;
    sheet.getRange('A2:H10').format.rowHeight=48;
  }
  if(data.name==='Source provenance') {
    sheet.getRange('A1:A4').format.columnWidth=110;
    used.format.wrapText=true;used.format.rowHeight=48;
  }
  if(data.name==='Conversion audit') {
    sheet.getRangeByIndexes(0,1,matrix.length,2).format.columnWidth=75;
  }
}
wb.recalculate();
await fs.writeFile(path.join(output,'inspect.txt'),(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20}})).ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(output,layout.filename));
for (const sheet of layout.sheets) {
  const cols=sheet.name==='threshold'?15:sheet.name==='DRL UT'||sheet.name==='DRL PL'?11:Math.min(sheet.matrix[0].length,8);
  const range=`A1:${String.fromCharCode(64+cols)}${Math.min(sheet.matrix.length,6)}`;
  const image=await wb.render({sheetName:sheet.name,range,scale:1,format:'png'});
  await fs.writeFile(path.join(output,sheet.name+'.png'),new Uint8Array(await image.arrayBuffer()));
}
console.log(JSON.stringify({file:path.join(output,layout.filename),sheets:layout.sheets.length}));
