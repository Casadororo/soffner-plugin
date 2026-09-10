# soffner-claude-plugin

Personal Claude Code plugin. Each skill is a directory under `skills/` with a single `SKILL.md`.

## Rule: skills are written in English

Every skill in this plugin is written in English. That covers the frontmatter `description`, headings, prose, tables, code comments, subagent prompt templates, role names and placeholder variables.

The `name` is the exception on purpose: it is the slash command the operator types, so it stays whatever they chose, pt-BR included (`dono`). Renaming a skill breaks muscle memory and every saved invocation of it, which is not worth the consistency.

This holds even though the projects these skills drive are pt-BR codebases with pt-BR teams. The skill is instruction for the model, not documentation for the team.

Why:

- Consistency. Half a plugin in English and half in pt-BR makes shared vocabulary drift (`Banca` vs `Panel`, `achado` vs `finding`) and the same concept ends up with two names across skills.
- Portability. A skill written in English is readable by anyone picking up the repo and matches the rest of the skill ecosystem it sits next to.
- Reuse. Prompt fragments get copied between skills; mixed languages inside one prompt is the most common way a template ends up half translated.

### The one exception: content the skill publishes elsewhere

A skill's **source** is English. Text a skill **writes into a pt-BR destination** stays pt-BR:

- PR titles and bodies, review comments and inline comments posted to GitHub.
- Commit messages, when the project's convention is pt-BR.
- Any payload aimed at the pt-BR team rather than at the operator.

`self-review` is the reference case: the whole skill is English, and the JSON payload it posts as a PR review is pt-BR. Wherever this exception applies, say so inline, next to the payload, so nobody "fixes" it later.

Terminal output that a skill prints back to the operator follows the skill: English.

## Naming

kebab-case, lowercase, no accents, and `name:` in the frontmatter must match the directory name. Verb first for a standalone skill (`self-review`), shared prefix when a family exists (`handoff`, `handoff-accept`), so `/handoff` groups them in autocomplete.

## Adding or changing a skill

```bash
mkdir -p skills/<name>
$EDITOR skills/<name>/SKILL.md
claude plugin validate .
```

`claude plugin validate .` catches the two frontmatter traps that pass the eye: a bare `": "` inside `description` breaks the YAML and the skill loads with empty metadata, and a `name` that does not match the directory.
