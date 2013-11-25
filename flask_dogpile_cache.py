from dogpile.cache import make_region
from flask import current_app
from functools import wraps
from types import NoneType


__version__ = '0.1.4'


class DogpileCache(object):
    def __init__(self, app=None, config=None, wrappers_debug=None,
                 wrappers_production=None):
        self.config = config
        self.app = app
        self._wrappers_debug = wrappers_debug
        self._wrappers_production = wrappers_production
        self._cache_regions = dict()

        if app is not None:
            self.init_app(app, config)

    def init_app(self, app, config=None, wrappers_debug=None,
                 wrappers_production=None):
        if not isinstance(config, (NoneType, dict)):
            raise ValueError("`config` must be dict or NoneType")

        if config is None:
            config = self.config
            if config is None:
                config = app.config

        config.setdefault('DOGPILE_CACHE_BACKEND', 'dogpile.cache.memcached')
        config.setdefault('DOGPILE_CACHE_URLS', None)
        config.setdefault('DOGPILE_CACHE_REGIONS', tuple())
        config.setdefault('DOGPILE_CACHE_BINARY', True)

        wrappers_debug = wrappers_debug or self._wrappers_debug
        wrappers_production = wrappers_production or self._wrappers_production

        self._set_cache_regions(app=app,
                                config=config,
                                wrappers_debug=wrappers_debug,
                                wrappers_production=wrappers_production)

    def _set_cache_regions(self, app, config, wrappers_debug,
                           wrappers_production):
        for region_tuple in config['DOGPILE_CACHE_REGIONS']:
            if len(region_tuple) < 2:
                raise ValueError('`DOGPILE_CACHE_REGIONS` tuple item length '
                                 'must be at least 2: region_name and '
                                 'region_timeout')

            region_name = region_tuple[0]
            region_timeout = region_tuple[1]

            if len(region_tuple) > 2:
                region_backend = region_tuple[2]
            elif config['DOGPILE_CACHE_BACKEND']:
                region_backend = config['DOGPILE_CACHE_BACKEND']
            else:
                raise ValueError('`DOGPILE_CACHE_BACKEND` must be specified '
                                 'or not initialized at all '
                                 '(for default value)')

            if len(region_tuple) > 3:
                region_urls = region_tuple[3]
            elif config['DOGPILE_CACHE_URLS']:
                region_urls = config['DOGPILE_CACHE_URLS']
            else:
                raise ValueError("`DOGPILE_CACHE_URLS` must be specified")

            region = make_region().configure(
                backend=region_backend,
                expiration_time=region_timeout,
                arguments={'url': region_urls,
                           'binary': config['DOGPILE_CACHE_BINARY']},
                wrap=wrappers_debug if app.debug else wrappers_production,
            )
            self._cache_regions[region_name] = region.cache_on_arguments()

        if not hasattr(app, 'extensions'):
            app.extensions = {}

        app.extensions['dogpile_cache'] = self

    def _get_region_decorator(self, region_name):
        if not current_app:
            raise RuntimeError('working outside of application context')
        return self._cache_regions[region_name]

    def region(self, name):
        def decorator(func):
            func.dogpile_cache_region_name = name

            @wraps(func)
            def wrapper(*args):
                if name in self._cache_regions:
                    cache_decorator = self._get_region_decorator(name)
                    return cache_decorator(func)(*args)
                else:
                    raise AttributeError("You didn't specified region `%s`"
                                         % name)
            return wrapper
        return decorator

    def invalidate(self, func, *args):
        decorator = self._get_region_decorator(func.dogpile_cache_region_name)
        func = decorator(func)
        return func.invalidate(*args)

    def refresh(self, func, *args):
        decorator = self._get_region_decorator(func.dogpile_cache_region_name)
        func = decorator(func)
        return func.refresh(*args)

    def set(self, func, value, *args):
        decorator = self._get_region_decorator(func.dogpile_cache_region_name)
        func = decorator(func)
        return func.set(value, *args)
