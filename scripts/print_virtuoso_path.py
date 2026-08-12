import virtuoso_bridge
import inspect
import os
print('module_file=', inspect.getsourcefile(virtuoso_bridge) or virtuoso_bridge.__file__)
print('module_path=', getattr(virtuoso_bridge, '__path__', None))
print('version=', getattr(virtuoso_bridge, '__version__', None))
