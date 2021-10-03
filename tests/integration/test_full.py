import unittest
from NyaaSort.NyaaSort import NyaaSort
import os
import tests.utils
import shutil


class TestFull(unittest.TestCase):
    def setUp(self):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        self.dir = tests.utils.copy_tree(base_dir)
        self.app = NyaaSort

    def test_nyaasort(self):
        self.assertEqual(self.app(self.dir, 0, 'False', self.dir, 'None').sort(), None)

    def tearDown(self):
        # Remove the test dir
        shutil.rmtree(self.dir)
        # Remove the SortConfig.ini
        os.remove(self.app.return_ini_location())


if __name__ == '__main__':
    unittest.main()
