import {PGlite} from '@electric-sql/pglite';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const db=new PGlite();
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const batch=base+'/artifacts/batch-20261019-104333/';
await db.exec('create role anon;create role authenticated;create role service_role;');
await db.exec(fs.readFileSync(base+'/sql/001_init.sql','utf8'));
await db.exec(fs.readFileSync(base+'/sql/003_raw_pipeline.sql','utf8'));
for(const table of ['regions','naver_trend','tourism_demand','local_places','ai_region_analysis']){
 const rows=JSON.parse(fs.readFileSync(batch+'before_'+table+'.json','utf8'));
 for(const row of rows){const cols=Object.keys(row);await db.query(`insert into public.${table} (${cols.map(x=>'"'+x+'"').join(',')}) values (${cols.map((_,i)=>'$'+(i+1)).join(',')})`,Object.values(row));}
}
for(const t of ['naver_trend','tourism_demand','local_places','ai_region_analysis'])await db.exec(`select setval(pg_get_serial_sequence('public.${t}','id'),(select max(id) from public.${t}));`);
const old=['naver_trend','tourism_stay','tourism_consumption','naver_local'].map(x=>fs.readFileSync(batch+x+'.json','utf8'));
const insert=async p=>{const r=await db.query('insert into public.raw_api_data(naver_trend_raw,tourism_demand_raw,tourism_consumption_raw,naver_local_raw) values($1,$2,$3,$4) returning id',p);return(await db.query('select * from public.raw_api_data where id=$1',[r.rows[0].id])).rows[0];};
assert.equal((await insert(old)).process_status,'PROCESSED');
const before=JSON.stringify((await db.query('select * from public.tourism_demand order by id')).rows);
const migration=fs.readFileSync(base+'/sql/006_correct_consumption_metric.sql','utf8');
await db.exec(migration);
let now=(await db.query('select * from public.tourism_demand order by id')).rows;
assert(now.every(r=>r.consumption_metric_code==='2201'));
assert.equal(JSON.stringify(now.map(({consumption_metric_code,...r})=>r)),before);console.log('PASS original columns/IDs unchanged; provenance labels 2201');
assert.equal((await db.query('select count(*)::int n from public.tourism_demand_metric_archive')).rows[0].n,26);console.log('PASS 26 original observations privately archived');
await db.exec(migration);assert.equal((await db.query('select count(*)::int n from public.tourism_demand_metric_archive')).rows[0].n,26);console.log('PASS migration rerun does not duplicate archive');
const good=[...old];good[2]=fs.readFileSync(base+'/artifacts/lesson-step16/consumption-request22.json','utf8');
assert.equal((await insert(good)).process_status,'PROCESSED');
assert.deepEqual((await db.query("select consumption_strength,consumption_metric_code from public.tourism_demand where region_code='11'")).rows[0],{consumption_strength:'97.07',consumption_metric_code:'22'});console.log('PASS actual metric22 updates Seoul to 97.07 with code22');
assert.equal((await db.query("select row_snapshot->>'consumption_strength' v from public.tourism_demand_metric_archive where row_snapshot->>'region_code'='11'")).rows[0].v,'119.08');console.log('PASS legacy Seoul119.08 survives metric correction');
assert.equal((await insert(good)).process_status,'PROCESSED');assert.equal((await db.query('select count(*)::int n from public.tourism_demand')).rows[0].n,26);console.log('PASS repeat22 has no duplicate current rows');
const snapshot=async()=>JSON.stringify((await db.query("select jsonb_build_object('t',(select jsonb_agg(t order by id) from public.tourism_demand t),'a',(select jsonb_agg(a order by id) from public.tourism_demand_metric_archive a),'n',(select jsonb_agg(n order by id) from public.naver_trend n),'l',(select jsonb_agg(l order by id) from public.local_places l)) s")).rows);
let beforeReject=await snapshot();assert.equal((await insert(old)).process_status,'ERROR');assert.equal(await snapshot(),beforeReject);console.log('PASS legacy2201 cannot silently masquerade as22');
const bad=[...good];const p=JSON.parse(bad[3]);p.items[0].mapx='99999999999';bad[3]=JSON.stringify(p);beforeReject=await snapshot();assert.equal((await insert(bad)).process_status,'ERROR');assert.equal(await snapshot(),beforeReject);console.log('PASS late failure rolls back current and archive changes');
await db.exec('set role anon');await assert.rejects(db.query('select * from public.tourism_demand_metric_archive'),/permission denied/);await db.exec('reset role');console.log('PASS archive blocked for public reads');
console.log('Metric22 PostgreSQL checks passed: 9');
console.log('Function fingerprint:',(await db.query("select md5(regexp_replace(regexp_replace(prosrc,'--[^'||chr(10)||']*','','g'),'[[:space:]]+','','g')) hash from pg_proc where proname='process_tourism_demand_raw'")).rows[0].hash);await db.close();
