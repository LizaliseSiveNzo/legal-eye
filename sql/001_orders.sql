-- Legal-Eye orders, for Supabase or any Postgres.
-- Mirrors backend/orders.py so SQLiteOrderStore can be swapped for
-- PostgresOrderStore without changing any caller.
--
-- Applied to Supabase project jyrzkfjvwtwaqiagjumg ("legal-eye", eu-west-3) on
-- 2026-08-16 as migration legal_eye_orders.
--
-- Kept out of the public schema even though the project is dedicated to
-- Legal-Eye. Supabase serves only the schemas listed in its API config, so a
-- table in legal_eye is unreachable through PostgREST by default. These rows
-- hold an email address and the full report body, and the cheapest way to
-- guarantee no browser ever reads them is for the API not to know they exist.
-- Set ORDERS_SCHEMA if you would rather use public.

create schema if not exists legal_eye;

create table if not exists legal_eye.orders (
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

create index if not exists orders_status_idx    on legal_eye.orders (status);
create index if not exists orders_email_idx     on legal_eye.orders (lower(email));
create index if not exists orders_delivered_idx on legal_eye.orders (delivered_at)
    where delivered_at is not null;

-- Orders hold an email address and the full report body, so no browser client
-- should ever read this table. RLS on, no policy, and the API roles revoked:
-- reachable only from the server with the service role, which bypasses RLS.
alter table legal_eye.orders enable row level security;

revoke all on schema legal_eye from anon, authenticated;
revoke all on legal_eye.orders from anon, authenticated;

-- POPIA s 14. Drop report bodies once they are no longer needed, keeping the
-- financial record. Schedule with pg_cron:
--   select cron.schedule('purge-reports','0 3 * * *',
--                        $$select legal_eye.purge_delivered_reports(30)$$);
create or replace function legal_eye.purge_delivered_reports(
    older_than_days integer default 30)
returns integer
language plpgsql
security definer
set search_path = legal_eye, pg_temp
as $$
declare
    purged integer;
begin
    update legal_eye.orders
       set report = null
     where status = 'delivered'
       and delivered_at is not null
       and delivered_at < now() - make_interval(days => older_than_days)
       and report is not null;
    get diagnostics purged = row_count;
    return purged;
end;
$$;

revoke all on function legal_eye.purge_delivered_reports(integer)
    from anon, authenticated, public;
