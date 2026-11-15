import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import numpy as np
from osgeo import gdal
from src.map_proccesing import Traversability

class EnclosureTests(unittest.TestCase):
    def run_case(self, values, expected):
        values = np.asarray(values, dtype=np.float32)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cost.tif'
            ds = gdal.GetDriverByName('GTiff').Create(str(path), values.shape[1], values.shape[0], 1, gdal.GDT_Float32)
            transform = (100, 1, 0, 200, 0, -1)
            ds.SetGeoTransform(transform)
            ds.GetRasterBand(1).SetNoDataValue(-9999)
            ds.GetRasterBand(1).WriteArray(values)
            ds = None
            processor = Traversability(block_size=2)
            processor.log = Mock()
            changed = processor.mark_enclosed_regions(path)
            ds = gdal.Open(str(path))
            np.testing.assert_array_equal(ds.ReadAsArray(), np.asarray(expected, dtype=np.float32))
            self.assertEqual(ds.GetGeoTransform(), transform)
            self.assertEqual(ds.GetRasterBand(1).GetNoDataValue(), -9999)
            self.assertEqual(changed, np.count_nonzero(values != np.asarray(expected, dtype=np.float32)))
            ds = None
            self.assertEqual(processor.mark_enclosed_regions(path), 0)

    def test_closed_ring_across_blocks(self):
        a = np.full((7, 7), .25, dtype=np.float32)
        a[1,1:6] = a[5,1:6] = 1
        a[1:6,1] = a[1:6,5] = 1
        expected = a.copy(); expected[2:5,2:5] = 1
        self.run_case(a, expected)

    def test_open_ring(self):
        a = np.ones((5,5)); a[1:4,1:4] = .3; a[0,2] = .3
        self.run_case(a, a)

    def test_diagonal_is_not_opening(self):
        self.run_case([[0,1,1],[1,.4,1],[1,1,1]], [[0,1,1],[1,1,1],[1,1,1]])

    def test_unknown_protects_region(self):
        self.run_case([[1,1,1],[1,.4,-9999],[1,1,1]], [[1,1,1],[1,.4,-9999],[1,1,1]])

    def test_nodata_border(self):
        a=np.full((5,5),-9999.); a[1:4,1:4]=.2
        self.run_case(a,a)

    def test_uniform_maps(self):
        for value in (0.,1.,-9999.):
            with self.subTest(value=value):
                a=np.full((5,5),value)
                self.run_case(a,a)

if __name__ == '__main__':
    unittest.main()
