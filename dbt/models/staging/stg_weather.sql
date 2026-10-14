select time_utc,temperature_c from {{ source('raw', 'raw_weather') }}
where temperature_c is not null
qualify row_number() over (
    partition by time_utc
    order by source_file 
) = 1
