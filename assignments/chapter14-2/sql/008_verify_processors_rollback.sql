-- Optional live unit verification for lecture STEP19-21.
-- Reprocesses the newest successful metric22 raw ONLY within a rolled-back transaction.
begin;
do $unit$
declare r public.raw_api_data%rowtype; n integer; t integer; p integer;
begin
  select * into strict r from public.raw_api_data
    where source='BATCH_RAW' and process_status='PROCESSED'
    order by id desc limit 1;
  n:=public.process_naver_trend_raw(r.id);
  t:=public.process_tourism_demand_raw(r.id);
  p:=public.process_naver_local_raw(r.id);
  if n<>(r.processed_counts->>'naver_trend')::integer
     or t<>26 or p<>(r.processed_counts->>'local_places')::integer
     or p not between 1 and 5 then
    raise exception 'PROCESSOR_ROW_COUNTS_MISMATCH';
  end if;
  if exists(select 1 from public.tourism_demand where raw_id=r.id
    and (stay_strength is null or consumption_strength is null or consumption_metric_code is distinct from '22')) then
    raise exception 'INCOMPLETE_OR_WRONG_TOURISM_METRIC';
  end if;
end;
$unit$;
rollback;
select jsonb_build_object('processor_rollback_test','PASS','latest_raw_id',r.id,
  'counts',r.processed_counts,'status',r.process_status) as processor_rollback_audit
from public.raw_api_data r where r.source='BATCH_RAW' and r.process_status='PROCESSED'
order by r.id desc limit 1;
