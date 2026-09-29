# no-slop

A design skill for coding agents, plus the script that audits the result.

`SKILL.md` is the rules: the tells that make a page read as machine-made, and
what to do instead. `scripts/scan_slop.py` is the enforcement half. Rules that
depend on counting are only as good as the count, so the counts are a program.

```
python3 scripts/scan_slop.py <dir> [--text|--json] [--per-file]
```

Stdlib only, Python 3.8+. Nothing to install.

## Why

AI output converges. Models predict the average of their training data, so
unprompted design decisions land on the same typefaces, the same lavender
gradient, the same three-card feature grid with an icon on top. Knowing this
does not prevent it. The patterns survive even when the designer is aware of
them, which is why every rule here is framed as a check you run on finished
code rather than advice you read once.

## Install

The skill is one markdown file with YAML frontmatter, so it drops into any
agent that loads skills from a directory.

```
# Claude Code
~/.claude/skills/no-slop/SKILL.md

# pi
~/.pi/agent/skills/no-slop/SKILL.md
```

Keep `scripts/scan_slop.py` next to the skill and have the agent run it during
the final audit pass. A skill that describes an audit but never runs one
degrades into advice.

## Usage

```bash
python3 scripts/scan_slop.py ./dist --text
```

```text
verdict: SLOP  (tells=18/4, instances=31, exit=2, files=1)
  [?] inter_sole_identity (Rule 1): inter used as the only identity face; name why
  [!] hero_emphasis (Rule 1): ['<em>Transform</em> your workflow']
  [!] vibecode_purple (Rule 2): ['#6366f1', '#7c3aed', '#8b5cf6', '#a855f7']
  [?] purple_tint (Rule 2): ['hsl(265 85% 60%)', 'rgba(124, 58, 237, 0.5)']
  [?] gradient_count (Rule 2/4): 8
  [!] colored_glows (Rule 2): 2
```

`?` is a judgement call and does not count toward the verdict. `!` does.
`tells` is how many distinct patterns fired, against the threshold of four.
`instances` is the total number of occurrences, which is useful when one
pattern fires twenty times but not the same as the threshold.

Exit codes:

| code | verdict | meaning |
| --- | --- | --- |
| 0 | `clean` | no findings |
| 1 | `review` | only judgement calls, or fewer than four tells |
| 2 | `slop` | four or more tells, the threshold the skill names |

Four or more triggered patterns is the point where a page reads as
machine-made no matter how polished it is. That number is the reason the
verdict exists, and it counts distinct patterns, not repeated instances of
one.

`--json` gives the full report with rule numbers, severities and counts, for
wiring into CI. `--per-file` reports one page at a time.

## What it checks

Every finding maps to a rule in `SKILL.md`.

| check | rule | severity |
| --- | --- | --- |
| `default_fonts` | 1 type | tell |
| `inter_sole_identity` | 1 type | review |
| `hero_emphasis` | 1 type | tell |
| `mono_body` | 1 type | tell |
| `vibecode_purple` | 2 color | tell |
| `purple_tint` | 2 color | review |
| `colored_glows` | 2 color | tell |
| `contrast_failures` | 2 color | tell |
| `glassmorphism` | 4 css | review |
| `gradient_count` | 2/4 | review |
| `left_border_cards` | 2 color | tell |
| `top_accent_borders` | 2 color | review |
| `uppercase_labels` | 3 layout | tell |
| `nested_cards` | 3 layout | tell |
| `numbered_steps` | 3 layout | tell |
| `stat_banner_hits` | 3 layout | review |
| `distinct_radius_values` | 4 css | tell |
| `off_scale_spacing` | 4 css | review |
| `hidden_without_js` | 5 motion | tell |
| `hover_lift_effects` | 5 motion | tell |
| `missing_reduced_motion` | 5 motion | tell |
| `outline_removed` | 7 floor | tell |
| `emoji_count` | 6 copy | review |
| `generic_taglines` | 6 copy | tell |
| `stale_copyright` | 6 copy | tell |
| `missing_og` | 7 floor | tell |
| `missing_favicon` | 7 floor | tell |
| `missing_meta_desc` | 7 floor | review |
| `generic_title` | 7 floor | tell |

## Not checked

The script reads source text. It does not render, does not parse a DOM, and
does not look at images, so these rules still need a human or a vision pass.

- Rule 1: type ramp count, body and display in the same family
- Rule 2: the 70/20/10 budget, the near-black-plus-warm-accent compound
- Rule 3: uniform N-up grids, the hero-slot label budget
- Rule 4: single shadow and border styles, selector specificity
- Rule 5: the one orchestrated moment, perpetual motion
- Rule 5b: whether the signature moment is derived from the subject
- Rule 6: button verb consistency, testimonial plausibility
- Rule 7: working links, responsive down to 360px
- imagery in general: duotone, stock 3D renders, fake app screenshots,
  blob-people illustration sets

## Escaping the verdict

The script cannot tell a default from a decision. A deliberate
lavender-on-black identity will be reported under `vibecode_purple` and
`gradient_count` every time, correctly by the letter of the rules and wrongly
by intent.

Treat the report as a list to argue with, not a gate. When a flagged pattern is
the content, or a named brand decision, say so in the plan and name the
alternative you rejected. That is what the skill asks for anyway: a decision
you can point at beats a pattern you did not notice.

## Tests

```bash
python3 tests/test_scan_slop.py
```

53 assertions across 11 fixtures, one per bug found while building this. They
run against the script in place, so a fixture failing means a check regressed.

## Adding a check

1. Add the regex and the check function.
2. Register it in `CHECKS` with its rule number and severity. Unregistered
   checks report as `?`, which is a bug.
3. Add a fixture under `tests/fixtures/<name>/` that fails before the change.
4. Assert on the JSON output.

A check without a fixture is a guess. Most of the initial ones were wrong in
ways that only showed up when run against real projects.

## License

MIT. See `LICENSE`.

## Contributing

The tells are drawn from published pattern audits of AI-generated interfaces.
New tells are welcome if they come with a fixture that demonstrates the
pattern, since the point is to catch things measurably rather than to list
taste.

Pair with a direction skill upstream: this one checks you did not hit the
clichés, it does not decide what to aim at.
