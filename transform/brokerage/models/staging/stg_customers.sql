select
    account_id,
    first_name,
    last_name,
    concat(first_name, ' ', last_name) as full_name,
    lower(email) as email,
    country,
    signup_date,
    account_status,
    date_diff(current_date(), signup_date, day) as days_since_signup

from {{ source('raw', 'customers') }}