import importlib.util
import tempfile
import unittest
from pathlib import Path

from scipy.optimize import linear_sum_assignment


REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "astro" / "wfg" / "call_hungarian.py"
SPEC = importlib.util.spec_from_file_location("astro_call_hungarian", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HungarianAssignmentTests(unittest.TestCase):
    def test_returns_minimum_cost_column_mapping_without_external_python2(self):
        cost = [[4, 1, 3], [2, 0, 5], [3, 2, 2]]
        expected_rows, expected_columns = linear_sum_assignment(cost)

        with tempfile.TemporaryDirectory() as tmp:
            mapping = MODULE.call_hungarian(cost, tmp)

        self.assertEqual(mapping[0], expected_columns.tolist())
        self.assertEqual(mapping[1], [expected_rows.tolist()[expected_columns.tolist().index(i)] for i in range(3)])
        self.assertEqual(sum(cost[i][mapping[0][i]] for i in range(3)), 5)

    def test_returns_inverse_column_to_row_mapping_for_three_cycle(self):
        cost = [[10, 0, 10], [10, 10, 0], [0, 10, 10]]

        with tempfile.TemporaryDirectory() as tmp:
            row_to_column, column_to_row = MODULE.call_hungarian(cost, tmp)

        self.assertEqual(row_to_column, [1, 2, 0])
        self.assertEqual(column_to_row, [2, 0, 1])
        self.assertEqual(sum(cost[row][row_to_column[row]] for row in range(3)), 0)


if __name__ == "__main__":
    unittest.main()