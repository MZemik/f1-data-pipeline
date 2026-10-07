with source as (
    select * from {{ source('bronze', 'races') }}
),

renamed as (
    select
        season,
        round,
        payload ->> 'raceName' as race_name,
        payload -> 'Circuit' -> 'Location' ->> 'country' as country,
        payload -> 'Circuit' -> 'Location' ->> 'locality' as locality,
        (payload -> 'Circuit' -> 'Location' ->> 'lat')::numeric as latitude,
        (payload -> 'Circuit' -> 'Location' ->> 'long')::numeric as longitude,
        payload -> 'Circuit' ->> 'circuitId' as circuit_id,
        payload -> 'Circuit' ->> 'circuitName' as circuit_name,
        (payload ->> 'date')::date as race_date,
        (payload ->> 'time')::time as race_time_utc,
        payload ? 'Sprint' as is_sprint_weekend,
        (payload -> 'Sprint' ->> 'date')::date as sprint_date,
        (payload -> 'Sprint' ->> 'time')::time as sprint_time_utc,
        _loaded_at
    from source
)

select * from renamed