# Hypotheses summary — chessbot

Derived view over `research/state.jsonl` (authoritative). Update a row every time a
`hypothesis_status` is logged. Grounding for every hypothesis: `notes/sota_chess_review.md`.

## Taxonomy

| Code | Category | What it varies |
|---|---|---|
| DATA | Training data / labels | Where positions and targets come from (engine vs human, self-play vs relabelled) |
| TARGET | Loss / target parameterisation | How the same labels are turned into a loss (HL-Gauss vs MSE, soft vs one-hot policy) |
| ARCH | Architecture | Network changes at (roughly) equal params |
| SEARCH | Inference-time search | MCTS variants, node budgets, search parameters |
| RL | RL fine-tuning | Self-play / league / expert-iteration recipes on top of the SL net |
| SCALE | Scaling | Params / data / compute sweeps, same recipe |
| DIAG | Diagnostics | No training — measures a property of existing checkpoints |

Primary metric: Elo diff with 95% CI from `chessbot.arena` (paired openings). Puzzles are secondary.

## DATA

| ID | Cat | Name | Verdict | Result |
|---|---|---|---|---|
| H1 | DATA | Engine-labelled vs human-imitation SL | PENDING | predicted ≥ +200 Elo for engine labels, nodes=1 |
| H7 | DATA | SF-relabelled self-play vs pure self-play targets | PENDING | predicted ≥ +40 Elo at equal self-play compute |

## TARGET

| ID | Cat | Name | Verdict | Result |
|---|---|---|---|---|
| H2 | TARGET | HL-Gauss vs MSE value head | PENDING | predicted lower value MAE and ≥ +30 Elo at 400 nodes |

## ARCH

| ID | Cat | Name | Verdict | Result |
|---|---|---|---|---|
| H3 | ARCH | Learned attention bias vs none | PENDING | predicted ≥ +50 Elo at nodes=1 |

## SEARCH

| ID | Cat | Name | Verdict | Result |
|---|---|---|---|---|
| H4 | SEARCH | MCTS 400 nodes vs raw policy | PENDING | predicted ≥ +250 Elo |

## RL

| ID | Cat | Name | Verdict | Result |
|---|---|---|---|---|
| H5 | RL | Gumbel expert-iteration + KL anchor beats SL init | PENDING | predicted ≥ +40 Elo in ≤ 50 GPU-h |
| H6 | RL | No KL anchor → collapse | PENDING | predicted ≥ 50% drop in opening diversity, Elo ≤ SL init |
