with fills as (

    select
        event_id,
        order_id,
        account_id,
        ticker,
        event_timestamp,
        event_date,
        quantity,
        fill_price_usd,
        fee_usd
    from {{ ref('stg_trading_events') }}
    where event_type = 'order_filled'

),

orders as (

    select
        order_id,
        side,
        order_type,
        event_timestamp as placed_at
    from {{ ref('stg_trading_events') }}
    where event_type = 'order_placed'

),

fx as (

    select
        rate_date,
        aud_usd_rate
    from {{ ref('stg_fx_rates') }}

),

customers as (

    select
        customer_key,
        account_id,
        valid_from,
        valid_to
    from {{ ref('dim_customer') }}

)

select
    f.event_id as trade_key,
    f.order_id,
    f.account_id,
    c.customer_key,
    f.ticker,
    o.side,
    o.order_type,
    f.event_timestamp as filled_at,
    o.placed_at,
    timestamp_diff(f.event_timestamp, o.placed_at, second) as seconds_to_fill,
    f.quantity,
    f.fill_price_usd,
    f.quantity * f.fill_price_usd as gross_value_usd,
    f.fee_usd,
    fx.aud_usd_rate,
    round(f.quantity * f.fill_price_usd / nullif(fx.aud_usd_rate, 0), 2) as gross_value_aud,
    round(f.fee_usd / nullif(fx.aud_usd_rate, 0), 2) as fee_aud,
    f.event_date as trade_date

from fills f
left join orders o
    on f.order_id = o.order_id
left join fx
    on f.event_date = fx.rate_date
left join customers c
    on f.account_id = c.account_id
    and f.event_timestamp >= c.valid_from
    and (f.event_timestamp < c.valid_to or c.valid_to is null)