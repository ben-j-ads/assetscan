# Research notes

What is established, what is convention, and what I couldn't verify. Researched 2026-10-19.

## The framework

Romaniuk's distinctive asset method (Ehrenberg-Bass Institute, *Building Distinctive Brand Assets*, Oxford University Press, 2018) scores each asset on two axes:

- **Fame:** the proportion of category buyers who, shown the asset without the brand name, link it to the brand.
- **Uniqueness:** how exclusively the link belongs to one brand. The more an asset is shared with rivals, the weaker it is.

Quadrants, per the Institute's summary: famous and unique = **use or lose**; unique but not famous = **invest**; famous but shared = **avoid** (it can trigger competitors to copy you); neither = **test or ignore**.

Method points that matter: use unbranded stimuli, sample category buyers, and measure **unprompted**. Romaniuk reports that prompting inflates fame by up to about 20 points. A separate Journal of Brand Management study found marketers tend to overestimate fame and underestimate uniqueness.

## What assetscan chose

| Choice | Why | Status |
|---|---|---|
| Fame = named you / shown | Matches the definition | Established |
| Uniqueness = named you / named any brand | The Institute's secondary summaries state it as "your attributions over all attributions for the cue" | Consistent with secondary sources, not checked against the book |
| Score = weighted geometric mean | Both axes must be present; arithmetic means let a famous-but-shared asset look fine | **My design.** Not a published metric |
| w = 0.5 | No evidence for another weight. One practitioner source argues fame matters more, so it's adjustable | Convention |
| Wilson intervals | Correct at small n and at 0 or 100%, unlike the normal-approximation interval | Standard statistics |
| Dirichlet(1,1,1) posterior for score range and box probability | Fame and uniqueness come from the same respondents, so they must be sampled jointly | Standard Bayesian practice; seeded for repeatability |
| Fame line 30%, uniqueness line 50% | See below | Convention, adjustable |
| Bands 20/45/70 | A readable scale | Convention |

## The 50/50 problem

With fame = b/n and uniqueness = b/(b+r), where b + r <= n: if fame >= 50% then r <= n - b <= b, so uniqueness is always >= 50%. A grid with both lines at 50% can never put an asset in "avoid". So the default fame line is 30%. I could not find a primary-source cut-off. One blog cites "over 70% fame and over 60% uniqueness" for the Institute; I could not confirm it from an Institute source, so it is not used.

## v0.2 additions

- **Segments:** rows for the same asset in different segments are pooled by summing counts (independent respondents), and each segment is scored on its own. Pooling weights segments by sample size, so design the sample deliberately.
- **Execution audit:** the five checks are the IDC monthly audit's list (without sound, name and context; held constant; System 1), drawn from the Ehrenberg-Bass distinctive asset idea and Orlando Wood's System 1 work. Score = share of checked items passed, averaged with touchpoint coverage (used / audited). **My design, not a published metric.** Unchecked items are excluded, not failed, so a half-audited asset isn't punished. It is kept apart from the survey score on purpose: the two measure different things (deployed vs known), and blending would hide which one is the problem.

## Sample size

For a proportion near 50% at 95% confidence, ±5 points needs 385 respondents and ±10 needs 97. Uniqueness rests only on people who named some brand, so a low-fame asset needs a larger sample for the same precision. assetscan warns under 100 respondents and under 30 attributions.

## Not covered yet

- Primary-source check of the uniqueness formula and any published thresholds (the book, Romaniuk's Journal of Brand Management papers).
- Time series (the same asset across waves).
- Validation of the execution score against outcomes. It is a transparent checklist, not a tested predictor.

## Sources

- Ehrenberg-Bass Institute, [Brands need distinctive assets](https://www.marketingscience.info/brands-need-distinctive-assets) and [Brands of distinction](https://marketingscience.info/news-and-insights/brands-of-distinction)
- Contagious, [Jenni Romaniuk on distinctive assets](https://contagious.com/io/article/jenni-romaniuk-on-distinctive-assets)
- Umbrex, [Distinctive Brand Assets Framework](https://umbrex.com/resources/frameworks/marketing-frameworks/distinctive-brand-assets-framework-ehrenberg-bass/) (secondary)
- Marketing Week, [Marketers' judgement of brand asset strength 'rarely accurate'](https://www.marketingweek.com/marketers-judgement-strength-brand-assets-rarely-accurate/)
- Romaniuk, J. (2018). *Building Distinctive Brand Assets*. Oxford University Press.
