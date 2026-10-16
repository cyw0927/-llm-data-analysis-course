-- Supabase SQL Editor에서 Seed Import/Make Upsert 후 실행
select 'regions' as entity, count(*) as row_count from public.regions
union all select 'naver_trend', count(*) from public.naver_trend
union all select 'tourism_demand', count(*) from public.tourism_demand
union all select 'local_places', count(*) from public.local_places
union all select 'ai_region_analysis', count(*) from public.ai_region_analysis
union all select 'collection_runs', count(*) from public.collection_runs;

select reference_date, region_code, count(*) as duplicate_count
from public.tourism_demand
group by reference_date, region_code
having count(*) > 1;

select reference_date, keyword, count(*) as duplicate_count
from public.naver_trend
group by reference_date, keyword
having count(*) > 1;

select max(reference_date) as latest_trend from public.naver_trend;
select max(reference_date) as latest_tourism from public.tourism_demand;
select max(collected_at) as latest_local_place from public.local_places;
select max(analysis_date) as latest_ai from public.ai_region_analysis;

select * from public.latest_tourism_demand limit 30;
select * from public.latest_naver_trend limit 20;
select source, status, row_count, started_at, finished_at
from public.collection_runs
order by started_at desc limit 20;
