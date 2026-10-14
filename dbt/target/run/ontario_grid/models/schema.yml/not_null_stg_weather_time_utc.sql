
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select time_utc
from "warehouse"."analytics"."stg_weather"
where time_utc is null



  
  
      
    ) dbt_internal_test