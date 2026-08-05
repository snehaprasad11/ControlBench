# ControlBench

**Compare, rank & predict the performance of classical controllers.**

ControlBench takes a plant transfer function G(s), automatically designs a family of
classical controllers (P, PI, PID, lead, lag), evaluates each closed loop on standard
time- and frequency-domain metrics, and ranks them. A machine-learning model predicts
key metrics directly from the transfer function for instant estimates.

It is a full-stack application: a **Python engine** exposed through a **FastAPI** REST
backend, with a **React (Vite)** frontend that renders interactive plots via Plotly.js.

## Architecture

```
React + Vite frontend  ──HTTP/JSON──▶  FastAPI backend  ──▶  controlbench engine
 (Plotly.js charts)                    (REST + Swagger)       (analysis · controllers
                                                               · metrics · ML)
```

## Status

Built in phases — each phase is runnable on its own.

- [x] **Phase 1 — Analysis engine.** Represent and validate a plant G(s); compute
      poles, zeros, order, open-loop stability, damping ratio and natural frequency.
- [x] **Phase 2 — Controller designs.** Auto-design P, PI, PID (Ziegler-Nichols with a
      loop-shaping fallback), lead and lag, behind one common interface; close the loop.
- [ ] Phase 3 — Performance metrics and ranking.
- [ ] Phase 4 — ML dataset generation and metric prediction (Jupyter notebooks).
- [ ] Phase 5 — FastAPI backend (REST API).
- [ ] Phase 6 — React + Vite frontend with interactive plots.

## Install

```bash
pip install -r requirements.txt
```

## Try it

```bash
python scripts/demo_phase1.py   # analysis engine on classic plants
python scripts/demo_phase2.py   # design & close the loop for all 5 controllers
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
controlbench/      # Python engine
  analysis/        #   Phase 1: PlantModel + (soon) metrics
  controllers/     #   Phase 2: classical controller designs
  ml/              #   Phase 4: dataset generation, training, inference
api/               # Phase 5: FastAPI backend (REST API)
frontend/          # Phase 6: React + Vite app (Plotly.js charts)
notebooks/         # Phase 4: ML + exploratory Jupyter notebooks
scripts/           # runnable demos
tests/             # pytest suite
```
