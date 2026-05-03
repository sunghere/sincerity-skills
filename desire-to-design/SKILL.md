---
name: desire-to-design
version: 2
description: 'Shape a vague creative desire ("I want to make a game/app/business") into a one-page concept document via a 7-stage dialogue covering motivation, taste, scope, and tradeoffs.'
triggers:
  - desire to design
  - shape vague idea
  - shape an idea
  - vague creative desire
  - I want to make a game
  - I want to build something
  - 만들고 싶어
  - 사업 아이템
  - 게임 만들고 싶어
  - 아이디어 구체화
  - 욕망을 스펙으로
---

# Desire to Design

A skill for transforming vague creative desires into concrete project specifications through structured dialogue.

## When to use this skill

Trigger when **both** of these are true:
1. The user wants to *create* something (game, app, business, book, content, art).
2. They lack concrete direction — vague desire, multiple disconnected ideas, or a specific idea that seems disconnected from their actual capabilities/interests.

Common signals:

- "I want to make a game/app/product" without specifics
- Multiple disconnected ideas thrown out at once ("maybe X, or Y, or Z?")
- Statements about ideal end results ("I want to build something amazing") without process
- Self-doubt mixed with desire ("Am I capable of making this?")
- Asking what's profitable/successful before exploring what they actually want
- A specific idea that seems oddly disconnected from their stated capabilities or interests

The skill works by **resisting the urge to immediately help build what they ask for**. Instead, it shapes the desire into something the person can actually execute.

## When NOT to use this skill

- The user already has a concrete, scoped idea and is asking for implementation help — use task/coding skills instead.
- The request is a small, well-defined task ("write a script that…", "fix this bug"). Vague desire ≠ small task; don't conflate.
- The user explicitly declines structured dialogue ("just brainstorm 10 ideas for me, don't interview me"). Honor it. Offer this skill again later if they get stuck.
- The conversation is mid-implementation of an already-shaped concept; don't reset the user back into discovery mode.

## Core philosophy

Most creative projects fail not from lack of ability, but from:
1. **Mismatched scope** — trying to build the ideal version when they should build the minimum version
2. **Disconnected from self** — building what they think will succeed instead of what they love
3. **Skipping taste analysis** — not knowing what makes something *good* in their eyes
4. **Avoiding tradeoffs** — wanting "all the good things" without choosing
5. **No concrete next action** — staying in idea space forever

This skill addresses each of these in sequence.

## The 7-stage flow

Don't rush through stages. Each stage builds on the previous one. Some users will need extended dialogue at one stage; others will move quickly. **Read the user's energy and depth of response** to gauge pacing.

For an annotated end-to-end run of these stages on a real session, see `references/example-session-flow.md`.

### Stage 0: Calibrate entry point

Before launching into Stage 1, gauge where the user actually is:

- **Already past Stage 1-2?** If they've named their motivation and assets clearly in prior turns, acknowledge those and start at Stage 3 (taste). Don't drag them back through reflection they've already done — that reads as patronizing and wastes the structure.
- **No engagement with the domain?** If the user wants to make something in a domain they haven't deeply consumed (wants to write a novel but doesn't read fiction; wants to ship a SaaS but has never used one daily), recommend a "consumption sprint" first — 5-10 great works in the space — before continuing. Stage 3 will be hollow otherwise. See red flags in `references/domain-prompts.md`.
- **Refuses structured dialogue?** ("Just give me ideas.") Honor it once. Offer the skill again when they hit a wall — usually after the third aimless brainstorm.

Match the user's pace, but hold the line on **Stage 3 (taste)** and **Stage 7 (reality check)**. These are the two stages where desire-to-design sessions silently fail when skipped.

### Stage 1: Honor the desire, then redirect

When the user expresses a vague desire, do NOT:
- Immediately give them a list of options
- Ask "what kind of X do you want to make?"
- Start brainstorming features

DO:
- Acknowledge their desire is valid and common
- Be honest about the realistic difficulty (without being discouraging)
- Identify what they're *actually* looking for: money, freedom, expression, connection, status, mastery
- The right project depends on the right motivation

**Key question to internalize**: "Why do they want to make this, beneath the surface?"

If the user is jumping between very different domains (e.g., "agent company OR puzzle game OR..."), this is a strong signal they don't yet know what they want — they want *something different from their current life*. Name this gently.

### Stage 2: Identify their hidden assets

Most users underestimate what they have. Look for:

- **Domain expertise**: Years in a field gives systems thinking
- **Time investment as taste**: "I've played 1000+ hours of X" means they have a calibrated taste detector for that domain — this is rare and valuable
- **Lived experience**: Pain points they've personally felt are validated problems
- **Network**: People they know who might be customers/users/collaborators

Reflect their assets back to them. Often they don't see these as assets.

Example from real session: User said "I've invested a lot in playing games" — this was reframed as "you have a calibrated taste detector for game fun, which is what most game developers struggle with."

### Stage 3: Taste analysis (the most critical stage)

This is where most "ideation" sessions fail by skipping. Don't skip.

Ask the user to name 3-5 specific works they deeply love in the relevant domain. For each one:
- What was the *specific moment* that hooked them?
- What kept them coming back ("just one more turn")?
- What made them say "I love this"?

Then the harder question: **"You also tried similar works that didn't grab you. What was the one-bit difference?"**

This question separates real taste from surface preferences. The answer reveals their actual aesthetic.

Common categories to probe (adjust per domain):
- Numbers going up vs. new content unlocking vs. systems clicking vs. completion
- Short bursts vs. long sessions
- Solo introspection vs. social
- Mastery vs. discovery vs. expression

The goal: extract their **"fun DNA"** or domain equivalent — a 1-2 sentence articulation of what they uniquely respond to.

**If the user pushes back** ("can we just skip to ideas?"): explain in one sentence why this stage exists ("without this, we'll generate ideas you won't love enough to finish"), then offer a compressed version — three works, one question each — instead of dropping the stage entirely. If they still refuse after that, proceed but flag it: the resulting concept doc should explicitly note "taste DNA not yet articulated; high risk of motivation collapse mid-build."

### Stage 4: Concept generation FROM taste

Now and only now, ask for concepts. The user's concepts will fall into categories:
- ✅ Aligned with their taste DNA → develop further
- ⚠️ Not aligned but they think it'll sell → flag the mismatch honestly
- ❌ Multiple unrelated concepts → ask them to commit (gently)

When they propose multiple ideas, evaluate each honestly with:
- **Strengths**: What works
- **Weaknesses**: What doesn't (be specific, not vague)
- **Risk level**: How hard to execute as solo/small team
- **Pick one** based on the analysis, with reasoning

Don't be wishy-washy here. Users need an honest assessment, not validation. They can always disagree.

### Stage 5: Core mechanic / one-line distillation

Force a one-sentence description. Examples:
- "Marketing tasks automated for solopreneurs" (not "automation platform")
- "Witch in fantasy world becomes a boxer" (not "fighting game")
- "Reorganize your closet without buying anything new" (not "wardrobe app")

If they can't say it in one line, they don't have it yet. Iterate until clarity.

Then identify the **single core feeling/mechanic** the project must deliver. Everything else is in service of this.

### Stage 6: System decisions with explicit tradeoffs

Now design the actual system. For each major decision, present 2-3 options with explicit tradeoffs. Critical principle: **never let "freedom" or "more is better" win unchallenged**.

Common traps to call out:
- "Unlimited freedom" → usually collapses to one optimal choice, killing variety
- "All features" → leads to mediocrity in all
- "Cover all use cases" → no clear identity
- "Make it work for everyone" → works for no one

Each constraint should create *meaningful* choices, not just options.

When the user makes a decision, validate the good ones explicitly and challenge the questionable ones with reasoning. Don't be a yes-man.

### Stage 7: Reality check + scope management

Before finalizing, do a brutal scope check. For solo creators especially:

- **Time estimate**: How many months/years of full-time work?
- **Asset burden**: Is the visual/content workload realistic?
- **Skill gap**: What do they need to learn? Is the learning curve realistic?
- **Iteration capacity**: Can they ship v1 and improve, or is it all-or-nothing?

Common scope reductions to suggest:
- One protagonist instead of many → cuts character art 90%
- Procedural over hand-crafted → trades initial work for replay value
- Cut secondary features → ship core, expand later
- Use existing assets/tools where possible

End this stage with a realistic project size statement in units that fit the domain — months of FTE for software/games, total word count and weekly writing cadence for books, episodes per quarter for podcasts, output volume per month for art/music, runway in months for businesses.

## Producing the final concept document

After working through stages 1-7, **write** the concept document to a file in the working directory. Don't just "offer to compile" — by Stage 7 the user has invested significant time; produce the artifact.

**Filename:**
- Default: `CONCEPT.md` in the working directory.
- If a `CONCEPT.md` already exists (multiple concepts in the same repo, or iterating on prior work), use `<slug>-concept.md` where `<slug>` is a kebab-case short name from the one-line concept (e.g. `boxer-witch-concept.md`).
- If the working directory contains a clear project structure (e.g. `docs/`, `design/`), prefer that location over root.

**Document properties:**
- A single markdown file (not a Word doc unless requested)
- One page if possible, two pages max
- Skimmable: tables, clear headers, key decisions highlighted
- Action-oriented at the end (concrete next steps)
- Written in the user's language (Korean conversation → Korean document)
- Suitable for sharing with collaborators or testing concept appeal

See `references/concept-doc-template.md` for the standard structure.

If the user explicitly says "don't write a file, just summarize," respect that — print the doc inline and skip the file write.

## Conversation principles

**Match the user's language.** If they trigger the skill in Korean, conduct the entire conversation — and write the final document — in Korean. Same for any other language. Don't switch to English just because the skill itself is written in English.

**Be direct, not deferential.** This skill works because of honest pushback. If the user proposes something that won't work, say so with reasoning. Compliments without substance erode trust.

**Match the user's pace.** Some want to move fast through stages; others want to dwell. Watch for signals of "let's keep going" vs "I'm processing this."

**One question at a time during deep stages.** Stages 3 (taste) and 4 (concept) need careful, single-focus questions. Multi-part questions cause shallow answers.

**Use concrete examples liberally.** Reference real games/products/works the user might know. Abstract advice doesn't stick.

**Resist over-formatting in early stages.** Heavy bullet lists feel like consulting deliverables and can make the conversation feel transactional. Save structured output for later stages and the final doc.

**The "one bit difference" probe is your most powerful tool.** When something is unclear or the user is being too general, ask "what's the one-bit difference between the X you loved and the similar X you didn't?"

**Honor sentimental motivations privately.** Sometimes the deep "why" is personal (a partner, a memory, a child). Acknowledge but don't put this front-and-center in the public-facing concept doc — recommend keeping it as private fuel.

## Anti-patterns to avoid

- ❌ Generating a long list of "trending product ideas" when asked for direction
- ❌ Validating every idea equally without honest assessment (sycophancy)
- ❌ Skipping taste analysis to get to "the real work"
- ❌ Letting the user stay in vague space because pushing feels rude

## Domain adaptation

The 7-stage flow works across creative domains. For per-domain vocabulary mapping (taste → fun DNA / pain DNA / reading DNA / etc.) and question banks, see `references/domain-prompts.md`.

## Reference files

- `references/concept-doc-template.md` — Final document structure and example
- `references/domain-prompts.md` — Question banks per domain (games, apps, business, etc.)
- `references/example-session-flow.md` — Annotated example of the flow in action
