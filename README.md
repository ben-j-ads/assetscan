# assetscan

**Is that logo, colour or sound actually yours?** Score your brand's distinctive assets on fame and uniqueness, with charts. Runs on your machine, no dependencies.

Built on the Ehrenberg-Bass distinctive asset grid (Romaniuk, *Building Distinctive Brand Assets*, 2018). Show category buyers an asset with the brand removed, count who name you and who name someone else, and assetscan does the rest.

## Install and run

```bash
pip install .
assetscan serve          # opens the app at http://localhost:8766
```

Or from a terminal: `assetscan scan examples/illustrative_asset_study.csv`.

## What you get

| Output | What it tells you |
|---|---|
| **Distinctiveness Score, 0 to 100** | One number per asset, with a 95% range |
| **Fame** | Share of respondents who named you |
| **Uniqueness** | Of those who named any brand, the share who named you |
| **The grid** | Use or lose, Invest, Avoid solo use, Test or ignore, plus how sure the data is of that box |
| **Who gets the credit** | Which rival is taking your asset's recognition |
| **Fame by segment** | Whether an asset travels beyond your buyers (csv `segment` column) |
| **Known against deployed** | The distinctiveness score against an execution score from a 5-point audit |
| **Warnings** | Thin samples, prompted tests, rivals out-scoring you |

## The maths in four lines

```text
Fame        = named you / shown the asset
Uniqueness  = named you / named any brand
Score       = 100 x Fame^w x Uniqueness^(1-w)        w = 0.5 by default
Intervals   = Wilson 95% on Fame and Uniqueness; Dirichlet posterior (4,000 seeded draws) on the score
```

The geometric mean is deliberate: an asset that is famous but shared, or unique but unknown, scores low. See [docs/RESEARCH.md](docs/RESEARCH.md) for the sources, why each choice was made, and which parts are convention rather than established fact.

## Your data

A csv with `asset,respondents,brand`, then one column per rival (header = rival name). Add `prompted` (yes/no) if you showed respondents a brand list.

```csv
asset,respondents,brand,Rival A,Rival B,Rival C
Lime square logo mark,400,248,22,10,6
```

`examples/illustrative_asset_study.csv` is **invented** to show the output. Do not read anything into it.

### Segments and the audit (v0.2)

Add a `segment` column (one row per asset per segment) and assetscan pools the rows for the headline score and shows each segment separately. Add the audit columns for the execution check:

```csv
asset,segment,respondents,brand,Rival A,check_sound,check_name,check_context,check_consistent,check_instant,touchpoints_used,touchpoints_total
```

The checks come from the IDC distinctive asset audit: recognisable without sound, without the name, out of context; held constant across releases; read by feel rather than explained. Blank means not checked, and is left out rather than counted as a fail. The execution score is shown beside the distinctiveness score and is never blended into it. See `examples/illustrative_segments_and_audit.csv` (invented data).

How many respondents? `assetscan plan --margin 5%` gives 385 per asset for ±5 points on fame at 95% confidence, worst case.

## Honest limitations (v0.1)

- It scores the data you collect. It does not run the survey. Use unbranded stimuli, category buyers and **unprompted** recall.
- The grid lines (fame 30%, uniqueness 50%) and the band cut-offs (20, 45, 70) are defaults, not published standards. Change them in the settings. With a 50% fame line, "famous but shared" can't exist, because more than half naming you leaves under half for rivals.
- Single brand, single market. Segments are pooled by summing counts, so segment sizes should reflect how you want them weighted.
- Score weights are untested against sales outcomes. Treat the score as a ranking aid.
- Has not had independent statistical review.

## Develop

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

MIT licensed. Part of ben.j.ads: marketing science, given away free, for people who spend money.
