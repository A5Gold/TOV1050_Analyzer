// Import existing workbooks, preserving unrelated sheets and formatting.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const output=path.resolve(process.argv[2]);
const requireRuntime=createRequire(path.join(output,'artifact-runtime.cjs'));
const {FileBlob,SpreadsheetFile}=await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href);
const layouts=JSON.parse(await fs.readFile(path.join(output,'workbook-layouts.json'),'utf8'));
await fs.mkdir(path.join(output,'candidates'),{recursive:true});
const manifest=[];
for(const layout of layouts) {
  if(process.argv[3] && layout.identity!==process.argv[3]) continue;
  console.log('Importing '+layout.identity);
  const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(layout.source));
  const previewDir=path.join(output,'previews',layout.identity);
  await fs.mkdir(previewDir,{recursive:true});
  const sourceImage=await wb.render({sheetName:layout.changes[0].name,range:'A1:G6',scale:1,format:'png'});
  await fs.writeFile(path.join(previewDir,'source-direction.png'),new Uint8Array(await sourceImage.arrayBuffer()));
  for(const data of [...layout.changes,...layout.added]) {
    const changed=layout.changes.includes(data);
    const sheet=changed?wb.worksheets.getItem(data.name):wb.worksheets.add(data.name);
    const cols=Math.max(...data.matrix.map(row=>row.length));
    const matrix=data.matrix.map(row=>[...row,...Array(cols-row.length).fill(null)]);
    if(changed) sheet.getRangeByIndexes(0,0,Math.max(data.source_max_row,matrix.length),cols).values=
      Array.from({length:Math.max(data.source_max_row,matrix.length)},()=>Array(cols).fill(null));
    const used=sheet.getRangeByIndexes(0,0,matrix.length,cols);
    used.values=matrix;
    used.format.font={name:'Arial',size:10};
    used.format.columnWidth=20;
    used.format.rowHeight=23;
    sheet.showGridLines=false;
    sheet.freezePanes.freezeRows(1);
    sheet.getRangeByIndexes(0,0,1,cols).format={fill:'#1F4E78',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:46,
      horizontalAlignment:'center',verticalAlignment:'center'};
    for(let c=0;c<cols;c++) {
      const label=String(matrix[0][c]);
      if(/FromM|ToM/.test(label)&&matrix.length>1) sheet.getRangeByIndexes(1,c,matrix.length-1,1).setNumberFormat('0.0###');
      if(/workbook|SHA256/i.test(label)) sheet.getRangeByIndexes(0,c,matrix.length,1).format.columnWidth=70;
    }
    if(changed) {
      sheet.getRangeByIndexes(0,6,matrix.length,1).format.columnWidth=30;
      sheet.getRangeByIndexes(1,6,matrix.length-1,1).format.wrapText=true;
    }
    if(data.name==='TL Boundaries') {
      sheet.getRangeByIndexes(0,5,matrix.length,1).format.columnWidth=55;
      sheet.getRangeByIndexes(0,6,matrix.length,2).format.columnWidth=44;
      sheet.getRangeByIndexes(1,5,matrix.length-1,3).format.wrapText=true;
      sheet.getRangeByIndexes(1,0,matrix.length-1,cols).format.rowHeight=36;
      sheet.getRangeByIndexes(1,2,matrix.length-1,2).setNumberFormat('0.0###');
    }
    if(data.name==='Wide Candidate Guide') {
      sheet.getRangeByIndexes(0,1,matrix.length,1).format.columnWidth=115;
      used.format.wrapText=true;used.format.rowHeight=43;
    }
    if(data.name==='Wide Candidate Source') {
      used.format.wrapText=true;used.format.rowHeight=70;
      sheet.getRange('A1:A2').format.columnWidth=95;
    }
    if(data.name==='Data Review') {
      sheet.getRangeByIndexes(0,6,matrix.length,2).format.columnWidth=60;
      used.format.wrapText=true;used.format.rowHeight=44;
      sheet.getRangeByIndexes(1,0,matrix.length-1,cols).format.fill='#FFF2CC';
    }
    if(changed && layout.source_warnings?.length) {
      const affected=new Set(layout.source_warnings.filter(w=>w.sheet===data.name).map(w=>w.tension_length));
      for(let r=1;r<matrix.length;r++) {
        if(String(matrix[r][6]??'').split(',').some(tl=>affected.has(tl)))
          sheet.getRangeByIndexes(r,3,1,4).format.fill='#FFF2CC';
      }
    }
  }
  wb.recalculate();
  await fs.writeFile(path.join(previewDir,'error-scan.txt'),(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20}})).ndjson);
  const target=path.join(output,'candidates',layout.filename);
  await(await SpreadsheetFile.exportXlsx(wb)).save(target);
  for(const data of [...layout.changes,...layout.added]) {
    const cols=layout.changes.includes(data)?11:Math.min(data.matrix[0].length,8);
    const preview=await wb.render({sheetName:data.name,range:`A1:${String.fromCharCode(64+cols)}${Math.min(data.matrix.length,6)}`,scale:1,format:'png'});
    await fs.writeFile(path.join(previewDir,data.name+'.png'),new Uint8Array(await preview.arrayBuffer()));
  }
  manifest.push({identity:layout.identity,file:target,source_sha256:layout.source_sha256,routes:layout.routes,
    source_warnings:layout.source_warnings??[],status:'review-only; not activated'});
  if(process.argv[3]) {
    const previous=JSON.parse(await fs.readFile(path.join(output,'manifest.json'),'utf8'));
    manifest.splice(0,manifest.length,...previous.map(item=>item.identity===layout.identity?manifest[0]:item));
  }
  await fs.writeFile(path.join(output,'manifest.json'),JSON.stringify(manifest,null,2));
  console.log('Exported '+layout.identity);
}
