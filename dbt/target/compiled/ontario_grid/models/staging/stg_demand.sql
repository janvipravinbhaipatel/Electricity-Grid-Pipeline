select
    date                                                 as date_est,
    hour_ending,
    cast(date as timestamp) + to_hours(hour_ending + 4)  as hour_start_utc,
    ontario_demand_mw,
    market_demand_mw
from "warehouse"."main"."raw_demand"
where hour_ending between 1 and 24
qualify row_number() over (
    partition by date, hour_ending
    order by source_file desc
) = 1