# optimization-tool

A Python optimization tool that connects pymoo evolutionary algorithms with
Cadence Virtuoso Maestro for analog IC design optimization.

## Architecture
![alt text][def]
```
┌──────────────────────────────────────┐
│  optimization_tool (Python)          │
│  ┌────────────────────────────────┐  │
│  │  pymoo Algorithm               │  │
│  │  (GA/NSGA2/DE/PSO/CMAES/…)     │  │
│  └────────────┬───────────────────┘  │
│               │ SKILL commands       │
│  ┌────────────▼───────────────────┐  │
│  │  virtuoso-bridge (SSH tunnel)  │  │
│  └────────────┬───────────────────┘  │
└───────────────┼──────────────────────┘
                │ SSH
┌───────────────▼──────────────────────┐
│  Linux (Virtuoso + Maestro)          │
│  └─ Spectre simulation               │
└──────────────────────────────────────┘
```

## Prerequisites

- Python 3.9+
- `virtuoso-bridge` installed and configured (SSH tunnel to Virtuoso)
- Cadence Virtuoso with Maestro
- pymoo and its dependencies

## Install

```powershell
cd C:\Users\DELL\optimization_tool

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -e "file:///C:/Users/DELL/virtuoso-bridge-lite-main"
pip install -e .
```

## Usage

### Quick start (dry-run, no real simulation)

```powershell
python -m optimization_tool --generations 10 --population 20
```

### Real run (with Virtuoso simulation)

```powershell
python -m optimization_tool --real-run --generations 50 --population 50
```

### With project archiving

```powershell
python -m optimization_tool --project-dir my_opamp_opt --generations 50
```

This creates a timestamped archive under `my_opamp_opt/runs/` with full
configuration, per-generation history, and final results.

### List available algorithms

```powershell
python -m optimization_tool --list-algos
```

### All options

| Argument | Default | Description |
|----------|---------|-------------|
| `--generations N` | 10 | Number of optimization generations |
| `--population N` | 20 | Population size |
| `--algo NAME` | nsga2 | Algorithm name (see `--list-algos`) |
| `--dry-run` | true | Run without real simulation (default) |
| `--real-run` | | Run actual Virtuoso simulation |
| `--project-dir DIR` | none | Project directory for archiving runs |
| `--run-directory DIR` | . | Remote Virtuoso run directory |
| `--csv-filename FILE` | none | Use local CSV instead of downloading |
| `--download-dir DIR` | none | Local directory for downloaded CSV |
| `--seed N` | 1 | Random seed |
| `--no-plot` | | Disable convergence/Pareto plots |
| `--plot-dir DIR` | . | Directory to save plot images |
| `--list-algos` | | List available algorithms and exit |
| `--quiet` | | Suppress verbose output |

## Available Algorithms

| Category | Algorithms |
|----------|-----------|
| Single-objective | ga, de, pso, cmaes |
| Multi-objective (2-3) | nsga2, spea2, nsga3, moead, rnsga3 |
| Many-objective (4+) | nsga3, moead, ctaea |

## Project Structure (with `--project-dir`)

```
my_project/
├── project.json              # Project metadata (auto-generated)
├── runs/
│   ├── 20260817_143001/      # Each run = timestamped directory
│   │   ├── config.json       # Full configuration snapshot
│   │   ├── variables.csv     # Variable names + bounds
│   │   ├── specs.csv         # Objective expressions + weights
│   │   ├── history.jsonl     # Per-generation log (JSONL)
│   │   ├── results.json      # Final Pareto set
│   │   ├── convergence.png   # Convergence plot
│   │   └── pareto.png        # Pareto front plot
│   └── ...
└── context/                  # Human notes (optional)
```

## References

- [pymoo documentation](https://pymoo.org/)
- [virtuoso-bridge-lite](https://github.com/your-org/virtuoso-bridge-lite)

[def]: image/Readme.png