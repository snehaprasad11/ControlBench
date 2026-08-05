# ControlBench

**Compare, rank & predict the performance of classical controllers.**

ControlBench takes a plant transfer function G(s), automatically designs a family of
classical controllers (P, PI, PID, lead, lag), evaluates each closed loop on standard
time- and frequency-domain metrics, and ranks them. A machine-learning model predicts
key metrics directly from the transfer function for instant estimates.

## Status

Built in phases — each phase is runnable on its own.

- [x] **Phase 1 — Analysis engine.** Represent and validate a plant G(s); compute
      poles, zeros, order, open-loop stability, damping ratio and natural frequency.
- [ ] Phase 2 — Controller designs (P, PI, PID, lead, lag).
- [ ] Phase 3 — Performance metrics and ranking.
- [ ] Phase 4 — ML dataset generation and metric prediction.
- [ ] Phase 5 — Streamlit dashboard.

## Install

```bash
pip install -r requirements.txt
```

## Try Phase 1

```bash
python scripts/demo_phase1.py
```

```python
from controlbench.analysis import PlantModel

plant = PlantModel([1], [1, 0.4, 1])   # 1 / (s^2 + 0.4 s + 1)
print(plant.summary())
# order 2, underdamped (zeta = 0.2), stable, wn = 1 rad/s
```

## Tests

```bash
pytest
```

## Project layout

```
controlbench/
  analysis/      # Phase 1: PlantModel + (soon) metrics
  controllers/   # Phase 2: classical controller designs
  ml/            # Phase 4: dataset generation, training, inference
scripts/         # runnable demos
tests/           # pytest suite
```
