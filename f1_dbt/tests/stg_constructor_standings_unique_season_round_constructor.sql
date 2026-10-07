-- Singular test: returns rows that violate uniqueness of (season, round, constructor_id).
-- The test passes when the query returns zero rows.
select
    season,
    round,
    constructor_id,
    count(*) as row_count
from {{ ref('stg_constructor_standings') }}
group by season, round, constructor_id
having count(*) > 1
