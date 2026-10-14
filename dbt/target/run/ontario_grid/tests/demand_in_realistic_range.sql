
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select *
from "warehouse"."analytics"."fct_hourly"
where ontario_demand_mw < 8000
   or ontario_demand_mw > 30000
  
  
      
    ) dbt_internal_test