with source as (
    select * from {{ source('bronze', 'driver_standings') }}
),

exploded as (
    select
        source.season,
        source.round,
        source._loaded_at,
        standing
    from source
    cross join lateral jsonb_array_elements(
        payload -> 'MRData' -> 'StandingsTable' -> 'StandingsLists' -> 0 -> 'DriverStandings'
    ) as standing
),

renamed as (
    select
        season,
        round,
        standing -> 'Driver' ->> 'driverId' as driver_id,
        standing -> 'Driver' ->> 'code' as driver_code,
        standing -> 'Driver' ->> 'givenName' as driver_given_name,
        standing -> 'Driver' ->> 'familyName' as driver_family_name,
        standing -> 'Constructors' -> 0 ->> 'constructorId' as constructor_id,
        standing -> 'Constructors' -> 0 ->> 'name' as constructor_name,
        (standing ->> 'position')::int as championship_position,
        standing ->> 'positionText' as position_text,
        (standing ->> 'points')::numeric as points,
        (standing ->> 'wins')::int as wins,
        _loaded_at
    from exploded
)

select * from renamed
