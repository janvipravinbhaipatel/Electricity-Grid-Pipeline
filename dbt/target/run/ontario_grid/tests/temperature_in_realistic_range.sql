
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select *
from "warehouse"."analytics"."fct_hourly"
where temperature_c < -40
   or temperature_c > 45
  
  
      
    ) dbt_internal_test