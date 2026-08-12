import inspect
import virtuoso_bridge
print('file=', inspect.getsourcefile(virtuoso_bridge) or getattr(virtuoso_bridge, '__file__', None))
print('version=', getattr(virtuoso_bridge, '__version__', None))
