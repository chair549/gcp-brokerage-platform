with trades as (

    select * from {{ ref('fct_trades') }}

),

instruments as (

    select * from {{ ref('dim_instrument') }}

),

customers as (

    select * from {{ ref('dim_customer') }}

)

select
    t.trade_date,
    i.sector,
    c.country,
    count(*) as trade_count,
    count(distinct t.account_id) as active_accounts,
    round(sum(t.gross_value_aud), 2) as gross_value_aud,
    round(sum(t.fee_aud), 2) as revenue_aud,
    round(avg(t.seconds_to_fill), 1) as avg_seconds_to_fill

from trades t
left join instruments i on t.ticker = i.instrument_key
left join customers c on t.customer_key = c.customer_key

group by 1, 2, 3