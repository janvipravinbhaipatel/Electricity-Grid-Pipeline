
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    hour_start_utc as unique_field,
    count(*) as n_records

from "warehouse"."analytics"."fct_hourly"
where hour_start_utc is not null
group by hour_start_utc
having count(*) > 1



  
  
      
    ) dbt_internal_test