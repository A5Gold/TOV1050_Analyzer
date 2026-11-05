import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
const root=process.cwd(), out=path.join(root,'outputs/validation-2026-11-03/npm-dev-retest');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const evidence={status:'running',entry:'npm run dev starts Electron/Vite/FastAPI; browser UI on same dev service; file picker adapter supplies real CSV paths; no API interception',reports:[],errors:[],requests_failed:[]};
const sources=['20260907','20260630'].map(d=>path.join(root,'00 Reference Document/Raw data/TWL',`${d}_TWL_UT.csv`));
const protectedFiles=[...sources,...(await fs.readdir(path.join(root,'config'))).filter(n=>n.endsWith('metadata.xlsx')).map(n=>path.join(root,'config',n))];
const sha=async p=>crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
const fingerprints=Object.fromEntries(await Promise.all(protectedFiles.map(async p=>[p,await sha(p)])));
const save=()=>fs.writeFile(path.join(out,'validation.json'),JSON.stringify(evidence,null,2));
let browser,page;
async function nextDownload(previous) {
  for(let i=0;i<600;i++) {
    const found=(await fs.readdir(out)).filter(n=>n.endsWith('.xlsx')&&!previous.includes(n));
    if(found.length) {const p=path.join(out,found[0]); let size=0;
      for(let j=0;j<60;j++){await pause(500);const n=(await fs.stat(p)).size;if(n>0&&n===size)return p;size=n;}
    }
    await pause(1000);
  }
  throw new Error('Download did not finish');
}
try {
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({acceptDownloads:true,viewport:{width:1440,height:1000}});
  await context.addInitScript(()=>{window.electronAPI={openFile:async()=>window.__testSource};});
  page=await context.newPage();
  page.on('download',d=>d.saveAs(path.join(out,d.suggestedFilename())).catch(e=>evidence.errors.push(String(e))));
  await page.goto('http://localhost:5174/');
  page.setDefaultTimeout(60000);
  page.on('pageerror',e=>evidence.errors.push(String(e)));
  page.on('requestfailed',r=>{if(r.url().includes('/api/'))evidence.requests_failed.push({url:r.url(),error:r.failure()});});
  page.on('console',m=>{if(m.type()==='error')evidence.errors.push(m.text());});
  for(let i=0;i<120;i++){try{if(await page.evaluate(()=>fetch('/api/health').then(r=>r.ok)))break;}catch{}await pause(1000);}
  evidence.runtime=await page.evaluate(()=>fetch('/api/diagnostics').then(r=>r.json()));
  if(path.resolve(evidence.runtime.database_path)!==path.join(out,'isolated.db'))throw new Error('Database not isolated');
  await save();
  await page.getByRole('button',{name:'Exception Generator',exact:true}).click();
  for(const source of sources){
    const started=performance.now();
    await page.getByRole('button',{name:/^(Start New Analysis|New Analysis)$/}).first().click();
    await fs.writeFile(path.join(out,'selected-source.txt'),source);
    await page.evaluate(source=>{window.__testSource=source;},source);
    await page.getByRole('button',{name:'Browse',exact:true}).click();
    const line=page.getByRole('combobox',{name:'Line',exact:true});
    if((await line.innerText())!=='TWL'){await line.click();await page.getByRole('option',{name:'TWL',exact:true}).click();}
    await page.getByLabel('Station Start',{exact:true}).fill('CEN');
    await page.getByLabel('Station End',{exact:true}).fill('TSW');
    const date=path.basename(source).slice(0,8);
    const dateGroup=page.getByRole('group',{name:'Date',exact:true});
    for(const [label,value] of [['Year',date.slice(0,4)],['Month',date.slice(4,6)],['Day',date.slice(6,8)]]){
      await dateGroup.getByRole('spinbutton',{name:label,exact:true}).click();
      await page.keyboard.type(value);
    }
    await page.keyboard.press('Tab');
    const submitted=page.waitForResponse(r=>r.url().includes('/analysis/jobs')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Start Analysis',exact:true}).click();
    const submit=await submitted,job=await submit.json();
    const submittedParams=submit.request().postDataJSON();
    if(submittedParams.date_str!==date)throw new Error('Incorrect analysis date '+JSON.stringify(submittedParams));
    if(submit.status()!==202)throw new Error(JSON.stringify(job));
    console.log('Analysis submitted '+path.basename(source),job.job_id);
    await save();
    const exportButton=page.getByRole('button',{name:'匯出例外報表',exact:true});
    await exportButton.waitFor({state:'visible',timeout:600000});
    const analysisSeconds=(performance.now()-started)/1000;
    const result=await page.evaluate(async ({id,session})=>{
      const r=await fetch(`/api/jobs/${id}/result?client_session_id=${encodeURIComponent(session)}`);if(!r.ok)throw new Error(await r.text());return r.json();
    },{id:job.job_id,session:job.client_session_id});
    const files=await fs.readdir(out);
    await exportButton.click();
    const report=await nextDownload(files);
    evidence.reports.push({source,report,analysis_seconds:analysisSeconds,total_seconds:(performance.now()-started)/1000,
      counts:Object.fromEntries(Object.entries(result.exceptions??{}).map(([k,v])=>[k,v.length])),aggregation_metadata:result.aggregation_metadata,analysis_job:job,params:result.params});
    await page.screenshot({path:path.join(out,`exception-${path.basename(source,'.csv')}.png`),timeout:5000}).catch(e=>evidence.errors.push('Screenshot: '+e));
    await save();console.log('Exported '+report);
  }
  await page.getByRole('button',{name:/History/}).first().click();
  if(await page.getByRole('button',{name:'Start New Comparison',exact:true}).count())await page.getByRole('button',{name:'Start New Comparison',exact:true}).click();
  for(let i=0;i<2;i++)await page.locator('input[type=file]').nth(i).setInputFiles(evidence.reports[i].report);
  const started=performance.now();
  const submitted=page.waitForResponse(r=>r.url().includes('/analyze/compare/jobs')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Compare',exact:true}).click();
  const response=await submitted,job=await response.json();
  evidence.history={job,submit_http:response.status(),submit_seconds:(performance.now()-started)/1000};await save();
  if(response.status()!==202)throw new Error(JSON.stringify(job));
  console.log('History submitted '+job.job_id);
  await page.getByRole('button',{name:'Save to DB',exact:true}).waitFor({state:'visible',timeout:600000});
  evidence.history.compare_seconds=(performance.now()-started)/1000;
  const result=await page.evaluate(async ({id,session})=>{
    const r=await fetch(`/api/jobs/${id}/result?client_session_id=${encodeURIComponent(session)}`);if(!r.ok)throw new Error(await r.text());return r.json();
  },{id:job.job_id,session:job.client_session_id});
  evidence.history.stats=result.stats;evidence.history.metrics=result.metrics;
  const files=await fs.readdir(out);
  await page.getByRole('button',{name:'Export',exact:true}).click();
  evidence.history.report=await nextDownload(files);
  await page.screenshot({path:path.join(out,'history-ready.png'),timeout:5000}).catch(e=>evidence.errors.push('Screenshot: '+e));
  evidence.sources_and_config_unchanged=(await Promise.all(protectedFiles.map(async p=>(await sha(p))===fingerprints[p]))).every(Boolean);
  if(!evidence.sources_and_config_unchanged)throw new Error('Protected file changed');
  evidence.status='passed';await save();console.log(JSON.stringify(evidence.history));
}catch(error){evidence.status='failed';evidence.error=String(error.stack??error);if(page){evidence.body=await page.locator('body').innerText().catch(()=>'?');await page.screenshot({path:path.join(out,'failure.png'),timeout:5000}).catch(()=>{});}await save();console.error(error);process.exitCode=1;}
finally{await save();process.exit(process.exitCode??0);}
