# GPQA Diamond

## Official dataset

- **Paper:** Rein et al., *GPQA: A Graduate-Level Google-Proof Q&A Benchmark* — https://arxiv.org/abs/2311.12022  
- **Repository:** https://github.com/idavidrein/gpqa  

## Full model responses (this package)

We **publish full multi-model responses** (standalone, aggregation, debate) for
the 198-question paper evaluation set under:

```text
data/gpqa_diamond_responses/
```

See that directory’s README and `manifest.json`. Questions as used in our
prompts are included with model outputs for replication; official GPQA
licensing still applies to the underlying benchmark.

## Role in the paper

GPQA provides **known-answer** closed-form evaluation. Production tasks use
leave-one-out consensus alignment and are a different construct—see the paper’s
Limitations and GPQA condition notes (mixed expert/light post-debate context).
