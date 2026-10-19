-- Read-only verification; no keys/raw response body are returned.
select id, run_id, source, fetched_at, process_status, processed_counts, error_message
from public.raw_api_data order by id desc limit 10;

with latest as (select max(id) id from public.raw_api_data where process_status='PROCESSED')
select 'naver_trend' as dataset, count(*) as latest_linked_rows from public.naver_trend, latest where raw_id=latest.id
union all select 'tourism_demand',count(*) from public.tourism_demand,latest where raw_id=latest.id
union all select 'local_places',count(*) from public.local_places,latest where raw_id=latest.id;

select 'regions' as dataset,count(*) from public.regions
union all select 'naver_trend',count(*) from public.naver_trend
union all select 'tourism_demand',count(*) from public.tourism_demand
union all select 'local_places',count(*) from public.local_places
union all select 'ai_region_analysis',count(*) from public.ai_region_analysis;

select reference_date,count(*) as regions,count(stay_strength) as stay_values,
  count(consumption_strength) as consumption_values from public.tourism_demand group by reference_date order by reference_date;

select has_table_privilege('anon','public.raw_api_data','select') as raw_public_select,
  has_table_privilege('authenticated','public.raw_api_data','select') as raw_user_select,
  has_function_privilege('anon','public.process_naver_trend_raw(bigint)','execute') as anonymous_processor_execute,
  (select relrowsecurity from pg_class where oid='public.raw_api_data'::regclass) as raw_rls,
  (select count(*) from pg_constraint where confrelid='public.raw_api_data'::regclass and contype='f') as raw_foreign_keys;

select proname,md5(regexp_replace(regexp_replace(prosrc,'--[^'||chr(10)||']*','','g'),'[[:space:]]+','','g')) as fingerprint
from pg_proc where proname in ('process_naver_trend_raw','process_tourism_demand_raw','process_naver_local_raw','trigger_process_batch_raw') order by proname;
