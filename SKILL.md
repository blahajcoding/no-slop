---
name: no-slop
description: A skill that guides an agent on how to make good designs that don't feel generic and AI generated.
---

# No-Slop Design

Remove the statistical tells of AI-generated UI. Use this alongside (or after) the
frontend-design skill: frontend-design gives you a direction worth wanting; this
skill stops your defaults from leaking through while you execute it. The patterns
below were observed surviving *despite* designers knowing about them — treat every
rule as a check you run on finished code, not advice you read once.

## Why these rules exist

AI output converges because models predict the average of their training data.
Every rule here counters one measured, reproducible tell (Krebs' 16-pattern Show HN
audit, Fountain Institute's vibe-coded signs, Aftermark's 500-site report). A page
that triggers 4+ of those patterns reads as machine-made even when it is polished.
Your defense is not taste in the abstract — it is deliberate choices plus a final
audit pass.

## Rule 1 — Type: try and escape the pool

**The test, not the list:** before you reach for a typeface, name the source you're drawing from — a menu, a field guide, a transit sign, an engineering drawing, a mid-century paperback. If you can't name one, you're about to default, and defaulting is what produces the list below.

**Defaulted-to (avoid as a first choice):** Space Grotesk, Geist, Instrument Serif, DM Serif Display, Playfair Display, Poppins, Montserrat, Roboto, Archivo, Spline Sans Mono, IBM Plex, Karla, Besley, Young Serif.

**Inter gets leniency:** Inter is the industry's neutral UI workhorse, not a slop marker by itself. It passes when (a) the product is dense functional UI where neutrality is the point, or (b) it's deliberately paired with a distinctive display face doing the identity work ("Inter body + custom display"). It still reads as default when it's the *sole* identity face on an expressive page — marketing hero, brand site, editorial piece — chosen because nothing else came to mind. If you ship Inter on that kind of page, name what makes your use a decision rather than a default.

These aren't banned because they're bad typefaces — several are excellent. They're on the list because they're what every model reaches for absent a specific reason, so their presence is a signal of no decision having been made, not a signal of bad taste.

**When they're still the right call:** dense, functional UI — data tables, dashboards, admin panels, code editors, forms with many fields — where legibility at small sizes and wide language support outweigh novelty. Inter and Roboto exist because they solve that problem well. If the brief is "internal analytics dashboard," picking Inter because you evaluated it against the alternatives and it won on x-height and tabular figures is a considered choice. Picking it because it's what loads first in your head is the tell.

**When they're not:** marketing pages, hero sections, brand-forward landing pages, anything where the typeface is doing expressive work rather than just rendering text. Here "I couldn't think of anything else" is exactly the failure mode this skill exists to catch.

**Additional hard checks:**
- Never set body and display in the same family "for cohesion".
- Hero H1 gets ONE typographic treatment: size, weight, case, and color are
  uniform across every word. No word recolored, italicized, or set in a second
  style unless removing the emphasis breaks the sentence's meaning (a negation,
  a number, a proper name). Test: render the H1 in grayscale; if your eye lands
  on one word first, flatten it. Serif-vs-sans context is irrelevant — the move
  itself is the fingerprint, in all its variants (italic-in-serif, color-only-
  in-caps, second-family word).
- Minimize monospace faces. Mono is for developer tools — TUIs, CLI tools, IDEs,
  code samples — not for marketing body copy. Setting an entire page's body text
  in mono to signal "technical" or "typewriter aesthetic" is a vibe-coded sign,
  whatever source you can name for it. If mono appears outside code/terminal/
  data contexts, keep it to short labels or metadata lines (a filename, a
  timestamp), never running paragraphs.
- Define a type ramp (max ~5 sizes) before writing components, then never improvise.

## Rule 2 — Color: budget, not vibes

- 70/20/10: dominant neutral, secondary, ONE accent. If a second accent appears,
  it must have a named job (e.g. destructive only).
- No purple/lavender gradients (`#7c3aed`, `#8b5cf6`, `#a855f7` territory) (unless specified by user), no
  neon-on-dark palettes where 4+ hues compete at full saturation.
- Compound check: near-black base + ONE warm accent (gold/amber/orange) + serif
  display is itself a converged default look ("tasteful darkroom"), regardless of
  hue count. Shipping that combination requires naming in the plan a rejected
  alternative palette and why; absent that, shift a variable — accent temperature
  (acid green, oxblood, bone) or base cast (brown, blue, olive instead of black).
  Exception: subjects where warm-accent-on-dark is literal (an actual darkroom,
  astronomy) pass with the one-sentence justification.
- Colored glows and large colored box-shadows are banned unless they represent
  actual light in the subject's world.
- Status dots and side-tab accent stripes only when they encode real state with a
  legend or label. Rainbow-cycling accents cancel emphasis out.
- Body text passes WCAG AA in both themes you ship.

## Rule 3 — Layout: structure earns its container

- Cards only for things that are independently actionable. No card-in-card nesting;
  group with whitespace, proximity, and type size instead.
- Feature sections may not use a uniform N-up grid — same column count, cell
  height, and internal order (figure → heading → body). Present 3+ parallel
  features as ledger rows, mixed-size layout where one feature visibly ranks
  higher, or prose. Test: screenshot the cells and strip the text; if the frames
  are interchangeable, restructure. Illustrations instead of icons do NOT exempt
  you — the tell is the repeated rhythm, not the picture. Exemption: grids of
  pure controls or data (download buttons per platform) with no marketing copy
  inside.
- Eyebrow labels are rationed: at most one per major section, and only when the
  label encodes information (a date, a location, a real category) — not as rhythm.
  All-caps micro-labels above every heading is the single most common surviving AI
  tell.
- Numbered steps only when the numbering does work: you can state what breaks if
  step 2 runs before step 1, AND a later step refers back to an earlier one by
  name. Otherwise delete the numbers — if the prose still reads correctly as
  "first… then… finally," order was never information. Capture→file→review
  flows fail this test essentially always.
- Stat banner rows only with real numbers; never `10k+ users · 99.9% uptime · 24/7`
  filler.
- Between the top of the hero and the H1, nothing appears except content the
  headline depends on. Burden of proof: complete "without this label, the reader
  would misunderstand the H1 because ___." No completable sentence, no label.
  Theming does not earn the slot — a themed pill ("SAFELIGHT ON") is a template
  badge wearing a costume; a fake founding-date eyebrow ("EST. WHEREVER YOU
  THINK") is a template eyebrow wearing a joke. Genuine status badges (beta,
  price, availability) pass because they complete the sentence.

## Rule 4 — CSS discipline: one of everything

Before writing components, declare tokens and use nothing outside them:
- One spacing scale (4px or 8px base). Every margin/padding/gap is a multiple.
- One radius scale: at most THREE values (e.g. 0/2px, 8px, 999px). Eight ad-hoc
  radii reads as accidental even when each looks fine locally.
- One shadow style, one border style, one chip style. Reuse until bored; boredom
  is consistency.
- Glassmorphism (`backdrop-filter`) and gradients need written justification in
  your plan tied to the subject. Count your gradients at the end; more than a
  handful means decoration crept in.
- Watch selector specificity so section paddings don't cancel out.

## Rule 5 — Motion: nothing hidden behind JavaScript

The most common modern animation bug: `.reveal { opacity: 0 }` waiting for an
IntersectionObserver to add a class. Headless renders, no-JS users, and crawlers
see an empty page. Rules:
- Content must be fully visible with JS disabled. Animate with keyframe animations
  that start visible, or add the hiding class via JS at observe-time, never in
  base CSS.
- One orchestrated moment per page: it triggers once, runs ≤ 2s, and ends in a
  resting state. Anything looping indefinitely — marquees, tickers, pulsing
  glows, slow rotates — fails even if it is the page's only animation; perpetual
  motion is itself the tell. Exception: loops that display live state (a clock,
  a progress bar bound to a current value).
- Hover effects may not move layout: color, background, underline — not translateY
  lifts, scales, or rotations on cards.
- Always honor `prefers-reduced-motion`.
- Test: screenshot with JS disabled and with a fresh headless browser. If either
  looks broken, fix the page, not the test.

## Rule 5b — Signature moment must be derived, not generic

The one orchestrated moment must be derived from the subject's own data or
material, not picked from the generative-art defaults: particles connected by
distance lines, drifting gradient blobs, ambient starfields. Test: describe the
animation in one sentence to someone who hasn't seen the page; if they cannot
guess the product, it's a default. Name the derivation in the plan ("lines drawn
from the user's actual backlink counts"), not just the effect.

## Rule 6 — Copy: specific beats clever

- Banned openers: "Transform your…", "Launch faster", "Build your dreams",
  "Create without limits", "Where ideas become…", "The future of…", "Supercharge",
  "Unlock your potential". If a competitor could paste the sentence onto their site
  unchanged, rewrite it.
- Name concrete things: prices, materials, dates, places, numbers. "Book a taster
  — $38" beats "Get started".
- Buttons state the action ("Save changes"), and keep the same verb through the flow.
- Testimonials only if plausible and attributed; otherwise none.
- Footer copyright shows the current year (compute it); no "All rights reversed".

## Rule 7 — Technical floor (non-negotiable)

Every shipped page has:
- `<title>` that names the actual thing (not "Home")
- meta description
- Open Graph tags (og:title, og:description, og:image)
- favicon
- working links only — a social icon that goes nowhere gets deleted, not stubbed
- responsive down to 360px, keyboard focus visible

## Final audit pass (run on the built code, not the plan)

Read your own HTML/CSS like a stranger's and count:
1. Identity faces outside the banned/burned pool? (Inter: check it against the leniency clause, not a flat ban)
2. Accent colors doing numbered jobs ≤ 2?
3. All-caps micro-labels: count them. >3 total = cut.
4. Distinct border-radius values ≤ 3?
5. Gradients counted and justified?
6. Any element invisible without JS?
7. Icon-topped identical cards? Card-in-card?
8. OG tags + favicon + current year present?
9. Any sentence a competitor could reuse verbatim?
10. Template drift: list your section inventory (order, count, grid shapes).
    If it reads eyebrow → H1 → lede → 2 CTAs → fineprint → 3 features → 3 steps
    → 2 plans ($0 left / $N right) → footer, you built the default SaaS grammar
    no matter what the skin looks like. Alter ≥ 2 structural variables: merge
    sections, put evidence before claim, replace one grid with prose, collapse
    pricing to a single row. Boilerplate microcopy (fineprint, plan bullets)
    may not appear verbatim in any two pages you ship — rewrite per page or cut.
11. Hero H1 grayscale test passes (no single-word emphasis)? Monospace confined
    to code/terminal/data contexts?

If any answer fails, fix before presenting. Two minutes of counting beats any
amount of intention.
