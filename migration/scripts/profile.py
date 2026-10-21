"""Inspect CSVs and the discovered database; emit reproducible aggregate evidence."""
import collections
import csv
import hashlib
import json
import math
from statistics import mean
from common import ROOT, save, sql_json


def main():
    rows = list(csv.DictReader((ROOT / 'data/amazon_delivery_cleaned.csv').open()))
    raw = list(csv.DictReader((ROOT / 'data/amazon_delivery.csv').open(), delimiter=';'))
    missing = {k: sum(r[k] == '' for r in rows) for k in rows[0]}
    coords = ['Store_Latitude', 'Store_Longitude', 'Drop_Latitude', 'Drop_Longitude']
    q = {
        'rows': len(rows), 'raw_rows': len(raw), 'columns': len(rows[0]),
        'duplicate_ids': len(rows) - len({r['Order_ID'] for r in rows}),
        'duplicate_rows': len(rows) - len({tuple(r.values()) for r in rows}),
        'missing': missing,
        'date_min': min(r['Order_Date'] for r in rows),
        'date_max': max(r['Order_Date'] for r in rows),
        'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [*ROOT.glob('data/*.csv'), *ROOT.glob('reports/*.pdf')]},
        'means': {k: mean(float(r[k]) for r in rows if r[k]) for k in
                  ['Delivery_Time', 'Distance_Km', 'Pickup_Delay_Min', 'Agent_Rating']},
        'ranges': {k: [min(float(r[k]) for r in rows if r[k]), max(float(r[k]) for r in rows if r[k])]
                   for k in ['Delivery_Time', 'Distance_Km', 'Pickup_Delay_Min', 'Agent_Age', 'Agent_Rating']},
        'long_flag_mismatch_gt_160': sum(int(r['Long_Delivery_Flag']) != int(float(r['Delivery_Time']) > 160) for r in rows),
        'invalid_coordinate_rows': sum(any(abs(float(r[c])) > (90 if 'Latitude' in c else 180) for c in coords) for r in rows),
        'zero_coordinate_rows': sum(any(float(r[c]) == 0 for c in coords) for r in rows),
        'raw_whitespace': {k: sum(r[k] != r[k].strip() for r in raw) for k in ['Traffic', 'Weather', 'Area', 'Vehicle']},
        'raw_missing': {k: sum(r[k].strip() in ('', 'NaN', 'nan') for r in raw) for k in raw[0]},
        'raw_only_ids': len({r['Order_ID'] for r in raw} - {r['Order_ID'] for r in rows}),
        'clean_only_ids': len({r['Order_ID'] for r in rows} - {r['Order_ID'] for r in raw}),
        'pickup_midnight_rows': sum(r['Pickup_Time'] < r['Order_Time'] for r in rows),
        'pickup_delay_modulo_mismatches': 0,
    }
    def minutes(t):
        h, m, s = map(int, t.split(':')); return h * 60 + m + s / 60
    q['pickup_delay_modulo_mismatches'] = sum(
        abs((minutes(r['Pickup_Time']) - minutes(r['Order_Time'])) % 1440 - float(r['Pickup_Delay_Min'])) > 1e-9 for r in rows)
    q['database'] = sql_json('''SELECT count(*) AS rows, count(DISTINCT order_id) AS distinct_ids,
        count(*) FILTER (WHERE order_id IS NULL) AS null_ids,
        min(order_date) AS date_min, max(order_date) AS date_max,
        avg(delivery_time) AS avg_delivery_time, avg(distance_km) AS avg_distance,
        avg(long_delivery_flag::numeric) AS long_delivery_rate,
        count(*) FILTER (WHERE agent_rating IS NULL) AS null_rating,
        count(*) FILTER (WHERE (delivery_time > 160)::int <> long_delivery_flag) AS flag_mismatches
        FROM public.amazon_delivery''')[0]
    # Exact identity and value comparison, normalized numeric representations.
    dbrows = sql_json('SELECT * FROM public.amazon_delivery')
    def canonical(r):
        numeric = {'Order_Hour','Day_Number','Agent_Age','Agent_Rating', *coords,
                   'Distance_Km','Pickup_Delay_Min','Delivery_Time','Long_Delivery_Flag'}
        return tuple(None if r.get(k.lower()) in (None, '') else float(r[k.lower()])
                     if k in numeric else str(r[k.lower()]) for k in rows[0])
    filemap = {r['Order_ID']: canonical({k.lower(): v for k, v in r.items()}) for r in rows}
    dbmap = {r['order_id']: canonical(r) for r in dbrows}
    q['database_csv_comparison'] = {
        'missing_ids': len(filemap.keys() - dbmap.keys()),
        'extra_ids': len(dbmap.keys() - filemap.keys()),
        'different_rows': sum(filemap[k] != dbmap[k] for k in filemap.keys() & dbmap.keys()),
    }
    q['database_fingerprint']=sql_json("SELECT md5(string_agg(row_to_json(b)::text, E'\\n' ORDER BY order_id)) AS digest FROM public.amazon_delivery b")[0]['digest']
    save('migration/evidence/data-profile.json', q)
    print(json.dumps({k: q[k] for k in ['rows','duplicate_ids','database_csv_comparison','zero_coordinate_rows','pickup_midnight_rows','pickup_delay_modulo_mismatches']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
