with source as (

    select * from {{ source('raw', 'trading_events') }}

),

deduplicated as (

    select
        *,
        row_number() over (
            partition by event_id
            order by ingested_at
        ) as rn
    from source

)

select
    event_id,
    event_type,
    event_timestamp,
    order_id,
    account_id,
    ticker,
    side,
    quantity,
    order_type,
    limit_price_usd,
    fill_price_usd,
    fee_usd,
    reason as cancellation_reason,
    ingested_at,
    date(event_timestamp) as event_date

from deduplicated
where rn = 1