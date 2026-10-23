-- Read-only review of new descriptive measures; 160 is not a promised SLA.
WITH b AS (
  SELECT * FROM amazon_bi.delivery_orders
  WHERE order_date >= DATE '2022-02-11' AND order_date < DATE '2022-04-07'
), cells AS (
  SELECT area,traffic,weather,count(*) AS n,
         count(*) FILTER (WHERE delivery_time>160) AS long_n,
         sum(greatest(delivery_time-160,0)) AS excess
  FROM b GROUP BY area,traffic,weather
), top5 AS (
  SELECT * FROM cells WHERE n>=200 ORDER BY excess DESC LIMIT 5
)
SELECT count(*) AS n,
       count(*) FILTER (WHERE delivery_time>160) AS long_n,
       count(*) FILTER (WHERE delivery_time>200) AS severe_n,
       sum(greatest(delivery_time-160,0)) AS excess,
       (SELECT sum(n) FROM top5) AS top5_n,
       (SELECT sum(long_n) FROM top5) AS top5_long_n,
       (SELECT sum(excess) FROM top5) AS top5_excess,
       count(*) FILTER (WHERE distance_km<5 AND store_latitude<>0
          AND store_longitude<>0 AND drop_latitude<>0 AND drop_longitude<>0) AS short_nonzero_n,
       count(*) FILTER (WHERE distance_km<5 AND delivery_time>160
          AND store_latitude<>0 AND store_longitude<>0
          AND drop_latitude<>0 AND drop_longitude<>0) AS short_nonzero_long_n
FROM b;
