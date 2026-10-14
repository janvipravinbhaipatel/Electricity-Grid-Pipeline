select *
from "warehouse"."analytics"."fct_hourly"
where ontario_demand_mw < 8000
   or ontario_demand_mw > 30000