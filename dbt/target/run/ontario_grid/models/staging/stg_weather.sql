
  
  create view "warehouse"."analytics"."stg_weather__dbt_tmp" as (
    select time_utc,temperature_c from "warehouse"."main"."raw_weather"
where temperature_c is not null
qualify row_number() over (
    partition by time_utc
    order by source_file 
) = 1
  );
