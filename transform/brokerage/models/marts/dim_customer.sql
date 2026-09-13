with snapshot as (

    select * from {{ ref('customers_snapshot') }}

),

versioned as (

    select
        *,
        row_number() over (
            partition by account_id
            order by dbt_valid_from
        ) as version_number
    from snapshot

)

select
    dbt_scd_id as customer_key,
    account_id,
    concat(first_name, ' ', last_name) as full_name,
    lower(email) as email,
    country,
    account_status,
    signup_date,
    case
        when version_number = 1 then timestamp('1900-01-01')
        else dbt_valid_from
    end as valid_from,
    dbt_valid_to as valid_to,
    dbt_valid_to is null as is_current

from versioned