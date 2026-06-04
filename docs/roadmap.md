# Dali roadmap

Dali is open citation integrity and evidentiary infrastructure for legal AI systems. The roadmap below communicates direction, not inevitability. Each version exists to make the next one tractable.

## Near-term (next 90 days)

- eyecite integration as the canonical legal citation parser
- CourtListener-backed canonical citation schema and resolution layer
- Evidence JSON v1.0 RFC publication
- expanded cross-jurisdiction benchmark corpus (UK / Commonwealth, Brazil / Civil Law, EU / Regulatory)
- deterministic replay and reproducibility artifacts
- first public multi-model benchmark runs across OpenAI, Gemini, and open-weight models
- expanded benchmark coverage for misattribution, proposition drift, and fabricated authority detection
- contributor and academic partnership expansion around legal AI reproducibility research

## Future Tier 1 corpus expansion

Additional scoring-eligible Tier 1 records are limited to court-documented or otherwise canonically retrievable legal AI citation failures with:

- authoritative source URLs
- retrieval timestamps
- reproducible verification paths
- stable citation metadata
- documented judicial or regulatory context

Potential future additions include:

- additional sanctions orders
- judicial findings involving fabricated authorities
- citation-related disciplinary proceedings
- court-documented retrieval failures
- verified legal filing incidents involving non-existent authorities

Unverified anecdotes, social-media reports, or non-reproducible claims do not become scoring-eligible benchmark records. This constraint is not a limitation. It is what makes the Tier 1 corpus defensible.

The highest-value corpus contributions are court documents, sanctions orders, and judicial findings that are already in the public record and can be independently retrieved. Expanding the corpus with weaker sourcing would undermine the evidentiary thesis the benchmark is built on.

## Benchmark expansion path

| Version | Focus | Goal |
|---|---|---|
| v0.3 | EU / Regulatory + clearer coverage model | Add high-relevance regulatory and multilingual legal-policy citations without optimizing for raw prompt count |
| v0.4 | Evidence-pathway analysis | Move beyond jurisdiction labels into generated citation, retrieved source, verified state, evidence artifact, and reconstruction test |
| v0.5 | Durability metrics | Add temporal drift, source decay, reconstructability scoring, and evidence replay testing |

See [benchmark-expansion-strategy.md](benchmark-expansion-strategy.md) for the jurisdiction strategy and v0.3-v0.5 rationale.

## Long-range direction

| Version | Focus |
|---|---|
| v1 | normalization |
| v2 | relationship modeling |
| v3 | semantic verification |
| v4 | temporal replay |
| v5 | cross-jurisdiction interoperability |

Each version is scoped narrowly. Ontology expansion is deliberately resisted, a new category is added only when an existing one demonstrably collapses two distinct legal behaviors into the same bucket.

## What this is not

- a chatbot or legal copilot
- a RAG retrieval layer
- a search engine
- a generalized AI governance or compliance platform

Dali is narrowly the citation integrity and evidentiary replay layer for legal AI systems. Adjacent capabilities belong in adjacent tools.
