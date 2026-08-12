# optimization-tool

A local Python optimization project that uses the `virtuoso-bridge-lite-main` package as a dependency.

## Install

```powershell
cd C:\Users\DELL\optimization_tool
pip install -e .
```

## Notes

This package depends on the local Virtuoso bridge repository installed in editable mode:

```powershell
pip install -e "file:///C:/Users/DELL/virtuoso-bridge-lite-main"
```

## Run

```powershell
python -m optimization_tool --iterations 5
```
