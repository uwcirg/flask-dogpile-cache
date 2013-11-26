from dogpile.cache import make_region
from functools import wraps
from types import NoneType


__version__ = '0.2'


class NotInitialized(object):
    pass


class DogpileCache(object):
    FUNC_REGION_NAME_ATTR = 'dogpile_cache_region_name'

    def __init__(self, app=None, config=None, wrappers_debug=None,
                 wrappers_production=None):
        """
        :param app: Flask app object.

        :param config: Configuration dict.

            DOGPILE_CACHE_BACKEND
                Optional. 'dogpile.cache.memcached' by default.
                You can override it with other available backends from
                dogpile.cache.

            DOGPILE_CACHE_URLS
                Required if not declared for each region.
                A list or tuple of cache servers' urls.
                For example, ["127.0.0.1:11211"].

            DOGPILE_CACHE_REGIONS
                Required. A list or tuple of region_data_tuples. Each
                region_data_tuple has from 2 to 4 elements:
                1) region_name (str, required). For example, 'hour'.
                2) region_timeout (int, required). For example, 3600.
                3) region_backend (str, optional). If not declared takes
                   its value from DOGPILE_CACHE_BACKEND.
                4) region_urls (list or tuple, optional). If not declared
                   takes its value from DOGPILE_CACHE_URLS.
                5) region_arguments (dict, optional). See description bellow.

            DOGPILE_CACHE_ARGUMENTS
                Optional.  The structure here is passed directly to the
                constructor of the class `CacheBackend` in use, though is
                typically a dictionary.

            The simplest config is:
                DOGPILE_CACHE_URLS = ["127.0.0.1:11211"]
                DOGPILE_CACHE_REGIONS = [
                    ('hour', 3600),
                    ('day', 3600 * 24),
                ]

        :param wrappers_debug, wrappers_production:
            A decorator class for altering the functionality of backends.
            Example:

                from dogpile.cache.proxy import ProxyBackend

                class DebugProxy(ProxyBackend):
                    @timer  # custom decorator that logs calls duration
                    def get(self, key):
                        return self.proxied.get(key)

                    @timer
                    def set(self, key, value):
                        return self.proxied.set(key, value)

                    @timer
                    def delete(self, key):
                        return self.proxied.delete(key)

        """
        self.config = config
        self.app = app
        self._wrappers_debug = wrappers_debug
        self._wrappers_production = wrappers_production
        self._cache_regions = NotInitialized()
        self._cache_regions_decorators = NotInitialized()

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
        config.setdefault('DOGPILE_CACHE_ARGUMENTS', {})
        if not (
            isinstance(config['DOGPILE_CACHE_REGIONS'], (list, tuple))
            and config['DOGPILE_CACHE_REGIONS']
        ):
            raise ValueError('`DOGPILE_CACHE_REGIONS` must be list or tuple')
        if not isinstance(config['DOGPILE_CACHE_ARGUMENTS'], dict):
            raise ValueError('`DOGPILE_CACHE_ARGUMENTS` must be dict')

        wrappers_debug = wrappers_debug or self._wrappers_debug
        wrappers_production = wrappers_production or self._wrappers_production

        self._set_cache_regions(app=app,
                                config=config,
                                wrappers_debug=wrappers_debug,
                                wrappers_production=wrappers_production)

    def _set_cache_regions(self, app, config, wrappers_debug,
                           wrappers_production):
        self._cache_regions = dict()
        self._cache_regions_decorators = dict()

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

            if len(region_tuple) > 4:
                region_arguments = region_tuple[4]
                if not isinstance(region_arguments, dict):
                    raise ValueError('`regions_arguments` must be dict')
            else:
                region_arguments = config['DOGPILE_CACHE_ARGUMENTS']

            arguments = dict(url=region_urls)
            arguments.update(region_arguments)

            region = make_region().configure(
                backend=region_backend,
                expiration_time=region_timeout,
                arguments=arguments,
                wrap=wrappers_debug if app.debug else wrappers_production,
            )
            region_decorator = region.cache_on_arguments()

            self._cache_regions[region_name] = region
            self._cache_regions_decorators[region_name] = region_decorator

        if not hasattr(app, 'extensions'):
            app.extensions = {}

        app.extensions['dogpile_cache'] = self

    def get_region(self, region_name):
        """
        Method for getting already configured cache region.

        :param region_name: Name for region from config (for example, 'hour').

        :return <CacheRegion object>:

        Will raise RunTimeError if call it before `init_app` method.
        """
        if isinstance(self._cache_regions, NotInitialized):
            raise RuntimeError('working outside of application context')
        return self._cache_regions[region_name]

    def get_all_regions(self):
        """
        Method for getting all already configured cache regions.

        :return dict: keys = region_names, values = <CacheRegion objects>

        Will raise RunTimeError if call it before `init_app` method.
        """
        if isinstance(self._cache_regions, NotInitialized):
            raise RuntimeError('working outside of application context')
        return self._cache_regions

    def get_region_decorator(self, region_name):
        """
        Method for getting already configured cache region_decorator.

        :param region_name: Name for region from config (for example, 'hour').

        :return <CacheRegion object>.cache_on_arguments():

        Will raise RunTimeError if call it before `init_app` method.
        """
        if isinstance(self._cache_regions_decorators, NotInitialized):
            raise RuntimeError('working outside of application context')
        return self._cache_regions_decorators[region_name]

    def region(self, name):
        """
        CacheRegion decorator.

        :param name: Region name from config['DOGPILE_CACHE_REGIONS'].

        Example:

            @cache.region('hour')
            def cached_func(*args):
                return args

            cached_value = cached_func()
        """
        def decorator(func):
            setattr(func, self.FUNC_REGION_NAME_ATTR, name)

            @wraps(func)
            def wrapper(*args):
                if name in self._cache_regions:
                    cache_decorator = self.get_region_decorator(name)
                    return cache_decorator(func)(*args)
                else:
                    raise KeyError("You didn't specified region `%s`" % name)
            return wrapper
        return decorator

    def invalidate_region(self, region_name, hard=True):
        """
        Method for invalidation cache for all funcs decorated with particular
        @cache.region().

        :param region_name: Region name from config['DOGPILE_CACHE_REGIONS'].

        :param hard: if True, cache values will all require immediate
                     regeneration; dogpile logic won't be used.  If False, the
                     creation time of existing values will be pushed back
                     before the expiration time so that a return+regen will be
                     invoked.

        Example:

            cache.invalidate_region('hour')
        """
        region = self.get_region(region_name)
        region.invalidate(hard)

    def invalidate_all_regions(self, hard=True):
        """
        Method for invalidation cache for all funcs decorated with
        @cache.region().

        :param hard: if True, cache values will all require immediate
                     regeneration; dogpile logic won't be used.  If False, the
                     creation time of existing values will be pushed back
                     before the expiration time so that a return+regen will be
                     invoked.
        Example:

            cache.invalidate_region('hour')
        """
        for region_name in self.get_all_regions().keys():
            self.invalidate_region(region_name, hard)

    def invalidate(self, func, *args):
        """
        Method for invalidating cache for particular func.

        :param func: Function, decorated with @cache.region().

        :param *args: Decorated function arguments.

        Example:

            cache.invalidate(cached_func_without_args)
            cache.invalidate(cached_func_with_args, *args)
        """
        region_name = getattr(func, self.FUNC_REGION_NAME_ATTR)
        decorator = self.get_region_decorator(region_name)
        func = decorator(func)
        return func.invalidate(*args)

    def refresh(self, func, *args):
        """
        Method for refreshing cache for particular func.

        :param func: Function, decorated with @cache.region().

        :param *args: Decorated function arguments.

        Example:

            cache.refresh(cached_func_without_args)
            cache.refresh(cached_func_with_args, *args)

        You must understand that refreshing func do not call regenerating cache
        for func. If cache exists it does nothing. If cache does not exist it
        will compute (create) new cache value and store it to cache server.
        """
        region_name = getattr(func, self.FUNC_REGION_NAME_ATTR)
        decorator = self.get_region_decorator(region_name)
        func = decorator(func)
        return func.refresh(*args)

    def set(self, func, value, *args):
        """
        Method for setting custom cache value for particular func.

        :param func: Function, decorated with @cache.region().

        :param value: Value to store.

        :param *args: Decorated function arguments.

        Example:

            cache.set(cached_func_without_args, 'value')
            cache.set(cached_func_with_args, 'value', *args)
        """
        region_name = getattr(func, self.FUNC_REGION_NAME_ATTR)
        decorator = self.get_region_decorator(region_name)
        func = decorator(func)
        return func.set(value, *args)
