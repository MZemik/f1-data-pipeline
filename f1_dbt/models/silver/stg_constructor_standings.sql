with source as (
    select * from {{ source('bronze', 'constructor_standings') }}
),

exploded as (
    select
        source.season,
        source.round,
        source._loaded_at,
        standing
    from source
    cross join lateral jsonb_array_elements(
        payload -> 'MRData' -> 'StandingsTable' -> 'StandingsLists' -> 0 -> 'ConstructorStandings'
    ) as standing
),

renamed as (
    select
        season,
        round,
        standing -> 'Constructor' ->> 'constructorId' as constructor_id,
        standing -> 'Constructor' ->> 'name' as constructor_name,
        standing -> 'Constructor' ->> 'nationality' as constructor_nationality,
        (standing ->> 'position')::int as championship_position,
        standing ->> 'positionText' as position_text,
        (standing ->> 'points')::numeric as points,
        (standing ->> 'wins')::int as wins,
        _loaded_at
    from exploded
)

select * from renamed
