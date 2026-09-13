select
    ticker,
    company_name,
    sector,
    exchange

from {{ source('raw', 'instruments') }}