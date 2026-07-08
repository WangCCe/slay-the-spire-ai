# Bottled Policy Oracle Adapter

The Bottled policy oracle is an offline comparison path for Ironclad non-combat decisions. It reads a local `bottled_ai` checkout and labels current samples with Bottled `REQUESTED_STRIKE` reference decisions.

## Scope

- Supported first: `shop`, `card_reward`, `event`, and `route`.
- Combat is feasibility-only and does not replace the current combat policy.
- The adapter does not launch Slay the Spire, CommunicationMod, training, or live gameplay.
- The adapter does not modify the Bottled checkout.

## Checkout Path

Default local path:

```powershell
C:\Users\20571\Documents\bottled_ai
```

Override options:

```powershell
$env:BOTTLED_AI_PATH = "C:\Users\20571\Documents\bottled_ai"
```

or pass:

```powershell
--bottled-repo C:\Users\20571\Documents\bottled_ai
```

## Offline Comparator

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\offline_decision_comparator.py `
  --fixture tests\fixtures\offline_decision_samples.json `
  --reference-mode native-bottled `
  --bottled-repo C:\Users\20571\Documents\bottled_ai `
  --output reports\offline_decision_comparator_bottled_oracle_smoke.md
```

Use `--reference-mode bottled-style` to keep the previous locally encoded reference behavior.

## Non-Combat RL Exporter

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\noncombat_rl_decision_loop.py `
  --trace D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace_clean.jsonl `
  --reference-mode native-bottled `
  --bottled-repo C:\Users\20571\Documents\bottled_ai `
  --output reports\noncombat_rl_decision_loop_bottled_oracle.md `
  --json-output reports\noncombat_rl_decision_samples_bottled_oracle.jsonl
```

The trace input must be raw decision trace JSONL, not an already exported sample JSONL.

## Output Contract

Native oracle rows include:

- `oracle_mode`: `native_bottled`
- Bottled repo path and git commit when available
- strategy name: `REQUESTED_STRIKE`
- raw command or decision payload when available
- limitations when the sample cannot be mapped faithfully

Unsupported or partial rows are explicit and are not high-confidence policy-fix evidence.
