
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ontario_demand_mw
from "warehouse"."analytics"."stg_demand"
where ontario_demand_mw is null



  
  
      
    ) dbt_internal_test