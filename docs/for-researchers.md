# For AI researchers and evaluation engineers

You are here because Dali sits in the same problem space as your work — hallucination evaluation, retrieval reliability, model trust, or domain-specific benchmarking. This doc is the 60-minute on-ramp.

If you already know your way around eval benchmarks, skip to [Submit a model to the leaderboard](#submit-a-model-to-the-leaderboard).

---

## What's distinctive about Dali's approach

Most legal-AI evaluations measure whether the model's **output** is correct. Dali measures whether the **evidence behind the output is reconstructable** — provenance, attribution, verifiability, and reconstructability — under a fixed policy version that allows long-horizon replay.

This shifts the unit of analysis from "did the model hallucinate?" to "can a third party, years from now, audit the workflow that produced this citation?" The second framing is the one a court actually applies. We argue it should be the one the eval community uses too.

Three properties make Dali useful as research infrastructure:

1. **Deterministic Tier 1**: the canonical corpus runs offline, with no model calls, producing identical `CitationIntegrityResult` artifacts (down to the SHA-256 evidence hash) given the same policy version. This is testable as a replay invariant.
2. **Policy versioning is enforced**: runs across mismatched policy versions cannot be silently aggregated. The runner refuses without `--allow-cross-version`. This is unusual in current eval infrastructure and we believe it should be standard.
3. **Tier 2 is cross-jurisdictional**: most legal-AI evals are U.S.-common-law only. Dali stresses civil-law structures, non-English sources, and adversarial citation traps as separate tracks — surfacing failure modes that aggregate metrics hide.

See [METHODOLOGY.md](../METHODOLOGY.md) for the full rubric and [docs/policy-versioning.md](policy-versioning.md) for the version invariants.

---

## v0.2 findings, briefly

| Finding | Why it matters for research |
|---|---|
| GPT-4.1 cited on 94% of prompts; 23% of cited URLs return 404 | Citation eagerness without verification is a measurable, model-specific property |
| GPT-4o cited on 26% of prompts; 20% of cited URLs return 404 | Lower citation rate does not automatically mean better — fabrication rate per citation is similar |
| Adversarial citation traps: GPT-4.1 took bait 76% of the time, 48% fabricated URLs | Adversarial robustness in domain-specific citation is much weaker than reported on general benchmarks |
| Brazilian / Portuguese civil-law track: 3% verified vs UK common-law: 76% | A 25× verification gap between two legal systems on the same models — the single most important data point in v0.2 |

Full per-model breakdown: [LEADERBOARD.md](../LEADERBOARD.md). Raw artifacts: [results/v0.2/](../results/v0.2/).

---

## Open methodology questions where researcher input is wanted

Dali's pre-1.0 phase is the right window for methodology critique. Specific questions the maintainer wants challenged:

1. **Does reconstructability add anything over hallucination taxonomy?** Stanford RegLab's "Hallucinating Law" (Dahl, Magesh, Suzgun, Ho, 2024) proposed a hallucination taxonomy. Is Dali's reconstructability framing a re-skin or a genuine refinement? We argue it changes the question from "what did the model do wrong?" to "what can we reconstruct after the fact?" — but the argument deserves adversarial review.
2. **Should Wayback Machine snapshots count as valid evidence?** A citation might resolve today via Internet Archive but not via the canonical source. This is a methodology call that affects scoring. Open issue label: `methodology`.
3. **What's the smallest credible Tier 1 corpus for a defensible follow-up paper?** Currently 3 cases. Expansion is the highest-priority contribution track but the threshold for "credible benchmark size" is a methodology question, not just an engineering one.
4. **Should adversarial-trap performance be weighted higher in the leaderboard ranking?** Currently we display it alongside other metrics. Arguably it should dominate the ranking because adversarial robustness is where real-world failures originate.
5. **How should verification durability decay over time be measured?** v0.5 plans to add temporal drift testing. The right measurement protocol is open.

Engagement on any of these via [GitHub Issues](https://github.com/yenk/Dali/issues) (label `methodology`) is welcomed. Substantive critique is more useful than approval.

---

## Submit a model to the leaderboard

The leaderboard is open. The minimum viable submission runs Tier 2 against any OpenAI-compatible or Anthropic API endpoint and produces a result file under `results/v0.2/<date>-<your-handle>/`.

### 60-minute submission protocol

```bash
git clone https://github.com/yenk/Dali && cd Dali
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set your API key for the provider you want to evaluate
export OPENAI_API_KEY=...
# or ANTHROPIC_API_KEY, etc. — see runners/model_registry.py

python runners/run_synthetic.py \
  --models <your-model-id> \
  --prompts benchmarks/tier2/ \
  --output results/v0.2/$(date +%Y-%m-%d)-<your-handle>/

# Validate
python -m corpus.validator results/v0.2/$(date +%Y-%m-%d)-<your-handle>/
```

Open a PR titled `leaderboard: add <model-id> v0.2 results` adding:

- Your run directory under `results/v0.2/`
- A new row in [LEADERBOARD.md](../LEADERBOARD.md)
- The `policy_version` from your run output (required)

Reviewers verify deterministic replay before merge. Result files are immutable once merged.

See [CONTRIBUTING.md § Result contributions](../CONTRIBUTING.md#result-contributions) for the full protocol.

---

## Other research contributions

| Track | What it looks like | Time |
|---|---|---|
| **Tier 2 prompt corpus** | Add probe prompts in `benchmarks/tier2/` for under-covered jurisdictions or failure modes. EU civil-law and policy/regulatory citations are highest priority. | 2-4 hr |
| **Methodology critique** | Read [METHODOLOGY.md](../METHODOLOGY.md) and open an issue with label `methodology` proposing a specific rubric or scoring change | 2 hr |
| **Reproducibility audit** | Independently replay v0.2 against the same OpenAI models and confirm (or refute) the reported numbers within tolerance. This is a publication-worthy artifact on its own. | 4 hr |
| **Cross-benchmark mapping** | Map Dali's failure-class taxonomy to existing benchmarks (TruthfulQA, HELM, MTBench legal subsets, Patronus FinanceBench-style domain evals) | 1 day |
| **Academic partnership** | Open an issue with label `research-partner` describing your group's interest. Law-school clinics, AI risk labs, legal-empirical research groups especially welcome. | varies |

---

## What you get back

- Named credit in the next release notes and `CITATION.cff`
- Your run results become a permanent, citable artifact (Zenodo DOI pending for v0.3)
- Co-authorship eligibility on the v0.3 technical report for substantive methodology or corpus contributions
- A leaderboard row that other researchers and journalists will cite when discussing the model you evaluated

---

## Related work worth reading first

If you are coming to this cold, the following grounds the conceptual territory:

- Dahl, Magesh, Suzgun, Ho. *Hallucinating Law: Legal Mistakes with Large Language Models are Pervasive.* Stanford RegLab, 2024.
- Charlotin, D. *AI Hallucination Cases Tracker* — canonical running list of court-documented incidents. [damiencharlotin.com/hallucinations](https://www.damiencharlotin.com/hallucinations/).
- AI Incident Database — [incidentdatabase.ai](https://incidentdatabase.ai) — broader catalog of AI incidents; Dali contributes a legal subset.

Dali is positioned upstream of all three: it produces the reproducible evidence artifacts that downstream tracking, taxonomy, and academic work can build on.

---

## Contact

- Methodology questions: open an issue with label `methodology`
- Partnership inquiries: open an issue with label `research-partner`
- For private research collaboration discussions: see contact details on [CITATION.cff](../CITATION.cff)
