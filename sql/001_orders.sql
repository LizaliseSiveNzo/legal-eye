-- Legal-Eye orders, for Supabase or any Postgres.
-- Mirrors backend/orders.py so SQLiteOrderStore can be swapped for a Supabase
-- store without changing any caller.

create table if not exists orders (
    id                 text primary key,
    email              text        not null,
    document_names     jsonb       not null default '[]'::jsonb,
    amount_cents       integer     not null check (amount_cents >= 0),
    currency           text        not null default 'ZAR',
    status             text        not null default 'pending'
                                   check (status in ('pending','paid','delivered',
                                                     'failed','refunded')),
    risk_score         integer     check (risk_score between 1 and 10),
    risk_band          text,
    report             text,
    provider           text,
    provider_reference text,
    marketing_opt_in   boolean     not null default false,
    -- ECTA s 42(2)(d): consent to immediate delivery, separately recorded.
    immediate_delivery_consent boolean not null default false,
    consent_at         timestamptz,
    created_at         timestamptz not null default now(),
    paid_at            timestamptz,
    delivered_at       timestamptz,
    failure_reason     text
);

create index if not exists orders_status_idx     on orders (status);
create index if not exists orders_email_idx      on orders (lower(email));
create index if not exists orders_delivered_idx  on orders (delivered_at)
    where delivered_at is not null;

-- Orders hold an email address and the full report, so no browser client should
-- ever read this table directly. Enable RLS with no public policy and reach it
-- only from the server using the service role key.
alter table orders enable row level security;

-- POPIA s 14. Drop report bodies once they are no longer needed, keeping the
-- financial record. Schedule with pg_cron:
--   select cron.schedule('purge-reports','0 3 * * *',
--                        $$select purge_delivered_reports(30)$$);
create or replace function purge_delivered_reports(older_than_days integer default 30)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
    purged integer;
begin
    update orders
       set report = null
     where status = 'delivered'
       and delivered_at is not null
       and delivered_at < now() - make_interval(days => older_than_days)
       and report is not null;
    get diagnostics purged = row_count;
    return purged;
end;
$$;
