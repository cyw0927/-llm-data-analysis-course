-- Lecture STEP 9-12. Read-only audit: no INSERT/UPDATE/DELETE/DDL.
with duplicate_keys as (
  select reference_date,region_code,count(*) as duplicate_count
  from public.tourism_demand group by reference_date,region_code having count(*)>1
), latest_sample as (
  select reference_date,region_code,stay_strength,consumption_strength
  from public.tourism_demand order by reference_date desc,region_code limit 5
), raw_columns as (
  select ordinal_position,column_name,data_type,is_nullable,column_default,is_identity
  from information_schema.columns where table_schema='public' and table_name='raw_api_data'
), raw_summary as (
  select id,source,process_status,processed_counts,processed_at,error_message,
    length(naver_trend_raw)>0 and length(tourism_demand_raw)>0
      and length(tourism_consumption_raw)>0 and length(naver_local_raw)>0 as four_bodies_present,
    jsonb_typeof(naver_trend_raw::jsonb)='object'
      and jsonb_typeof(tourism_demand_raw::jsonb)='object'
      and jsonb_typeof(tourism_consumption_raw::jsonb)='object'
      and jsonb_typeof(naver_local_raw::jsonb)='object' as four_valid_json_objects
  from public.raw_api_data
)
select jsonb_build_object(
  'tourism_rows',(select count(*) from public.tourism_demand),
  'duplicate_keys',(select count(*) from duplicate_keys),
  'latest_tourism_date',(select max(reference_date) from public.tourism_demand),
  'latest_sample',(select jsonb_agg(s) from latest_sample s),
  'null_metric_rows',(select count(*) from public.tourism_demand where stay_strength is null or consumption_strength is null),
  'raw_columns',(select jsonb_agg(c order by ordinal_position) from raw_columns c),
  'raw_batches',(select jsonb_agg(r order by id) from raw_summary r),
  'raw_rls',(select relrowsecurity from pg_class where oid='public.raw_api_data'::regclass),
  'raw_anon_select',has_table_privilege('anon','public.raw_api_data','select')
) as lecture_step9_12_audit;
