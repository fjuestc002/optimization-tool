import importlib.util as iu
modules = ["numpy", "pandas", "virtuoso_bridge"]
for m in modules:
    print(m, iu.find_spec(m) is not None)
