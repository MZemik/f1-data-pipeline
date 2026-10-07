-- Singular test: returns rows that violate uniqueness of (season, round, driver_id).
-- The test passes when the query returns zero rows.
select
    season,
    round,
    driver_id,
    count(*) as row_count
from {{ ref('stg_driver_standings') }}
group by season, round, driver_id
having count(*) > 1
