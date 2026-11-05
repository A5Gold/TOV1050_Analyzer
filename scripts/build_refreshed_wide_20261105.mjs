import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const output=path.resolve('outputs/metadata-review-2026-11-05/wide-v3');
const runtime=createRequire(path.join(output,'artifact-runtime.cjs'));
const {FileBlob,SpreadsheetFile}=await import(pathToFileURL(runtime.resolve('@oai/artifact-tool')).href);
if(process.argv.includes('--preview-history')){
  const file=path.resolve('outputs/validation-2026-11-05/wide-enrichment/20260907_TWL_UT_MAINLINE_CEN_TSW_Exception_Report_2_Repeated.xlsx');
  const book=await SpreadsheetFile.importXlsx(await FileBlob.load(file));
  const preview=await book.render({sheetName:'Summary',range:'A1:V5',scale:1,format:'png'});
  await fs.writeFile(path.join(output,'previews','history-summary.png'),new Uint8Array(await preview.arrayBuffer()));
  process.exit(0);
}
const layouts=JSON.parse(await fs.readFile(path.join(output,'layouts.json'),'utf8'));
await fs.mkdir(path.join(output,'candidates'),{recursive:true});
await fs.mkdir(path.join(output,'previews'),{recursive:true});
const manifest=[];
for(const layout of layouts){
  console.log('Import '+layout.filename);
  const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(layout.source));
  const before=await wb.render({sheetName:layout.routes[0].sheet,range:'A1:K5',scale:1,format:'png'});
  await fs.writeFile(path.join(output,'previews',layout.filename+'.before.png'),new Uint8Array(await before.arrayBuffer()));
  for(const data of layout.changes){
    const sheet=data.new?wb.worksheets.add(data.name):wb.worksheets.getItem(data.name);
    const cols=Math.max(...data.matrix.map(r=>r.length));
    if(!data.new)sheet.getRangeByIndexes(0,0,Math.max(data.old_rows,data.matrix.length),cols).clear({applyTo:'contents'});
    const values=data.matrix.map(r=>[...r,...Array(cols-r.length).fill(null)]);
    const range=sheet.getRangeByIndexes(0,0,values.length,cols);
    range.values=values;
    if(data.name.endsWith(' UT')||data.name.endsWith(' DT')||data.name==='DRL PL'){
      sheet.getRangeByIndexes(1,3,values.length-1,4).format.fill='#FFFFFF';
      for(const c of [0,1,3,4,8,9])sheet.getRangeByIndexes(1,c,values.length-1,1).setNumberFormat('0.####');
    }
    if(data.new){range.format.columnWidth=35;range.format.font={name:'Arial',size:10};sheet.getRange('B1:B6').format.columnWidth=110;range.format.wrapText=true;range.format.rowHeight=42;}
    sheet.getRangeByIndexes(0,0,1,cols).format.font={name:'Arial',size:10,bold:true,color:'#FFFFFF'};
    sheet.getRangeByIndexes(0,0,1,cols).format.fill='#1F4E78';
    if(data.name==='Data Review'&&values.length>1)sheet.getRangeByIndexes(1,0,values.length-1,cols).format.fill='#FFFFFF';
  }
  wb.recalculate();
  const peek=await wb.inspect({kind:'table',range:`'${layout.routes[0].sheet}'!A1:K5`,include:'values,formulas',tableMaxRows:5,tableMaxCols:11});
  await fs.writeFile(path.join(output,'previews',layout.filename+'.inspect.ndjson'),peek.ndjson);
  for(const name of [layout.routes[0].sheet,'TL Boundaries']){
    const png=await wb.render({sheetName:name,range:name==='TL Boundaries'?'A1:G5':'A1:K5',scale:1,format:'png'});
    await fs.writeFile(path.join(output,'previews',layout.filename+'.'+name+'.png'),new Uint8Array(await png.arrayBuffer()));
  }
  await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(output,'candidates',layout.filename));
  manifest.push({file:layout.filename,source:layout.source,source_sha256:layout.source_sha256,routes:layout.routes,production_activation:false});
  await fs.writeFile(path.join(output,'manifest.json'),JSON.stringify(manifest,null,2));
  console.log('Export '+layout.filename);
}
