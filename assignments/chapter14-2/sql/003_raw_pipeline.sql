-- Additive migration: preserve existing tables, rows and policies.
-- Run as postgres in the existing Supabase SQL Editor. No external requests.
begin;
create table if not exists public.raw_api_data (
  id bigint generated always as identity primary key,
  run_id uuid not null default gen_random_uuid() unique,
  source text not null default 'BATCH_RAW',
  naver_trend_raw text not null,
  tourism_demand_raw text not null,
  tourism_consumption_raw text not null,
  naver_local_raw text not null,
  fetched_at timestamptz not null default now(),
  process_status text not null default 'PENDING'
    check (process_status in ('PENDING','PROCESSED','ERROR')),
  processed_at timestamptz,
  error_message text,
  processed_counts jsonb
);
alter table public.raw_api_data enable row level security;
revoke all on public.raw_api_data from public, anon, authenticated;
revoke all on sequence public.raw_api_data_id_seq from public, anon, authenticated;
grant all on public.raw_api_data to service_role;
grant usage, select on sequence public.raw_api_data_id_seq to service_role;
alter table public.naver_trend add column if not exists raw_id bigint references public.raw_api_data(id) on delete set null;
alter table public.tourism_demand add column if not exists raw_id bigint references public.raw_api_data(id) on delete set null;
alter table public.local_places add column if not exists raw_id bigint references public.raw_api_data(id) on delete set null;
create index if not exists naver_trend_raw_id_idx on public.naver_trend(raw_id);
create index if not exists tourism_demand_raw_id_idx on public.tourism_demand(raw_id);
create index if not exists local_places_raw_id_idx on public.local_places(raw_id);

create or replace function public.process_naver_trend_raw(p_raw_id bigint)
returns integer language plpgsql set search_path = '' as $$
declare
  payload jsonb; g jsonb; point jsonb; day date; title text; ratio numeric;
  seen text[] := '{}'; identity_key text; n integer := 0;
begin
  select naver_trend_raw::jsonb into strict payload from public.raw_api_data where id=p_raw_id;
  if jsonb_typeof(payload->'results') is distinct from 'array'
     or jsonb_array_length(payload->'results')<>4 then
    raise exception 'INVALID_TREND_GROUPS';
  end if;
  for g in select value from jsonb_array_elements(payload->'results') loop
    title := btrim(g->>'title');
    if title is null or not title=any(array['여행','축제','캠핑','맛집'])
       or jsonb_typeof(g->'data') is distinct from 'array'
       or jsonb_array_length(g->'data')=0 then raise exception 'INVALID_TREND_DATA'; end if;
    for point in select value from jsonb_array_elements(g->'data') loop
      if coalesce(point->>'period','') !~ '^\d{4}-\d{2}-\d{2}$'
         or coalesce(point->>'ratio','') !~ '^\d+(\.\d+)?$' then raise exception 'INVALID_TREND_POINT'; end if;
      day := (point->>'period')::date; ratio := (point->>'ratio')::numeric;
      if ratio not between 0 and 100 then raise exception 'INVALID_TREND_RATIO'; end if;
      identity_key := day::text||'|'||title;
      if identity_key=any(seen) then raise exception 'DUPLICATE_TREND_POINT'; end if;
      seen := array_append(seen,identity_key);
      insert into public.naver_trend(reference_date,keyword,ratio,raw_id,collected_at)
      values(day,title,ratio,p_raw_id,now())
      on conflict(reference_date,keyword) do update set
        ratio=excluded.ratio,raw_id=excluded.raw_id,collected_at=excluded.collected_at;
      n:=n+1;
    end loop;
  end loop;
  -- Every group must cover exactly the same months and titles must be unique.
  if (select count(distinct value->>'title') from jsonb_array_elements(payload->'results'))<>4
     or exists(select 1 from public.naver_trend where raw_id=p_raw_id group by reference_date having count(*)<>4)
     then raise exception 'MISMATCHED_TREND_PERIODS'; end if;
  return n;
end;
$$;

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
    if item->>'areaCd' is distinct from '11' or item->>'tarExpDsIxCd' is distinct from '2201'
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
    insert into public.tourism_demand(reference_date,region_code,stay_strength,consumption_strength,raw_id,collected_at)
    values((ym||'01')::date,code,s_value,c_value,p_raw_id,now())
    on conflict(reference_date,region_code) do update set stay_strength=excluded.stay_strength,
      consumption_strength=excluded.consumption_strength,raw_id=excluded.raw_id,collected_at=excluded.collected_at;
    n:=n+1;
  end loop;
  return n;
end;
$$;

create or replace function public.process_naver_local_raw(p_raw_id bigint)
returns integer language plpgsql set search_path = '' as $$
declare
  payload jsonb; item jsonb; title text; address_text text; district text; code text;
  lon double precision; lat double precision; key text; seen text[] := '{}'; n integer:=0;
begin
  select naver_local_raw::jsonb into strict payload from public.raw_api_data where id=p_raw_id;
  if jsonb_typeof(payload->'items') is distinct from 'array' then raise exception 'INVALID_LOCAL_ITEMS'; end if;
  if jsonb_array_length(payload->'items') not between 1 and 5 then raise exception 'EMPTY_OR_EXCESS_LOCAL_ITEMS'; end if;
  for item in select value from jsonb_array_elements(payload->'items') loop
    title:=btrim(regexp_replace(item->>'title','<[^>]*>','','g'));
    title:=replace(replace(replace(replace(replace(title,'&amp;','&'),'&quot;','"'),'&#39;',''''),'&lt;','<'),'&gt;','>');
    address_text:=btrim(coalesce(nullif(item->>'roadAddress',''),item->>'address'));
    if coalesce(title,'')='' or coalesce(address_text,'') !~ '^(서울특별시|서울) ' then raise exception 'INVALID_LOCAL_IDENTITY'; end if;
    district:=split_part(address_text,' ',2);
    select region_code into strict code from public.regions where region_name=district and length(region_code)=5 and region_code like '11%';
    lon:=(item->>'mapx')::double precision; lat:=(item->>'mapy')::double precision;
    if abs(lon)>1000000 and abs(lat)>1000000 and trunc(lon)=lon and trunc(lat)=lat then
      lon:=lon/10000000;lat:=lat/10000000;
    end if;
    if lon is null or lat is null or lon not between 124 and 132 or lat not between 33 and 39 then raise exception 'INVALID_LOCAL_COORDINATES'; end if;
    -- Keep Python seed's SHA256 identity/category; don't duplicate its existing places.
    key:=encode(sha256(convert_to(code||'|관광명소|'||title||'|'||address_text,'UTF8')),'hex');
    if key=any(seen) then raise exception 'DUPLICATE_LOCAL_PLACE'; end if;
    seen:=array_append(seen,key);
    insert into public.local_places(place_key,region_code,search_category,name,category,address,road_address,longitude,latitude,source_link,raw_id)
    values(key,code,'관광명소',title,item->>'category',item->>'address',item->>'roadAddress',lon,lat,
      case when item->>'link' ~ '^https?://' then item->>'link' else null end,p_raw_id)
    on conflict(place_key) do update set category=excluded.category,address=excluded.address,
      road_address=excluded.road_address,longitude=excluded.longitude,latitude=excluded.latitude,
      source_link=excluded.source_link,raw_id=excluded.raw_id,collected_at=now(),updated_at=now();
    n:=n+1;
  end loop;
  return n;
end;
$$;

create or replace function public.trigger_process_batch_raw()
returns trigger language plpgsql set search_path = '' as $$
declare n integer; t integer; l integer;
begin
  -- Subtransaction: any processor failure rolls back ALL derived writes,
  -- but preserves the raw row and a safe error code for investigation.
  begin
    if new.source<>'BATCH_RAW' then raise exception 'UNSUPPORTED_SOURCE'; end if;
    n:=public.process_naver_trend_raw(new.id);
    t:=public.process_tourism_demand_raw(new.id);
    l:=public.process_naver_local_raw(new.id);
    if n=0 or t=0 or l=0 then raise exception 'EMPTY_BATCH'; end if;
    update public.raw_api_data set process_status='PROCESSED',processed_at=now(),error_message=null,
      processed_counts=jsonb_build_object('naver_trend',n,'tourism_demand',t,'local_places',l) where id=new.id;
  exception when others then
    -- SQLERRM may include raw payload/credentials: persist only SQLSTATE.
    update public.raw_api_data set process_status='ERROR',processed_at=now(),
      error_message='BATCH_VALIDATION_FAILED ['||sqlstate||']',processed_counts=null where id=new.id;
  end;
  return new;
end;
$$;
revoke all on function public.process_naver_trend_raw(bigint), public.process_tourism_demand_raw(bigint),
  public.process_naver_local_raw(bigint),public.trigger_process_batch_raw() from public, anon, authenticated;
grant execute on function public.process_naver_trend_raw(bigint),public.process_tourism_demand_raw(bigint),
  public.process_naver_local_raw(bigint),public.trigger_process_batch_raw() to service_role;
create or replace trigger after_insert_batch_raw after insert on public.raw_api_data
for each row execute function public.trigger_process_batch_raw();
commit;
