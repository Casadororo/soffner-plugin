---
name: decide
description: "Use when a step in your work is a CHOICE between known labels rather than something to write - triage, routing, does-this-rule-apply, is-this-a-false-positive, which-severity - and you want it decided by a local typed-decision model instead of by a model turn. Also use when wiring an existing skill or hook to that tool. Never use it for anything that needs reasoning across files, a written explanation, or a judgement the caller cannot enumerate as labels up front: this model picks from a list, it does not think. The contract is the point - the caller branches on the exit code, so a missing tool degrades to whatever the caller already did."
---

# decide

`decide` turns a step that is only a choice into a call to a local model that answers in one forward pass, with no generated text, and returns calibrated probabilities.

It exists because a lot of what a coding agent spends turns on is not writing: it is picking a label from a list it already knows. "Does this rule apply to this diff?" "Is this finding a false positive?" "Is this string user-facing?" Each of those is a round trip that costs a prefill and a turn, and none of them produces prose.

**This is not a reasoning tool.** It picks from labels you supply. It cannot read three files and infer that a query breaks under a specific tenant. Keep that work where it is.

## The contract

Everything below matters less than this table. A caller branches on the exit code and never has to ask whether the tool is installed.

| Exit | Meaning | What the caller does |
|---|---|---|
| `0` | Decided at or above the floor | Use the answer |
| `2` | The request is wrong: bad JSON, unknown question type, too many options, prompt over the head budget | Fix the request. Not a fallback path, a bug in the caller |
| `3` | Unavailable: nothing is listening | **Fall back to whatever you did before this tool existed.** Do not fail, do not ask the user to install anything |
| `4` | Answered, but below `--floor` | Escalate: decide it the way you would have without the tool |

`3` and `4` are deliberately different. `3` is "the tool is not here". `4` is "the tool is here and says it does not know". A caller that collapses them loses the second signal, which is the more useful one.

## Calling it

```bash
echo '{
  "state": { "goal": "...", "subject": "..." },
  "questions": {
    "needs_translation": { "type": "noul", "instructions": "Is this string shown to an end user?" }
  }
}' | decide ask
```

Or `decide ask --request req.json`. Output on stdout, logs on stderr.

```json
{
  "answers": { "needs_translation": { "type": "noul", "noul": 0.93, "confidence": 0.86 } },
  "provider": "laya",
  "model": "multilingual",
  "floor": 0.55,
  "min_confidence": 0.86,
  "abstain": false,
  "elapsed_ms": 214
}
```

### Question types

| Type | `criteria` | Returns |
|---|---|---|
| `choice` | object `label -> description` (or a plain array of labels) | `choice`, plus `probabilities` over every label |
| `score` | ordered array of levels | `score` as the expectation over level indices, a continuous float, plus `legend` |
| `noul` | none | `noul`, which is P(true) from 0 to 1 |

Every answer carries `confidence`, and `confidence` is **normalised Shannon entropy**, not the top probability. A two-way split at 0.51/0.49 has a high top probability and a confidence near zero, which is the number you actually want for a floor.

### State

`state` takes a string, or an object rendered as `KEY: value` lines **in the order you wrote them**.

Write the goal first. This is not style. If you hand a decision model a serialised object, some serialisers sort the keys, and a long field like a list of candidates ends up ahead of the goal, eating the budget until the goal never reaches the model at all. It then answers confidently about a question it never saw. Passing an ordered object, or plain text you built yourself, is what avoids that.

## Three ceilings that decide whether this works

The model has a small, rigid budget, and blowing it does not produce an error at the model layer: it produces a confident wrong answer. `decide` refuses with exit `2` before that happens, and these are the reasons.

**Options per question.** Default ceiling is 12 (`--max-options`). The question prompt and *all* of its options share one budget (`head_max_len`: 192 tokens on `english`, 256 on the others). With sixty options there are about four tokens per label, the labels decode as unreadable ids, and the model picks among them with high confidence. Past 12, shortlist first with something cheap and deterministic, then ask.

**Label length.** Truncated to 48 characters (`--label-chars`). A label is what the model reads; a sentence is not a label.

**State length.** Truncated to 2400 characters (`--state-chars`), tail first. What is left of `max_len` after the head budget is roughly 320 tokens of state on `english` and 768 on the other two.

## Checkpoints

| `--model` | Encoder | State budget | Head budget |
|---|---|---|---|
| `multilingual` (default) | mmBERT-base, 322M | 1024 | 256 |
| `english` | ModernBERT-large, 421M | 512 | 192 |
| `typed-decisions` | ModernBERT-large, 421M | 1024 | 256 |

Always name the checkpoint. The upstream library can route by detected language, which quietly sends non-English text to the multilingual checkpoint no matter what you intended, and reloading weights between requests costs seconds per call.

`multilingual` is the default here because the text these decisions run over (diffs, strings, log lines, mixed-language code) is not English. `typed-decisions` scores better on its own benchmark and was fine-tuned on that benchmark's training split, so treat its numbers as in-domain and not as a promise about yours.

## Honesty about the confidence

The published in-task calibration is good (ECE ~0.03). The published **zero-shot** calibration is not (ECE ~0.20): outside the tasks it was tuned on, it is confidently wrong often enough that a threshold picked by feel is a guess wearing a number.

So:

1. **Set the floor from a labelled sample of your own**, not from the default. Run 30 to 50 cases you already know the answer to, look at where the confidence separates right from wrong, and put the floor there.
2. **Verify deterministically when you can.** If a cheap check exists after the decision (a grep, a status code, a file that must exist), run it. A decision that a mechanical check can confirm should be confirmed by it.
3. **Treat exit `4` as normal traffic**, not an error. A tool that abstains on the hard cases and is right on the easy ones is worth more than one that always answers.

## Running the sidecar

The model is a Python library with no server of its own, so this plugin ships one.

```bash
decide install                 # ~/.decide/venv, then pip install laya
decide up                      # starts it and waits until it answers
decide status                  # exit 0 warm, exit 3 cold
decide selftest                # one fixture decision, refuses a non-model answer
decide down
```

`decide up` blocks until the sidecar actually answers a ping. This matters: the first start builds the checkpoint and the first ever start also downloads it (hundreds of MB). If you start it in the background and do not wait, that whole cost hides inside your first real decision instead.

Keep it resident. A cold checkpoint costs seconds per request; a warm one on CPU is a couple hundred milliseconds. `decide ask` never starts the sidecar on its own, because an implicit start inside a hook would block on a download.

`--provider mock` answers deterministically without any model, for tests. It always reports `confidence: 0`, so it always exits `4` and can never be mistaken for a real decision.

## When not to use it

- The answer is prose, a diff, an explanation, or a plan.
- The labels are not knowable before you look. This model picks from a list; it cannot invent the list.
- You would need more than a couple of hundred tokens of options to state the question.
- A deterministic check already answers it. A `grep` that is always right beats a model that is usually right.
- The decision is rare. One call per session is not worth a resident process; the win comes from volume.
