import logging
import sys
import time
from pathlib import Path

# ── Logging configuration ───────────────────────────────────────────────
# Suppress verbose SSH [cmd] output from console; redirect to file.
# The log file is at ~/.virtuoso-bridge/logs/commands.log by default,
# or set VB_LOG_DIR to customise.
logging.getLogger("virtuoso_bridge").setLevel(logging.DEBUG)
# Root logger: keep warnings+errors on console, everything else to file
root_logger = logging.getLogger()
if not root_logger.handlers:
    root_logger.setLevel(logging.WARNING)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    root_logger.addHandler(console)
# ─────────────────────────────────────────────────────────────────────────

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from virtuoso_bridge import VirtuosoClient
from optimization import (
    VariableBoundsError,
    fetch_variables_with_units,
    get_current_test_name,
    download_and_parse_specs,
    mae_set_var_str,
    run_simulation_and_wait,
    read_simulation_output_csv,
    extract_objectives_from_output_csv,
    validate_variable_bounds,
)
import pandas as pd


def main():
    client = VirtuosoClient.from_env()

    # ── Suppress verbose SSH [cmd] console output ──
    # These are hardcoded print() calls in virtuoso_bridge's SSHRunner.
    # The same info is already logged via logger.info() to the file.
    ssh_runner = getattr(getattr(client, '_tunnel', None), '_ssh_runner', None)
    if ssh_runner is not None:
        ssh_runner._verbose = False

    print("Connected to Virtuoso")

    current_test = get_current_test_name(client)
    print("Current test:", current_test)

    # ── Read variables with raw strings (preserving units like "n", "u", "m") ──
    names, raw_vals, vals, mins, maxs = fetch_variables_with_units(client)
    print(f"Variables ({len(names)}):")
    for i, (n, r, v) in enumerate(zip(names, raw_vals, vals)):
        print(f"  {n}: raw='{r}'  num={v:.6e}  min={mins[i]:.6e}  max={maxs[i]:.6e}")

    # ── Validate variable bounds ──
    for n, v, lo, hi in zip(names, vals, mins, maxs):
        validate_variable_bounds(n, float(v), float(lo), float(hi))
    print("All variable bounds are valid.")

    run_dir = "/home/colon/Desktop/project1010drv"

    # ── Set variable values using raw strings (preserves unit prefixes) ──
    for name, raw_val in zip(names, raw_vals):
        res = mae_set_var_str(client, name, raw_val)
        print(f"Set var {name} = {raw_val}  →  {res}")

    # ── Run simulation with callback-based monitoring ──
    print("Starting real simulation (callback-based, timeout=600s)...")
    t0 = time.time()
    try:
        history, status = run_simulation_and_wait(client, timeout=600)
        elapsed = round(time.time() - t0, 2)
        print(f"Simulation finished in {elapsed}s.  History: {history}  Status: {status}")

        if status != "done":
            print(f"WARNING: Simulation status is '{status}', not 'done'. Results may be incomplete.")
    except TimeoutError:
        print(f"ERROR: Simulation timed out after 600s. The remote Virtuoso may need manual cleanup.")
        print("Try: dismiss any modal dialogs, then re-run.")
        return
    except RuntimeError as e:
        print(f"ERROR: Simulation failed to start: {e}")
        return

    # ── Download and parse results ──
    print("Downloading output CSV...")
    csv_path = read_simulation_output_csv(client, run_dir, current_test)
    print("Downloaded CSV to:", csv_path)

    df = pd.read_csv(csv_path)
    print("CSV Content Head:")
    print(df.head(10))

    objs = extract_objectives_from_output_csv(df, n_obj=3)
    print("Extracted objectives:", objs)


if __name__ == "__main__":
    main()