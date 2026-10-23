"""Read-only analysis to choose drill-down questions, not new dashboards.

New exploratory thresholds: severe >200 min, short route <5 km. Neither is
a promised SLA. Excess minutes above 160 describe severity, not savings.
"""
import csv
import hashlib
import json
import math
from collections import defaultdict
from statistics import mean, pstdev
from common import ROOT, save


def quantile(values, p):
    values = sorted(values)
    offset = (len(values)-1)*p
    low, high = math.floor(offset), math.ceil(offset)
    return values[low] + (values[high]-values[low])*(offset-low)


def metrics(rows):
    times = [float(r['Delivery_Time']) for r in rows]
    return dict(n=len(rows), long=sum(t>160 for t in times),
                severe=sum(t>200 for t in times),
                excess_minutes=sum(max(t-160,0) for t in times),
                avg=mean(times), p10=quantile(times,.1), p90=quantile(times,.9),
                p95=quantile(times,.95), sd=pstdev(times),
                long_rate=sum(t>160 for t in times)/len(rows))


def groups(rows, keys):
    result=defaultdict(list)
    for row in rows:
        result[tuple(row[key] for key in keys)].append(row)
    return result


def grouped_metrics(rows, keys):
    return [{**dict(zip(keys,key)), **metrics(items)}
            for key,items in groups(rows,keys).items()]


def standardized_vehicle(rows):
    # Direct standardization on common strata; selected vehicles only.
    vehicles=['motorcycle','scooter']
    strata=groups(rows,['Area','Traffic','Weather','distance_band'])
    eligible=[]
    for key,items in strata.items():
        by_vehicle=groups(items,['Vehicle'])
        if all(len(by_vehicle.get((v,),[]))>=20 for v in vehicles):
            eligible.append((key,by_vehicle))
    common_n=sum(len(by_vehicle[(v,)]) for _,by_vehicle in eligible for v in vehicles)
    estimates=[]
    for v in vehicles:
        selected=[r for _,by_vehicle in eligible for r in by_vehicle[(v,)]]
        adjusted=sum(mean(float(r['Delivery_Time']) for r in by_vehicle[(v,)]) *
                     sum(len(by_vehicle[(w,)]) for w in vehicles)/common_n
                     for _,by_vehicle in eligible)
        estimates.append(dict(vehicle=v, common_sample=len(selected),
                              common_unadjusted=metrics(selected)['avg'],
                              adjusted_avg=adjusted))
    target=[r for r in rows if r['Vehicle'] in vehicles]
    return dict(strata=len(eligible),common_n=common_n,total_eligible=len(target),
                coverage=common_n/len(target),minimum_per_vehicle_per_stratum=20,
                adjustment=['Area','Traffic','Weather','distance_band'],
                estimates=estimates,
                all_unadjusted=grouped_metrics(target,['Vehicle']))


def main():
    source=ROOT/'data/amazon_delivery_cleaned.csv'
    rows=list(csv.DictReader(source.open()))
    for r in rows:
        r['distance_band']=str(int(float(r['Distance_Km'])//3)*3)
    overall=metrics(rows)
    cells=sorted(grouped_metrics(rows,['Area','Traffic','Weather']),
                 key=lambda x:x['excess_minutes'],reverse=True)
    top=[x for x in cells if x['n']>=200][:5]
    short=[r for r in rows if float(r['Distance_Km'])<5]
    short_nonzero=[r for r in short if all(float(r[k])!=0 for k in
                   ['Store_Latitude','Store_Longitude','Drop_Latitude','Drop_Longitude'])]
    non_grocery=[r for r in rows if r['Category']!='Grocery']
    pickup=grouped_metrics(rows,['Pickup_Delay_Min'])
    pickup_means=[x['avg'] for x in pickup]
    categories=grouped_metrics(rows,['Category'])
    non_grocery_categories=[x for x in categories if x['Category']!='Grocery']
    result=dict(
        source='data/amazon_delivery_cleaned.csv', sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        period=[min(r['Order_Date'] for r in rows),max(r['Order_Date'] for r in rows)],
        grain='one order', overall=overall,
        quality=dict(duplicate_ids=len(rows)-len({r['Order_ID'] for r in rows}),
                     missing_ratings=sum(not r['Agent_Rating'] for r in rows),
                     zero_coordinates=sum(any(float(r[k])==0 for k in ['Store_Latitude','Store_Longitude','Drop_Latitude','Drop_Longitude']) for r in rows),
                     long_flag_mismatches=sum(int(r['Long_Delivery_Flag'])!=int(float(r['Delivery_Time'])>160) for r in rows)),
        by_area=grouped_metrics(rows,['Area']),by_traffic=grouped_metrics(rows,['Traffic']),
        joint_cells=top,
        top5=dict(n=sum(x['n'] for x in top),long=sum(x['long'] for x in top),
                  excess_minutes=sum(x['excess_minutes'] for x in top),
                  order_share=sum(x['n'] for x in top)/overall['n'],
                  long_share=sum(x['long'] for x in top)/overall['long'],
                  excess_share=sum(x['excess_minutes'] for x in top)/overall['excess_minutes']),
        short_routes=dict(**metrics(short), long_share=sum(float(r['Delivery_Time'])>160 for r in short)/overall['long']),
        short_routes_nonzero_coordinates=metrics(short_nonzero),
        pickup=dict(groups=pickup,avg_gap=max(pickup_means)-min(pickup_means)),
        categories=dict(groups=categories,non_grocery_avg_range=[min(x['avg'] for x in non_grocery_categories),max(x['avg'] for x in non_grocery_categories)]),
        vehicle_standardization_all=standardized_vehicle(rows),
        vehicle_standardization_non_grocery=standardized_vehicle(non_grocery),
    )
    save('migration/evidence/drilldown-opportunities.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
