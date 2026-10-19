-- Correct the metric, preserve existing values and their original provenance.
-- 22 = tourism consumption strength; 2201 = outsider consumption amount (submetric).
-- Does not recollect or replace existing observations. Archive legacy observations
-- before future genuine metric-22 batches may update the current dashboard table.
begin;
alter table public.tourism_demand add column if not exists consumption_metric_code text;
-- Infer metadata only from the linked raw response, never from its numeric value.
update public.tourism_demand d set consumption_metric_code=(
  select item->>'tarExpDsIxCd' from public.raw_api_data r,
    lateral jsonb_array_elements(r.tourism_consumption_raw::jsonb#>'{response,body,items,item}') item
  where r.id=d.raw_id and item->>'baseYm'=to_char(d.reference_date,'YYYYMM')
    and case when coalesce(item->>'signguCd','') in ('','0','_') then item->>'areaCd' else item->>'signguCd' end=d.region_code
) where d.consumption_metric_code is null and d.raw_id is not null;
create table if not exists public.tourism_demand_metric_archive (
  id bigint generated always as identity primary key,
  source_row_id bigint not null,
  metric_code text not null,
  raw_id bigint references public.raw_api_data(id) on delete set null,
  row_snapshot jsonb not null,
  snapshot_fingerprint text not null unique,
  archived_at timestamptz not null default now()
);
alter table public.tourism_demand_metric_archive enable row level security;
revoke all on public.tourism_demand_metric_archive from public,anon,authenticated;
revoke all on sequence public.tourism_demand_metric_archive_id_seq from public,anon,authenticated;
grant all on public.tourism_demand_metric_archive to service_role;
grant usage,select on sequence public.tourism_demand_metric_archive_id_seq to service_role;
insert into public.tourism_demand_metric_archive(source_row_id,metric_code,raw_id,row_snapshot,snapshot_fingerprint)
select d.id,d.consumption_metric_code,d.raw_id,to_jsonb(d),md5(to_jsonb(d)::text)
from public.tourism_demand d where d.consumption_metric_code='2201'
on conflict(snapshot_fingerprint) do nothing;
create or replace function public.process_tourism_demand_raw(p_raw_id bigint)
returns integer language plpgsql set search_path = '' as $$
declare
  stay jsonb; spend jsonb; s_items jsonb; c_items jsonb; item jsonb; match_item jsonb;
  ym text; code text; identity_key text; seen text[] := '{}'; c_seen text[] := '{}';
  s_value numeric; c_value numeric; n integer := 0; matches integer;
begin
  select tourism_demand_raw::jsonb,tourism_consumption_raw::jsonb
    into strict stay,spend from public.raw_api_data where id=p_raw_id;
  if coalesce(stay#>>'{response,header,resultCode}','') not in ('0000','00','0')
     or coalesce(spend#>>'{response,header,resultCode}','') not in ('0000','00','0') then
    raise exception 'TOURISM_API_ERROR'; end if;
  s_items := stay#>'{response,body,items,item}'; c_items := spend#>'{response,body,items,item}';
  if jsonb_typeof(s_items)='object' then s_items:=jsonb_build_array(s_items); end if;
  if jsonb_typeof(c_items)='object' then c_items:=jsonb_build_array(c_items); end if;
  if jsonb_typeof(s_items) is distinct from 'array' or jsonb_typeof(c_items) is distinct from 'array'
     then raise exception 'INVALID_TOURISM_ITEMS'; end if;
  if jsonb_array_length(s_items)=0 or jsonb_array_length(s_items)<>jsonb_array_length(c_items)
     or jsonb_array_length(s_items)<>coalesce((stay#>>'{response,body,totalCount}')::integer,-1)
     or jsonb_array_length(c_items)<>coalesce((spend#>>'{response,body,totalCount}')::integer,-1)
     then raise exception 'INCOMPLETE_TOURISM_PAGE'; end if;
  if jsonb_array_length(s_items)<>(select count(*) from public.regions where region_code='11' or region_code ~ '^11\d{3}$')
     or (select count(distinct value->>'baseYm') from jsonb_array_elements(s_items))<>1 then
    raise exception 'INCOMPLETE_SEOUL_COVERAGE'; end if;
  -- Validate both sides before joining; no duplicate/extra/unmatched consumption keys.
  for item in select value from jsonb_array_elements(c_items) loop
    code:=case when coalesce(item->>'signguCd','') in ('','0','_') then item->>'areaCd' else item->>'signguCd' end;
    identity_key:=coalesce(item->>'baseYm','')||'|'||coalesce(code,'');
    if identity_key=any(c_seen) then raise exception 'DUPLICATE_CONSUMPTION_KEY'; end if;
    c_seen:=array_append(c_seen,identity_key);
    if item->>'areaCd' is distinct from '11' or item->>'tarExpDsIxCd' is distinct from '22'
      then raise exception 'UNEXPECTED_CONSUMPTION_METRIC'; end if;
  end loop;
  for item in select value from jsonb_array_elements(s_items) loop
    ym:=item->>'baseYm';
    code:=case when coalesce(item->>'signguCd','') in ('','0','_') then item->>'areaCd' else item->>'signguCd' end;
    if coalesce(ym,'') !~ '^\d{4}(0[1-9]|1[0-2])$' or coalesce(code,'') !~ '^11(\d{3})?$'
       or item->>'areaCd' is distinct from '11' or item->>'tarSjrnDsIxCd' is distinct from '21'
       or not exists(select 1 from public.regions where region_code=code)
       then raise exception 'INVALID_TOURISM_IDENTITY'; end if;
    identity_key:=ym||'|'||code;
    if identity_key=any(seen) then raise exception 'DUPLICATE_STAY_KEY'; end if;
    seen:=array_append(seen,identity_key);
    select count(*) into matches from jsonb_array_elements(c_items) c
      where c->>'baseYm'=ym and
      case when coalesce(c->>'signguCd','') in ('','0','_') then c->>'areaCd' else c->>'signguCd' end=code;
    if matches<>1 then raise exception 'UNMATCHED_TOURISM_KEY'; end if;
    select c into match_item from jsonb_array_elements(c_items) c
      where c->>'baseYm'=ym and
      case when coalesce(c->>'signguCd','') in ('','0','_') then c->>'areaCd' else c->>'signguCd' end=code;
    if coalesce(item->>'tarSjrnDsIxVal','') !~ '^\d+(\.\d+)?$'
       or coalesce(match_item->>'tarExpDsIxVal','') !~ '^\d+(\.\d+)?$'
       then raise exception 'INVALID_TOURISM_VALUE'; end if;
    s_value:=(item->>'tarSjrnDsIxVal')::numeric; c_value:=(match_item->>'tarExpDsIxVal')::numeric;
    insert into public.tourism_demand(reference_date,region_code,stay_strength,consumption_strength,consumption_metric_code,raw_id,collected_at)
    values((ym||'01')::date,code,s_value,c_value,'22',p_raw_id,now())
    on conflict(reference_date,region_code) do update set stay_strength=excluded.stay_strength,
      consumption_strength=excluded.consumption_strength,consumption_metric_code=excluded.consumption_metric_code,raw_id=excluded.raw_id,collected_at=excluded.collected_at;
    n:=n+1;
  end loop;
  return n;
end;
$$;


revoke all on function public.process_tourism_demand_raw(bigint) from public,anon,authenticated;
grant execute on function public.process_tourism_demand_raw(bigint) to service_role;
commit;
