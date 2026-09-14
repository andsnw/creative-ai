# Catalog quality policy

Creative AI optimizes for a trustworthy, useful directory — not for the largest possible tool count.

## Acceptance gate

A tool may be added only when all of the following are true:

1. **Official source exists** — the product/project has an identifiable official website, official documentation, or an official source-code repository.
2. **AI is a real product capability** — AI is central to the tool or a clearly documented first-class capability, not an unrelated marketing label.
3. **Clear user value** — the tool solves a concrete task for a recognizable user/workflow and its catalog description can explain that value without vague hype.
4. **Currently usable** — there is evidence the product/project is available, maintained, or meaningfully active at review time. Dead links, abandoned demos, waitlist-only concepts with no usable product, and discontinued products are rejected unless the catalog explicitly supports an archival state.
5. **No duplicate/alias** — no maintained tool already represents the same product or official URL.
6. **No unsupported claims** — descriptions must not invent popularity, adoption, rankings, pricing, capabilities, or launch dates.
7. **Worth recommending or discovering** — inclusion must make the directory more useful. Thin clones, obvious spam/SEO shells, low-information landing pages, and trivial wrappers without meaningful differentiation should not be added merely to increase the count.

## Source preference

Prefer, in order:

1. Official product documentation or official product website.
2. Official source repository for open-source projects.
3. Official company announcements or help center pages when needed to establish availability/capabilities.

Third-party directories may be used only for discovery. They are not sufficient evidence for acceptance by themselves.

## Review record and enforcement

Accepted reviews are stored in `data/catalog-quality.json`. Every accepted review records:

- canonical tool name;
- official URL exactly matching the maintained catalog;
- one or more first-party evidence URLs;
- review date;
- one-sentence concrete user value;
- reviewer decision.

The manifest also records `enforcedForAdditionsAtOrAfter`. Any catalog entry with a lifecycle `event=added` at or after that UTC timestamp must have an accepted quality review, otherwise `scripts/validate_tools.py` fails CI. This prevents future breadth batches from silently adding unreviewed tools.

Rejected candidates should stay in review notes or audit records so the same low-quality entries are not repeatedly reconsidered without new evidence.

## Existing catalog audit

The current catalog predates this strict gate. Existing entries should therefore be audited in batches. A tool not yet present in `data/catalog-quality.json` is **pending re-audit**; that state does not imply that the tool is unsafe or low quality. It only means the stricter review has not yet been completed.

If an audited tool fails the policy, it should be removed or corrected rather than kept just to preserve the catalog count. Removal reasons should be recorded so the decision remains transparent.

Catalog size is a secondary metric. Trustworthiness and usefulness are the primary requirements.
