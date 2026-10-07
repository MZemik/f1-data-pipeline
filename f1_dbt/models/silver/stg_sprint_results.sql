with source as (
    select * from {{ source('bronze', 'sprint_results') }}
),

exploded as (
    select
        source.season,
        source.round,
        source._loaded_at,
        result
    from source
    cross join lateral jsonb_array_elements(
        payload -> 'MRData' -> 'RaceTable' -> 'Races' -> 0 -> 'SprintResults'
    ) as result
),

renamed as (
    select
        season,
        round,
        result -> 'Driver' ->> 'driverId' as driver_id,
        result -> 'Driver' ->> 'code' as driver_code,
        result -> 'Driver' ->> 'givenName' as driver_given_name,
        result -> 'Driver' ->> 'familyName' as driver_family_name,
        (result -> 'Driver' ->> 'dateOfBirth')::date as driver_date_of_birth,
        result -> 'Driver' ->> 'nationality' as driver_nationality,
        (result -> 'Driver' ->> 'permanentNumber')::int as driver_permanent_number,
        result -> 'Constructor' ->> 'constructorId' as constructor_id,
        result -> 'Constructor' ->> 'name' as constructor_name,
        result -> 'Constructor' ->> 'nationality' as constructor_nationality,
        (result ->> 'number')::int as car_number,
        (result ->> 'grid')::int as grid_position,
        (result ->> 'position')::int as finish_position,
        result ->> 'positionText' as position_text,
        (result ->> 'points')::numeric as points,
        (result ->> 'laps')::int as laps_completed,
        result ->> 'status' as status,
        (result -> 'Time' ->> 'millis')::bigint as race_time_ms,
        (result -> 'FastestLap' ->> 'rank')::int as fastest_lap_rank,
        (result -> 'FastestLap' ->> 'lap')::int as fastest_lap_number,
        result -> 'FastestLap' -> 'Time' ->> 'time' as fastest_lap_time,
        _loaded_at
    from exploded
)

select * from renamed
