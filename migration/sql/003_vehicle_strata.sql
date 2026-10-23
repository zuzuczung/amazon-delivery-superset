-- SELECT-only: one row per area × traffic × weather × 3 km distance band.
-- Fixed snapshot. No Grocery; motorcycle and scooter only.
WITH aggregated AS (
 SELECT area,traffic,weather,floor(distance_km/3)::int*3 AS distance_low,
        count(*) FILTER (WHERE vehicle='motorcycle') AS n_motor,
        count(*) FILTER (WHERE vehicle='scooter') AS n_scooter,
        coalesce(sum(delivery_time) FILTER (WHERE vehicle='motorcycle'),0) AS time_motor,
        coalesce(sum(delivery_time) FILTER (WHERE vehicle='scooter'),0) AS time_scooter
 FROM amazon_bi.delivery_orders
 WHERE order_date>=DATE '2022-02-11' AND order_date<DATE '2022-04-07'
   AND category<>'Grocery' AND vehicle IN ('motorcycle','scooter')
 GROUP BY area,traffic,weather,floor(distance_km/3)::int*3
), means AS (
 SELECT *,time_motor::double precision/nullif(n_motor,0) AS mean_motor,
          time_scooter::double precision/nullif(n_scooter,0) AS mean_scooter,
          n_motor+n_scooter AS pooled_n,
          n_motor>=20 AND n_scooter>=20 AS eligible,
          lpad(distance_low::text,2,'0') || '–' || lpad((distance_low+3)::text,2,'0') || ' km' AS distance_band
 FROM aggregated
)
SELECT *,mean_motor-mean_scooter AS gap,
       floor((mean_motor-mean_scooter)/5)::int*5 AS gap_bin,
       area || ' · ' || traffic || ' · ' || weather || ' · ' || distance_band AS group_label,
       CASE WHEN eligible THEN 'Đủ mẫu so sánh' ELSE 'Chưa đủ mẫu' END AS support_status
FROM means
