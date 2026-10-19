-- Read-only audit. Does not execute processors or modify existing records.
with latest as (
  select * from public.raw_api_data where source='BATCH_RAW' order by id desc limit 1
), funcs as (
  select proname,prosecdef,
    md5(regexp_replace(regexp_replace(prosrc,'--[^'||chr(10)||']*','','g'),'[[:space:]]+','','g')) as fingerprint
  from pg_proc where pronamespace='public'::regnamespace and proname in
    ('process_naver_trend_raw','process_tourism_demand_raw','process_naver_local_raw','trigger_process_batch_raw')
), triggers as (
  select tgname,tgenabled,pg_get_triggerdef(oid) as definition
  from pg_trigger where tgrelid='public.raw_api_data'::regclass and not tgisinternal
)
select jsonb_build_object(
  'raw_count',(select count(*) from public.raw_api_data),
  'legacy_raw_fingerprints',(select jsonb_agg(jsonb_build_object('id',r.id,'hash',md5(to_jsonb(r)::text)) order by r.id) from public.raw_api_data r where r.id in (1,2)),
  'archive_count',(select count(*) from public.tourism_demand_metric_archive),
  'archive_fingerprint',(select md5(coalesce(jsonb_agg(a order by id)::text,'')) from public.tourism_demand_metric_archive a),
  'legacy_seoul',(select row_snapshot->>'consumption_strength' from public.tourism_demand_metric_archive where row_snapshot->>'region_code'='11' limit 1),
  'latest',(select jsonb_build_object(
    'id',r.id,'run_id',r.run_id,'source',r.source,'status',r.process_status,'processed_at',r.processed_at,'error',r.error_message,'counts',r.processed_counts,
    'raw_sizes',jsonb_build_array(length(r.naver_trend_raw),length(r.tourism_demand_raw),length(r.tourism_consumption_raw),length(r.naver_local_raw)),
    'naver_rows',(select count(*) from public.naver_trend where raw_id=r.id),
    'tourism_rows',(select count(*) from public.tourism_demand where raw_id=r.id),
    'complete_tourism_rows',(select count(*) from public.tourism_demand where raw_id=r.id and stay_strength is not null and consumption_strength is not null),
    'correct_metric_rows',(select count(*) from public.tourism_demand where raw_id=r.id and consumption_metric_code='22'),
    'local_rows',(select count(*) from public.local_places where raw_id=r.id),
    'invalid_local_rows',(select count(*) from public.local_places where raw_id=r.id and (name ~ '<[^>]*>' or longitude is null or latitude is null or longitude not between 124 and 132 or latitude not between 33 and 39)),
    'consumption_api_code',r.tourism_consumption_raw::jsonb#>>'{response,header,resultCode}',
    'consumption_metric_codes',(select jsonb_agg(distinct item->>'tarExpDsIxCd') from jsonb_array_elements(r.tourism_consumption_raw::jsonb#>'{response,body,items,item}') item)
  ) from latest r),
  'current_seoul',(select jsonb_build_object('value',consumption_strength,'metric_code',consumption_metric_code,'raw_id',raw_id) from public.tourism_demand where region_code='11' and reference_date='2025-09-01'),
  'duplicate_trend_keys',(select count(*) from (select reference_date,keyword from public.naver_trend group by reference_date,keyword having count(*)>1) q),
  'duplicate_tourism_keys',(select count(*) from (select reference_date,region_code from public.tourism_demand group by reference_date,region_code having count(*)>1) q),
  'duplicate_place_keys',(select count(*) from (select place_key from public.local_places group by place_key having count(*)>1) q),
  'functions',(select jsonb_agg(f order by proname) from funcs f),
  'triggers',(select jsonb_agg(t order by tgname) from triggers t),
  'raw_public_select',has_table_privilege('anon','public.raw_api_data','select'),
  'archive_public_select',has_table_privilege('anon','public.tourism_demand_metric_archive','select')
) as lecture_step24_audit;
