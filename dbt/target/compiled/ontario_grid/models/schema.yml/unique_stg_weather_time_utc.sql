
    
    

select
    time_utc as unique_field,
    count(*) as n_records

from "warehouse"."analytics"."stg_weather"
where time_utc is not null
group by time_utc
having count(*) > 1


