select *
from "warehouse"."analytics"."fct_hourly"
where temperature_c < -40
   or temperature_c > 45