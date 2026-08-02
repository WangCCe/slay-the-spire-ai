# Baseline Warm-Start Corpus Archive

`demonstrations.json.gz` is a deterministic gzip copy of the canonical
demonstration corpus. The raw file is omitted from ordinary Git because it is
320,965,025 bytes and GitHub does not accept new LFS objects from this public
fork.

From the repository root, restore the canonical file with Windows production
Python:

```powershell
D:\anaconda\envs\stsai\python.exe -c "import gzip, pathlib, shutil; source = pathlib.Path(r'reports/noncombat_simulator_baseline_warm_start_20260802_archive/demonstrations.json.gz'); target = pathlib.Path(r'reports/noncombat_simulator_baseline_warm_start_20260802/demonstrations.json'); target.parent.mkdir(parents=True, exist_ok=True); src = gzip.open(source, 'rb'); dst = target.open('wb'); shutil.copyfileobj(src, dst); src.close(); dst.close()"
```

Then revalidate the complete managed set:

```powershell
D:\anaconda\envs\stsai\python.exe -c "from analysis_scripts.noncombat_simulator_baseline_warm_start import validate_warm_start_artifact_directory; validate_warm_start_artifact_directory(r'reports/noncombat_simulator_baseline_warm_start_20260802'); print('valid')"
```

The archive and raw SHA-256 values are frozen in `manifest.json`.
