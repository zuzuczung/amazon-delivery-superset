"""Boundary tests that matter when translating DAX-like aggregations to SQL."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify import measures,quantile,expected


def order(key,t,flag=0,rating='4.5',area='Urban',traffic='Low'):
    return dict(order_id=key,delivery_time=str(t),distance_km='3',pickup_delay_min='10',
                long_delivery_flag=str(flag),agent_rating=rating,area=area,traffic=traffic)


class MetricSemantics(unittest.TestCase):
    def test_percentile_linear_interpolation(self):
        self.assertEqual(quantile([10,20,30,40],.9),37)
        self.assertEqual(quantile([1,5],.5),3)

    def test_empty_not_zero_for_average_or_rate(self):
        x=measures([]);self.assertEqual(x['orders'],0)
        self.assertIsNone(x['avg_time']);self.assertIsNone(x['long_rate']);self.assertIsNone(x['p90'])

    def test_null_rating_excluded_without_excluding_order(self):
        x=measures([order('a',100,rating=None),order('b',200,1,rating='5')])
        self.assertEqual(x['orders'],2);self.assertEqual(x['rating'],5);self.assertEqual(x['long_rate'],.5)

    def test_total_is_weighted_by_orders(self):
        rows=[order('a',200,1,area='Semi-Urban')]+[order(str(i),100,area='Urban') for i in range(9)]
        _,groups=expected(rows,dict(dataset='area_matrix',dimension='matrix_area',columns='matrix_traffic'))
        self.assertEqual(groups[('Total','Total')]['long_rate'],.1)
        self.assertEqual(groups[('Total','Total')]['avg_time'],110)
        self.assertEqual(groups[('Urban','Total')]['orders'],9)


if __name__=='__main__':unittest.main()
