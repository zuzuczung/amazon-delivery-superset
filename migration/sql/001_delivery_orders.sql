-- Target is the existing tunglocaldb connection, NOT the Superset metadata DB.
-- Source has been discovered and checked: public.amazon_delivery (one row/order).
-- No source rows are changed; no join, imputation, deduplication or recleaning.
BEGIN;
CREATE SCHEMA IF NOT EXISTS amazon_bi;
DO $$
BEGIN
  IF to_regclass('amazon_bi.delivery_orders') IS NOT NULL AND
     obj_description(to_regclass('amazon_bi.delivery_orders'), 'pg_class') IS DISTINCT FROM
     'amazon-delivery-intelligence:superset-migration:v1' THEN
    RAISE EXCEPTION 'Refusing to replace an object not owned by this migration';
  END IF;
END $$;
CREATE OR REPLACE VIEW amazon_bi.delivery_orders AS
SELECT
  order_id, order_date, order_time, pickup_time, order_hour,
  day_name, day_number, agent_age, age_group, agent_rating,
  NULLIF(rating_group, '') AS rating_group,
  store_latitude, store_longitude, drop_latitude, drop_longitude,
  distance_km, pickup_delay_min, weather, traffic, vehicle, area, category,
  delivery_time, delivery_band, long_delivery_flag,
  -- Display helpers only; boundaries inferred from the PDF, not recovered DAX.
  lpad((floor(distance_km / 3)::int * 3)::text, 2, '0') || '–' ||
  lpad((floor(distance_km / 3)::int * 3 + 3)::text, 2, '0') || ' km' AS distance_band,
  day_number::text || ' · ' || day_name AS weekday_sorted
FROM public.amazon_delivery;
COMMENT ON VIEW amazon_bi.delivery_orders IS
  'amazon-delivery-intelligence:superset-migration:v1';
COMMIT;
