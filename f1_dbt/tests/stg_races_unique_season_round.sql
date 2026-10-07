-- Singular test: returns rows that violate uniqueness of (season, round).
-- The test passes when the query returns zero rows.
select
    season,
    round,
    count(*) as row_count
from {{ ref('stg_races') }}
group by season, round
having count(*) > 1
