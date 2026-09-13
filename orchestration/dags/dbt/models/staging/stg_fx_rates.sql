select
    rate_date,
    base_currency,
    quote_currency,
    rate as aud_usd_rate,
    1.0 / nullif(rate, 0) as usd_aud_rate

from {{ source('raw', 'fx_rates') }}