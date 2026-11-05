import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const root=process.cwd(),out=path.join(root,'outputs/metadata-activation-2026-11-05/wide-v3');
const {chromium}=await import(pathToFileURL(path.join(root,'frontend/node_modules/playwright/index.mjs')).href);
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const evidence={status:'running',entry:'npm run dev starts Electron/Vite/FastAPI; browser UI on same dev service, formal config, isolated test DB, real CSV sample via file-picker adapter; no API interception'};
const save=()=>fs.writeFile(path.join(out,'smoke.json'),JSON.stringify(evidence,null,2));
let browser,page;
try{
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.addInitScript(source=>{window.electronAPI={openFile:async()=>source};},path.join(out,'TWL-activation-smoke.csv'));
  page=await context.newPage();
  await page.goto('http://localhost:5174/');
  page.setDefaultTimeout(90000);
  for(let i=0;i<120;i++){
    try{if(await page.evaluate(()=>fetch('/api/health').then(r=>r.ok)))break;}catch{}
    await pause(1000);
  }
  evidence.runtime=await page.evaluate(()=>fetch('/api/diagnostics').then(r=>r.json()));
  console.log('Runtime verified '+JSON.stringify(evidence.runtime));
  if(path.resolve(evidence.runtime.config_directory)!==path.join(root,'config'))throw new Error('Wrong config directory');
  if(path.resolve(evidence.runtime.database_path)!==path.join(out,'isolated.db'))throw new Error('Wrong test DB');
  const release=JSON.parse(await fs.readFile(path.join(root,'config/tov1050-metadata-release.json'),'utf8'));
  evidence.release=release.release;
  const sheets=[];
  for(const file of release.files){
    console.log('Read '+file.identity);
    const filename=path.basename(file.destination);
    const data=await page.evaluate(async name=>{const r=await fetch('/api/metadata/'+encodeURIComponent(name)+'/sheets');if(!r.ok)throw new Error(await r.text());return r.json();},filename);
    if(!Array.isArray(data))throw new Error('Unexpected sheets response');
    for(const sheet of Object.keys(file.runtime_preflight))if(!data.includes(sheet))throw new Error('Missing sheet '+sheet);
    sheets.push({file:filename,sheets:data.length});
  }
  evidence.metadata_files=sheets;await save();
  await page.getByRole('button',{name:'Exception Generator',exact:true}).click();
  await page.getByRole('button',{name:/^(Start New Analysis|New Analysis)$/}).first().click();
  await page.getByRole('button',{name:'Browse',exact:true}).click();
  const line=page.getByRole('combobox',{name:'Line',exact:true});
  if((await line.innerText())!=='TWL'){await line.click();await page.getByRole('option',{name:'TWL',exact:true}).click();}
  await page.getByLabel('Station Start',{exact:true}).fill('CEN');
  await page.getByLabel('Station End',{exact:true}).fill('TSW');
  const submitted=page.waitForResponse(r=>r.url().includes('/analysis/jobs')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Start Analysis',exact:true}).click();
  const response=await submitted,job=await response.json();
  if(response.status()!==202)throw new Error(JSON.stringify(job));
  evidence.analysis_job=job;await save();
  const query='?client_session_id='+encodeURIComponent(job.client_session_id);
  let state;
  for(let i=0;i<240;i++){
    state=await page.evaluate(url=>fetch(url).then(r=>r.json()),'/api/jobs/'+job.job_id+query);
    if(['ready','failed','cancelled'].includes(state.status))break;
    await pause(1000);
  }
  if(state.status!=='ready')throw new Error(JSON.stringify(state));
  const result=await page.evaluate(url=>fetch(url).then(r=>r.json()),'/api/jobs/'+job.job_id+'/result'+query);
  const expected=release.files.find(f=>f.identity==='TWL').approved_sha256;
  if(result.aggregation_metadata.metadata_sha256!==expected)throw new Error('Analysis did not use activated config SHA');
  if(result.metadata_capabilities.enrichment_source!=='wide_excel')throw new Error('Wrong enrichment provider');
  if(result.metadata_capabilities.enrichment_version!=='wide-excel-enrichment-2026-11-05-v1')throw new Error('Wrong enrichment version');
  await page.getByRole('button',{name:'匯出例外報表',exact:true}).waitFor({state:'visible'});
  evidence.analysis={aggregation_metadata:result.aggregation_metadata,metadata_capabilities:result.metadata_capabilities,
    counts:Object.fromEntries(Object.entries(result.exceptions??{}).map(([k,v])=>[k,v.length]))};
  for(const f of release.files){const digest=crypto.createHash('sha256').update(await fs.readFile(f.destination)).digest('hex');if(digest!==f.approved_sha256)throw new Error('Config changed during smoke');}
  await page.screenshot({path:path.join(out,'activation-ui.png'),timeout:10000});
  evidence.status='passed';await save();console.log('PASS: formal config, all 8 files, actual UI analysis uses approved TWL SHA');
}catch(error){evidence.status='failed';evidence.error=String(error.stack??error);if(page){evidence.body=await page.locator('body').innerText().catch(()=>'?');await page.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});}await save();console.error(error);process.exitCode=1;}
finally{await save();if(browser)await browser.close().catch(()=>{});process.exit(process.exitCode??0);}
