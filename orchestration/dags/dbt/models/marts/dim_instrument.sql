select
    ticker as instrument_key,
    ticker,
    company_name,
    sector,
    exchange

from {{ ref('stg_instruments') }}