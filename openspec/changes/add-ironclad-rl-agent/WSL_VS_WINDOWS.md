# WSL vs Windows Python Environment for RL Training

## Environment Analysis

**Your Current Setup**:
- **WSL Version**: WSL2 (Ubuntu 20.04)
- **GPU**: RTX 3060 Laptop GPU (Windows-side)
- **Game Location**: Windows (`D:\SteamLibrary\steamapps\common\SlayTheSpire\`)
- **Project Location**: Windows (`D:\PycharmProjects\slay-the-spire-ai`), accessed via WSL at `/mnt/d/...`
- **Python (WSL)**: 3.13.5 in `/home/wangce/miniconda3/`

## Critical Architecture Question

```
┌─────────────────────────────────────────────────┐
│  Windows: Slay the Spire + Communication Mod   │
│  Location: D:\SteamLibrary\steamapps\common\... │
│  GPU: RTX 3060 (Windows drivers)                │
└───────────────┬─────────────────────────────────┘
                │ stdin/stdout
                ▼
        ┌───────────────┐
        │  Python Agent │  ← Which Python runs here?
        └───────────────┘
```

## Recommendation: Use Windows Python ⭐

### Why Windows Python is Better

#### 1. **GPU Access**
- **Windows Python**: Direct CUDA access to RTX 3060
- **WSL Python**: Requires WSL2 CUDA forwarding (experimental, may have issues)

#### 2. **Communication Mod Integration**
Communication Mod expects to launch a Python process on **Windows**:
```properties
# Communication Mod config.properties
execute=D:\Python39\python.exe D:\PycharmProjects\slay-the-spire-ai\main.py
```

If you specify WSL Python path, Communication Mod can't launch it directly.

#### 3. **File System Performance**
- **Windows Python**: Direct access to `D:\` (native performance)
- **WSL Python**: Accessing `/mnt/d/` adds overhead (9P filesystem)

#### 4. **Debugging and Logs**
- Game logs (`ai_debug.log`) are written to game directory on Windows
- Windows Python writes to same location seamlessly
- WSL Python would need to handle cross-filesystem paths

## When WSL Python Makes Sense

### WSL2 + CUDA Forwarding (Experimental)

**If WSL2 has GPU support configured**:
```bash
# In WSL, check if GPU is visible
python3 -c "import torch; print(torch.cuda.is_available())"
```

If this returns `True`, WSL2 can access Windows GPU via WSL2 CUDA forwarding.

**But still problematic for Communication Mod**:
- Communication Mod on Windows can't easily launch WSL process
- Would need wrapper script: `wsl python3 /mnt/d/.../main.py`
- Adds complexity and potential failure points

### Pure Training Mode (No Live Game)

**For offline training only** (collecting data, training from saved data):
- WSL Python is acceptable
- But you still need Windows Python for live game interaction

## Recommended Setup

### Option 1: Windows Python (Recommended) ⭐

**Install PyTorch on Windows**:
```powershell
# In PowerShell or Command Prompt
# Create virtual environment
python -m venv D:\PycharmProjects\slay-the-spire-ai\venv

# Activate
D:\PycharmProjects\slay-the-spire-ai\venv\Scripts\activate

# Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}')"
```

**Configure Communication Mod**:
```properties
# C:\Users\{USERNAME}\AppData\Local\ModTheSpire\CommunicationMod\config.properties

execute=D:\PycharmProjects\slay-the-spire-ai\venv\Scripts\python.exe D:\PycharmProjects\slay-the-spire-ai\main.py --agent rl
```

**Advantages**:
- ✅ Direct GPU access
- ✅ Seamless Communication Mod integration
- ✅ Native file system performance
- ✅ Simpler debugging

### Option 2: Hybrid (Advanced)

**Use WSL for development, Windows for game**:
```bash
# In WSL, use Windows Python via interop
/mnt/c/Python39/python.exe main.py --agent rl
```

Or create wrapper script:
```bash
#!/bin/bash
# run_rl_windows.sh
/mnt/c/Python39/python.exe /mnt/d/PycharmProjects/slay-the-spire-ai/main.py "$@"
```

**Advantages**:
- ✅ WSL development environment (better tools, terminal)
- ✅ Windows Python for game interaction
- ❌ Added complexity

### Option 3: WSL2 with Full GPU Support (Experimental)

**If you really want to use WSL2**:

1. Install WSL2 CUDA drivers (separate from Windows drivers)
2. Install PyTorch in WSL2 with CUDA
3. Configure Communication Mod to use WSL wrapper:
```batch
# In Communication Mod config
execute=wsl python3 /mnt/d/PycharmProjects/slay-the-spire-ai/main.py
```

**Disadvantages**:
- ❌ Experimental (WSL2 CUDA support is relatively new)
- ❌ Complex setup
- ❌ May have performance/compatibility issues
- ❌ Harder to debug

## Performance Comparison

### Training Speed (Network Forward/Backward)

| Setup | GPU Access | Expected Speed | Notes |
|-------|-----------|----------------|-------|
| **Windows Python** | ✅ Native CUDA | Fastest (baseline) | Recommended |
| WSL2 Python (CUDA forwarding) | ⚠️ Via WSL2 | ~90-95% of native | Some overhead |
| WSL1 Python | ❌ No GPU | 10-20x slower | CPU only |

### Game Execution Speed

| Setup | stdin/stdout | File I/O | Overall |
|-------|--------------|----------|---------|
| **Windows Python** | ✅ Native | ✅ Native | Fastest |
| WSL Python (via /mnt/d/) | ⚠️ Interop | ⚠️ 9P FS | ~5-10% slower |

## Final Recommendation

### For Training RL Agent

**Use Windows Python** with these steps:

1. **Install PyTorch on Windows** (see Option 1 above)
2. **Create virtual environment** in project directory
3. **Configure Communication Mod** to use Windows Python
4. **Train** with: `python main.py --agent rl --mode train`

### For Development/Testing

**Use WSL for development, Windows for game**:
- Edit code in WSL (better terminal, tools)
- Test/run in Windows (via PyCharm or direct Windows Python)
- Or use PyCharm's WSL interpreter with remote execution

## Quick Start Command

```powershell
# Windows PowerShell
cd D:\PycharmProjects\slay-the-spire-ai
python -m venv venv
.\venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
python main.py --agent rl --mode train --games 100
```

## Summary

| Use Case | Recommended |
|----------|-------------|
| **Live game + RL training** | **Windows Python** ⭐ |
| Offline training only | Either (Windows simpler) |
| Code development | WSL (better tools) |
| GPU acceleration | Windows Python (native) |

**Bottom line**: Use Windows Python for the agent, but you can still develop code in WSL.
