import unittest
from NyaaSort.NyaaSort import NyaaSort
import os
import shutil


class TestFull(unittest.TestCase):
    def setUp(self):
        self.app = NyaaSort
        base_dir = os.path.dirname(os.path.realpath(__file__))
        true_dir = os.path.join(base_dir, 'fixtures')
        # Make a new test dir
        self.dir = os.path.join(base_dir, 'test_temp_dir')
        if os.path.exists(self.dir):
            shutil.rmtree(self.dir)
            shutil.copytree(true_dir, self.dir)
        else:
            shutil.copytree(true_dir, self.dir)

    def test_nyaasort(self):
        self.assertEqual(self.app(self.dir).sort(), None)

    def tearDown(self):
        # Remove the test dir
        shutil.rmtree(self.dir)


if __name__ == '__main__':
    unittest.main()
