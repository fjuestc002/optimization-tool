import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import optimization from project
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from optimization import fetch_variables, download_and_parse_specs
from virtuoso_bridge import VirtuosoClient

client = VirtuosoClient.from_env()
print('Connected client')

# get current test name
current_test = client.execute_skill('maeGetSetup()').output
print('Current test:', current_test)

# fetch variables
names, vals, mins, maxs = fetch_variables(client)
print('Variables:', names)
print('Values:', vals)
print('Mins:', mins)
print('Maxs:', maxs)

# download and parse specs csv
run_dir = '/home/colon/Desktop/project1010drv'
try:
    spec_names, weights, specs, local_path = download_and_parse_specs(client, run_dir, current_test)
    print('Spec names:', spec_names)
    print('Weights:', weights)
    print('Specs:', specs)
    print('Downloaded CSV at', local_path)
except Exception as e:
    print('Error downloading/parsing specs CSV:', e)
