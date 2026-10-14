
    
    

select
    hour_start_utc as unique_field,
    count(*) as n_records

from "warehouse"."analytics"."stg_demand"
where hour_start_utc is not null
group by hour_start_utc
having count(*) > 1


