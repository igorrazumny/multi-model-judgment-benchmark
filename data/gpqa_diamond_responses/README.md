# GPQA Diamond — full model responses

Full multi-model **standalone**, **aggregation**, and **debate** outputs for the
**198** GPQA Diamond questions used in the paper evaluation set.

## Contents

| Path | Role |
|------|------|
| `manifest.json` | Index of all items + selection fingerprint |
| `index_by_source.json` | Map `gpqa_diamond_NNN.json` → item file |
| `items/<result_id>.json` | One question + all model responses |

Each item includes:

- `question` — evaluation prompt text as sent  
- `golden_set` — correct-answer metadata used for scoring  
- `scores` — per-model tier scores from the benchmark  
- `tracks.expert` / `tracks.light` — model lists, standalone responses, aggregation per-model text, debate interim (including raw responses per round where recorded)  

## Provenance

- Selection matches the paper’s frozen GPQA condition audit (`selection_sha256` in `manifest.json`).  
- GPQA Diamond is due to Rein et al.; official dataset: https://github.com/idavidrein/gpqa · paper: https://arxiv.org/abs/2311.12022  

## License / use

- **Model outputs** in this directory are released for research replication of the paper.  
- **GPQA questions** remain subject to the GPQA authors’ terms; obtain the official dataset for full licensing context.  

## Note on debate context

Post-debate expert scores in the paper use a **mixed expert + light** argument digest for some items. See the paper’s GPQA condition notes; this dump preserves the recorded tracks so those conditions can be audited.
