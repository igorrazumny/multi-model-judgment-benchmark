# GPQA Diamond (external)

This reference package **does not redistribute** GPQA Diamond question text.

## Obtain the dataset

- **Paper:** Rein et al., *GPQA: A Graduate-Level Google-Proof Q&A Benchmark* — https://arxiv.org/abs/2311.12022  
- **Repository:** https://github.com/idavidrein/gpqa  

Download Diamond according to the authors’ terms, then point evaluation scripts
at your local path.

## Role in the paper

GPQA provides **known-answer** closed-form evaluation. Production tasks use
leave-one-out consensus alignment and are a different construct—see the paper’s
Limitations and GPQA condition notes (mixed expert/light post-debate context).
