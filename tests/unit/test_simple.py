import unittest
from NyaaSort.NyaaSort import NyaaSort


class TestSimple(unittest.TestCase):
    def setUp(self):
        self.app = NyaaSort
        self.dir = ''

    def test_anime_dict(self):
        folders = ['[DameDesuYo] Shingeki no Kyojin (The Final Season)',
                   '[Erai-raws] Enen no Shouboutai - Ni no Shou',
                   '[Multiple groups] Enen no Shouboutai S2']
        folders_dict = {'Enen no Shouboutai - Ni no Shou': '[Erai-raws] Enen no Shouboutai - Ni no Shou',
                        'Enen no Shouboutai S2': '[Multiple groups] Enen no Shouboutai S2',
                        'Shingeki no Kyojin (The Final Season)': '[DameDesuYo] Shingeki no Kyojin (The Final Season)'}
        # Test if no folders
        self.assertEqual(self.app(self.dir).get_anime_dict(['']), {})
        self.assertEqual(self.app(self.dir).get_anime_dict(folders), folders_dict)


if __name__ == '__main__':
    unittest.main()
