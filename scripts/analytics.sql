-- Operational analytics over the jobs table (PostgreSQL).
--
-- Run against the compose stack:
--   docker compose exec -T postgres psql -U sigserve sigserve < scripts/analytics.sql
-- or in production:
--   docker compose -f docker-compose.prod.yml exec -T postgres \
--       psql -U sigserve sigserve < scripts/analytics.sql
--
-- Sections:
--   1. Daily outcomes and success rate, with a 7-day rolling rate
--   2. Queue latency (created -> started) percentiles per day
--   3. Sampler runtime by input size (matrix cell-count buckets)
--   4. Per-key usage ranking

-- 1. Daily outcomes and success rate.
--    Success rate counts only jobs the sampler decided (finished/failed);
--    cancellations are user actions, not service failures.
WITH daily AS (
    SELECT
        date_trunc('day', created_at) AS day,
        count(*) AS submitted,
        count(*) FILTER (WHERE status = 'finished') AS finished,
        count(*) FILTER (WHERE status = 'failed') AS failed,
        count(*) FILTER (WHERE status = 'canceled') AS canceled
    FROM jobs
    GROUP BY day
)
SELECT
    day::date AS day,
    submitted,
    finished,
    failed,
    canceled,
    round(100.0 * finished / nullif(finished + failed, 0), 1) AS success_pct,
    round(
        100.0 * sum(finished) OVER w / nullif(sum(finished + failed) OVER w, 0), 1
    ) AS success_pct_7d
FROM daily
WINDOW w AS (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY day;

-- 2. Queue latency: how long jobs sat queued before a worker picked them up.
WITH waits AS (
    SELECT
        date_trunc('day', created_at) AS day,
        extract(epoch FROM started_at - created_at) AS wait_s
    FROM jobs
    WHERE started_at IS NOT NULL
)
SELECT
    day::date AS day,
    count(*) AS jobs_started,
    round((percentile_cont(0.5) WITHIN GROUP (ORDER BY wait_s))::numeric, 2) AS p50_wait_s,
    round((percentile_cont(0.95) WITHIN GROUP (ORDER BY wait_s))::numeric, 2) AS p95_wait_s,
    round(max(wait_s)::numeric, 2) AS max_wait_s
FROM waits
GROUP BY day
ORDER BY day;

-- 3. Sampler runtime by input size. Cell count (types x samples) is the
--    driver of per-iteration cost; jobs predating the dimension columns
--    have NULL shape and are excluded.
WITH finished_jobs AS (
    SELECT
        n_mutation_types * n_samples AS cells,
        (params ->> 'rank')::int AS rank,
        extract(epoch FROM finished_at - started_at) AS runtime_s
    FROM jobs
    WHERE status = 'finished'
      AND n_mutation_types IS NOT NULL
      AND started_at IS NOT NULL
      AND finished_at IS NOT NULL
),
bucketed AS (
    SELECT
        width_bucket(cells, ARRAY[100, 1000, 10000, 100000]) AS bucket,
        rank,
        runtime_s
    FROM finished_jobs
)
SELECT
    CASE bucket
        WHEN 0 THEN '< 100 cells'
        WHEN 1 THEN '100 - 1k'
        WHEN 2 THEN '1k - 10k'
        WHEN 3 THEN '10k - 100k'
        ELSE '>= 100k'
    END AS input_size,
    count(*) AS jobs,
    round(avg(rank), 1) AS avg_rank,
    round((percentile_cont(0.5) WITHIN GROUP (ORDER BY runtime_s))::numeric, 1) AS p50_runtime_s,
    round((percentile_cont(0.95) WITHIN GROUP (ORDER BY runtime_s))::numeric, 1) AS p95_runtime_s
FROM bucketed
GROUP BY bucket
ORDER BY bucket;

-- 4. Per-key usage, ranked by submissions, with sampler time consumed.
WITH per_key AS (
    SELECT
        k.name,
        count(*) AS jobs,
        count(*) FILTER (WHERE j.status = 'failed') AS failed,
        sum(extract(epoch FROM j.finished_at - j.started_at))
            FILTER (WHERE j.status = 'finished') AS sampler_s
    FROM jobs j
    JOIN api_keys k ON k.id = j.api_key_id
    GROUP BY k.name
)
SELECT
    rank() OVER (ORDER BY jobs DESC) AS rank,
    name,
    jobs,
    failed,
    round(coalesce(sampler_s, 0)::numeric, 0) AS sampler_s
FROM per_key
ORDER BY jobs DESC, name;
