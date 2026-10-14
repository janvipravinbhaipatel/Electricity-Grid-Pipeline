
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select hour_start_utc
from "warehouse"."analytics"."fct_hourly"
where hour_start_utc is null



  
  
      
    ) dbt_internal_test