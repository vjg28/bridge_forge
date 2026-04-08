# Reward Design Notes

## Current Reward Structure

### Submit (final, 0.0–1.0)
```
reward = structural_pass × span_met × deck_height_met × (
    0.30 × deflection_score +
    0.25 × cost_score +
    0.20 × mass_score +
    0.15 × type_score +
    0.10 × complexity_score
)
```

### Simulate (partial, 0.0–0.6)
```
reward = 0.3 × structural_pass + 0.2 × deflection_score + 0.1 × cost_score
```

### All other steps: reward = 0.0

---

## Proposed: Progress Rewards (per-step shaping)  [Future Iterations]

Small reward (0.0–0.55 max) given after every design step:

| Signal | Reward | Notes |
|---|---|---|
| Bridge type selected | +0.05 | Any valid type |
| Matches recommended type | +0.05 | Bonus on top |
| Span coverage | +0.15 × (actual_span / required_span) | Capped at 1.0 |
| Deck height progress | +0.05 × (max_y / required_height) | Only for hard scenario |
| Members added | +0.02 per member | Capped at 0.10 |
| Supports added | +0.05 per support | Capped at 0.10 |
| Load applied | +0.05 | At least one load present |

**Max progress reward: ~0.55** (always below simulate/submit range)

---

## Open Questions

1. **Cost in simulate formula**: cost_score at simulate time is premature —
   design isn't finalized. Consider removing or replacing with structural readiness.

2. **Simulate formula alternatives**:
   - Option A: `0.3 × structural_pass + 0.2 × deflection_score` (simpler, honest)
   - Option B: `0.4 × structural_pass + 0.2 × deflection_score + 0.1 × span_met` (adds geometry check)

3. **Budget-less scenarios**: Easy has no budget, so cost_score = 1.0 always.
   The 0.1 weight is wasted in simulate for easy tasks.
