
  
    
    

    create  table
      "warehouse"."analytics"."fct_hourly__dbt_tmp"
  
    as (
      select
    d.hour_start_utc,
    d.date_est,
    d.hour_ending,
    dayname(d.date_est)  as day_of_week,
    month(d.date_est)    as month,
    d.ontario_demand_mw,
    d.market_demand_mw,
    w.temperature_c
from "warehouse"."analytics"."stg_demand" d
left join "warehouse"."analytics"."stg_weather" w
    on w.time_utc = d.hour_start_utc
    );
  
  