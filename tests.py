from __future__ import with_statement

import sys

from copy import deepcopy
from flask import Flask
from flask.ext.dogpile_cache import DogpileCache

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class DogpileCacheTest(unittest.TestCase):
    def setUp(self):
        default_cache_backend = 'dogpile.cache.memcached'
        default_cache_urls = ["127.0.0.1:11211"]
        self.config = dict(
            DOGPILE_CACHE_BACKEND=default_cache_backend,
            DOGPILE_CACHE_URLS=default_cache_urls,
            DOGPILE_CACHE_REGIONS=[
                ('hour', 3600, default_cache_backend, default_cache_urls),
                ('day', 3600 * 24),
                ('week', 3600 * 24 * 7),
                ('month', 3600 * 24 * 31),
            ],
            DOGPILE_CACHE_ARGUMENTS={'binary': True},
        )

        self.app = Flask(__name__)
        self.app.debug = True
        self.cache = DogpileCache(self.app, self.config)

        self.func_cached_for_hour_value = 12345
        self.func_cached_for_day_value = 67890

        @self.cache.region('hour')
        def func_cached_for_hour(delta=0):
            return self.func_cached_for_hour_value + delta

        @self.cache.region('day')
        def func_cached_for_day(delta=0):
            return self.func_cached_for_day_value + delta

        self.func_cached_for_hour = func_cached_for_hour
        self.func_cached_for_day = func_cached_for_day
        self.func_result_map = ((self.func_cached_for_hour,
                                 self.func_cached_for_hour_value),
                                (self.func_cached_for_day,
                                 self.func_cached_for_day_value))

    def tearDown(self):
        self.config = None
        self.app = None
        self.cache = None
        self.func_result_map = None
        self.func_cached_for_hour_value = None
        self.func_cached_for_day_value = None
        self.func_cached_for_hour = None
        self.func_cached_for_day = None

    def clean_up_cache(self):
        self.cache.invalidate_all_regions()

    def test_get(self):
        self.clean_up_cache()
        for func, correct_value in self.func_result_map:
            self.assertEqual(func(), correct_value)

    def test_get_with_arg(self):
        self.clean_up_cache()
        for func, correct_value in self.func_result_map:
            self.assertNotEqual(func(777), correct_value)

    def test_set(self):
        self.clean_up_cache()
        for func, correct_value in self.func_result_map:
            custom_value = correct_value + 1
            self.cache.set(func, custom_value)
            self.assertEqual(func(), custom_value)

    def test_refresh(self):
        self.clean_up_cache()
        for func, correct_value in self.func_result_map:
            custom_value = correct_value + 1
            self.cache.set(func, custom_value)
            self.assertEqual(func(), custom_value)
            self.cache.refresh(func)
            self.assertEqual(func(), custom_value)

    def test_invalidate(self):
        self.clean_up_cache()
        for func, correct_value in self.func_result_map:
            custom_value = correct_value + 1
            self.cache.set(func, custom_value)
            self.assertEqual(func(), custom_value)
            self.cache.invalidate(func)
            self.assertEqual(func(), correct_value)

    def test_invalidate_region(self):
        self.clean_up_cache()
        for func, correct_value in self.func_result_map:
            custom_value = correct_value + 1
            self.cache.set(func, custom_value)

        self.cache.invalidate_region('hour')
        self.assertEqual(self.func_cached_for_hour(),
                         self.func_cached_for_hour_value)
        self.assertNotEqual(self.func_cached_for_day(),
                            self.func_cached_for_day_value)

    def test_invalidate_all_regions(self):
        self.clean_up_cache()
        for func, correct_value in self.func_result_map:
            custom_value = correct_value + 1
            self.cache.set(func, custom_value)

        self.cache.invalidate_all_regions()
        for func, correct_value in self.func_result_map:
            self.assertEqual(func(), correct_value)

    def test_working_outside_of_application_context(self):
        cache = DogpileCache()
        self.assertRaises(RuntimeError, cache.get_region, 'x')
        self.assertRaises(RuntimeError, cache.get_all_regions)
        self.assertRaises(RuntimeError, cache.get_region_decorator, 'x')

    def test_cache_with_not_existent_region(self):
        @self.cache.region('not_existent_region_name')
        def func():
            pass

        self.assertRaises(KeyError, func)

    def test_not_cached_func(self):
        not_cached_func = lambda: None
        self.assertRaises(AttributeError,
                          self.cache.invalidate,
                          not_cached_func)
        self.assertRaises(AttributeError,
                          self.cache.refresh,
                          not_cached_func)
        self.assertRaises(AttributeError,
                          self.cache.set,
                          not_cached_func,
                          'some_value')

    def test_wrong_config(self):
        app = Flask(__name__)

        config = deepcopy(self.config)
        config['DOGPILE_CACHE_REGIONS'] = []
        self.assertRaises(ValueError, DogpileCache, app, config)

        config = deepcopy(self.config)
        config['DOGPILE_CACHE_REGIONS'].append(tuple())
        self.assertRaises(ValueError, DogpileCache, app, config)

        config = deepcopy(self.config)
        config['DOGPILE_CACHE_REGIONS'].append(('bad',))
        self.assertRaises(ValueError, DogpileCache, app, config)

        config = deepcopy(self.config)
        config['DOGPILE_CACHE_BACKEND'] = None
        self.assertRaises(ValueError, DogpileCache, app, config)

        config = deepcopy(self.config)
        config['DOGPILE_CACHE_URLS'] = None
        self.assertRaises(ValueError, DogpileCache, app, config)

        config = deepcopy(self.config)
        config['DOGPILE_CACHE_REGIONS'] = None
        self.assertRaises(ValueError, DogpileCache, app, config)

        config = deepcopy(self.config)
        config['DOGPILE_CACHE_ARGUMENTS'] = None
        self.assertRaises(ValueError, DogpileCache, app, config)


if __name__ == '__main__':
    unittest.main()
