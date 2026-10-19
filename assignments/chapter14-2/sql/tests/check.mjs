import { PGlite } from '@electric-sql/pglite';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const db=new PGlite();
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const batch=path.resolve(process.argv[2] || path.join(base,'artifacts/batch-20261019-104333'))+path.sep;
await db.exec('create role anon; create role authenticated; create role service_role;');
await db.exec(fs.readFileSync(base+'/sql/001_init.sql','utf8'));
await db.exec(fs.readFileSync(path.join(base,'sql/003_raw_pipeline.sql'),'utf8'));
for (const table of ['regions','naver_trend','tourism_demand','local_places','ai_region_analysis']) {
  for(const row of JSON.parse(fs.readFileSync(batch+'before_'+table+'.json','utf8'))){
    const cols=Object.keys(row);await db.query(`insert into public.${table} (${cols.map(x=>'"'+x+'"').join(',')}) values (${cols.map((_,i)=>'$'+(i+1)).join(',')})`,Object.values(row));
  }
}
// Imported explicit seed IDs do not advance local test sequences.
for(const t of ['naver_trend','tourism_demand','local_places','ai_region_analysis']) await db.exec(`select setval(pg_get_serial_sequence('public.${t}','id'),(select max(id) from public.${t}));`);
const payload=['naver_trend','tourism_stay','tourism_consumption','naver_local'].map(x=>fs.readFileSync(batch+x+'.json','utf8'));
const insert=async(p=payload)=>{
 const r=await db.query('insert into public.raw_api_data(naver_trend_raw,tourism_demand_raw,tourism_consumption_raw,naver_local_raw) values($1,$2,$3,$4) returning id',p);
 return (await db.query('select * from public.raw_api_data where id=$1',[r.rows[0].id])).rows[0];
};
const counts=async()=> (await db.query("select (select count(*) from naver_trend)::int n,(select count(*) from tourism_demand)::int t,(select count(*) from local_places)::int l")).rows[0];
const snapshot=async()=>JSON.stringify((await db.query("select jsonb_build_object('n',(select jsonb_agg(x order by id) from naver_trend x),'t',(select jsonb_agg(x order by id) from tourism_demand x),'l',(select jsonb_agg(x order by id) from local_places x)) data")).rows[0]);
let result=await insert(); console.log('real API batch:',result.process_status,result.processed_counts,result.error_message); assert.equal(result.process_status,'PROCESSED');assert.deepEqual(result.processed_counts,{naver_trend:52,tourism_demand:26,local_places:5});
const first=await counts();result=await insert();assert.equal(result.process_status,'PROCESSED');assert.deepEqual(await counts(),first);console.log('PASS repeat has no duplicate rows',first);
let tests=2;
async function reject(label,change){const p=payload.map(JSON.parse);change(p);const before=await snapshot();const row=await insert(p.map(JSON.stringify));assert.equal(row.process_status,'ERROR',label);assert.equal(await snapshot(),before,label+' must roll back all derived changes');assert.equal(row.processed_counts,null);assert.match(row.error_message,/^BATCH_VALIDATION_FAILED \[[A-Z0-9]{5}\]$/);console.log('PASS reject + rollback:',label);tests++;}
await reject('tourism API error',p=>p[2].response.header.resultCode='99');
await reject('partial tourism page',p=>p[1].response.body.totalCount=100);
await reject('unmatched month',p=>p[2].response.body.items.item[0].baseYm='202508');
await reject('duplicate consumption region',p=>p[2].response.body.items.item[1]=p[2].response.body.items.item[0]);
await reject('wrong metric',p=>p[2].response.body.items.item[0].tarExpDsIxCd='22');
await reject('invalid coordinates',p=>p[3].items[0].mapx='99999999999');
await reject('empty places',p=>p[3].items=[]);
await reject('out of scope address',p=>p[3].items[0].roadAddress='부산광역시 중구 중앙대로 1');
await reject('invalid trend ratio',p=>p[0].results[0].data[0].ratio=101);
await reject('trend month mismatch',p=>p[0].results[0].data.pop());
await reject('duplicate trend',p=>p[0].results[1]=p[0].results[0]);
const beforeBad=await snapshot();result=await insert(['not-json',...payload.slice(1)]);assert.equal(result.process_status,'ERROR');assert.equal(await snapshot(),beforeBad);tests++;console.log('PASS malformed JSON + rollback');
await db.exec('set role anon');
for(const stmt of ['select * from raw_api_data','select process_naver_trend_raw(1)','select process_tourism_demand_raw(1)','select process_naver_local_raw(1)']){await assert.rejects(db.query(stmt),/permission denied/);tests++;}
await db.query('select count(*) from local_places');await db.exec('reset role');
await db.exec(fs.readFileSync(path.join(base,'sql/003_raw_pipeline.sql'),'utf8'));assert.deepEqual(await counts(),first);tests++;console.log('PASS migration rerun preserves rows');
console.log('PostgreSQL checks passed:',tests);await db.close();
