# GPU Optimization for RTX 3060 Laptop

## Hardware Specifications

**GPU**: NVIDIA GeForce RTX 3060 Laptop GPU
- **VRAM**: 6GB GDDR6
- **Compute Capability**: 8.6 (Ampere architecture)
- **Tensor Cores**: Yes (for mixed precision training)
- **CUDA Cores**: 3840

## Performance Optimizations

### 1. Increased Batch Size
- **CPU default**: 64 samples per batch
- **GPU optimized**: 128 samples per batch
- **Benefit**: Better GPU utilization, faster training

### 2. Mixed Precision Training (FP16)
- **Enable**: Automatic Mixed Precision (AMP) in PyTorch
- **Benefit**: 2x faster training, half the VRAM usage
- **Implementation**:
```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

with autocast():
    q_values = model(states)
    loss = compute_loss(q_values, targets)

scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

### 3. GPU-Aware Replay Buffer
- **Store**: States and transitions in GPU memory (if VRAM permits)
- **Alternative**: Keep buffer in system RAM, transfer batches to GPU
- **Recommended**: Buffer in RAM (~1.5GB), transfer batches to GPU for training

### 4. Action Masking on GPU
- **Compute**: Boolean mask on GPU (faster than CPU)
- **Apply**: Set Q-values for invalid actions to -inf in-place

## Memory Budget (6GB VRAM)

| Component | VRAM Usage | Notes |
|-----------|------------|-------|
| Online Network | ~250MB | 420K parameters, FP32 |
| Target Network | ~250MB | Copy of online network |
| Optimizer States | ~500MB | Adam moments (2× parameters) |
| Training Batch (128) | ~50MB | 128 × 512 floats × 2 (state, next_state) |
| Gradients | ~250MB | Same size as parameters |
| **Total (Networks)** | **~1.3GB** | Well within budget |
| Replay Buffer | Optional | Better in system RAM |
| Available for Growth | ~4.7GB | Room for larger networks |

## Expected Training Speed

### Per-Step Training Time

| Operation | CPU Time | GPU Time | Speedup |
|-----------|----------|----------|---------|
| Forward pass (batch=128) | ~150ms | ~8ms | ~19x |
| Backward pass | ~200ms | ~10ms | ~20x |
| Optimizer step | ~50ms | ~5ms | ~10x |
| **Total per step** | **~400ms** | **~23ms** | **~17x** |

### Full Training Timeline

For 10,000 games:
- **Game execution**: ~10 min/game × 10,000 = 70 days (bottleneck)
- **Network training**: 4 steps per game × 10,000 games × 23ms = ~15 minutes total
- **Key insight**: Training overhead is negligible with GPU!

### Realistic Training Schedule

**Week 1-2** (Initial validation):
- Run 500-1000 games
- Time: 3-7 days of continuous game running
- Checkpoint daily, analyze win rate progress

**Week 3-8** (Extended training):
- Continue to 10,000 games
- Pause/resume as needed
- Monitor learning curves

## Installation Commands

### PyTorch with CUDA 11.8
```bash
# For CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Or CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Verify CUDA Installation
```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

Expected output:
```
CUDA available: True
GPU: NVIDIA GeForce RTX 3060 Laptop GPU
```

## Training Configuration

### Recommended Settings for RTX 3060

```python
config = {
    # Hardware
    "device": "cuda",
    "pin_memory": True,  # Faster CPU→GPU transfer
    "num_workers": 2,    # Data loading (if using DataLoader)

    # Network
    "batch_size": 128,    # Increased for GPU
    "replay_buffer_size": 100_000,

    # Training
    "learning_rate": 1e-4,
    "gradient_clip": 10.0,
    "train_every": 4,     # Train every 4 environment steps
    "target_update": 1000,

    # Mixed precision
    "use_amp": True,      # Automatic Mixed Precision
    "amp_dtype": torch.float16,
}
```

## Performance Tips

### 1. Minimize CPU→GPU Transfers
- Keep replay buffer in system RAM
- Transfer only training batches to GPU
- Use `pin_memory=True` for faster transfers

### 2. Overlap Computation and Transfer
- Use non-blocking transfers: `tensor.to(device, non_blocking=True)`
- While GPU trains, CPU can collect next game states

### 3. Maximize GPU Utilization
- Larger batch sizes (128 or 256 if VRAM allows)
- Avoid Python loops on GPU
- Use vectorized operations

### 4. Monitor GPU Usage
```bash
# In another terminal
watch -n 1 nvidia-smi
```

Look for:
- **GPU-Util**: >80% is good
- **Memory-Usage**: Should be ~2-3GB (headroom available)
- **Temperature**: <85°C is safe for laptop

## Bottleneck Analysis

### Current Bottleneck: Game Execution
- Game runs at ~1-2 FPS (AI decision time ~100ms)
- 10 minutes per game average
- **Network training is NOT the bottleneck** (thanks to GPU)

### Future Optimizations (if needed)
1. **Multiple game instances**: Run 2-3 games in parallel
   - Requires multiple game licenses or sandboxing
   - Would reduce training time by 2-3x

2. **Faster game engine**: Skip animations, speed up game
   - Requires game modding
   - Could reduce game time to ~5 minutes

3. **Distributed training**: Multiple machines
   - Complex setup, not needed for validation

## Troubleshooting

### Out of Memory (OOM)
**Symptom**: `RuntimeError: CUDA out of memory`

**Solutions**:
1. Reduce batch size: 128 → 64 → 32
2. Reduce replay buffer: 100k → 50k
3. Disable mixed precision (uses more VRAM)
4. Clear cache: `torch.cuda.empty_cache()`

### Slow Training
**Symptom**: Training not as fast as expected

**Checks**:
1. Verify GPU is being used: `model.device` should be `cuda:0`
2. Check GPU utilization: `nvidia-smi` should show >80%
3. Enable mixed precision: `use_amp=True`
4. Increase batch size if underutilizing GPU

### High Temperature
**Symptom**: GPU temperature >85°C

**Solutions**:
1. Ensure laptop ventilation is clear
2. Use cooling pad
3. Reduce batch size (lower GPU load)
4. Take breaks during long training sessions

## Summary

With your RTX 3060 Laptop GPU:
- ✅ **15-20x faster** network training than CPU
- ✅ **2GB VRAM usage** (well within 6GB budget)
- ✅ **Minimal training overhead** (game execution is bottleneck)
- ✅ **Supports mixed precision** (2x faster, less VRAM)
- ✅ **Can pause/resume** training over weeks/months

The main constraint is **game execution time** (~70 days for 10k games), not computation!
