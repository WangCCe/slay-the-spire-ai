# State-Conditioned Simulator Learning Terminal Archive

`training_rows.json.gz` is a deterministic gzip copy of the canonical terminal
training rows. The raw file is omitted from ordinary Git because it is
126,834,076 bytes and this public fork does not accept new LFS objects.

The other 74 manifest-listed terminal artifacts remain in
`reports/noncombat_state_conditioned_simulator_learning_experiment_20260805/`
as their original canonical files. The complete raw output remains preserved
locally.

From the repository root, restore the canonical training rows with Windows
production Python:

```powershell
D:\anaconda\envs\stsai\python.exe -c "import gzip, pathlib, shutil; source = pathlib.Path(r'reports/noncombat_state_conditioned_simulator_learning_experiment_20260805_archive/training_rows.json.gz'); target = pathlib.Path(r'reports/noncombat_state_conditioned_simulator_learning_experiment_20260805/training_rows.json'); target.parent.mkdir(parents=True, exist_ok=True); src = gzip.open(source, 'rb'); dst = target.open('wb'); shutil.copyfileobj(src, dst); src.close(); dst.close()"
```

Then independently validate the reconstructed terminal bundle:

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\verify_noncombat_state_conditioned_simulator_learning_experiment.py --output reports\noncombat_state_conditioned_simulator_learning_experiment_20260805
```

The archive, raw, and terminal-manifest SHA-256 values are frozen in
`manifest.json`.
