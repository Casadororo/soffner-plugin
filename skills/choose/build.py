#!/usr/bin/env python3
"""Builds the page of the choose skill: one self-contained HTML file with the options in groups,
a picture or a code block for each, a note per option and one at the end, and a button that copies
the choices as text to paste back into the chat.

    python3 -I build.py <spec.json> <out.html>

The spec is described in SKILL.md. Images are read relative to the spec and inlined, so the page
opens anywhere, offline, and nothing it shows is fetched from outside. Standard library only.
"""

import base64
import html
import json
import re
import sys
from pathlib import Path

LABELS = {
    "pt-BR": {
        "source": "De onde vem:",
        "note": "nota sobre {key} (opcional)",
        "extra_title": "Mais alguma coisa?",
        "extra_help": "O que faltou, o que mudaria numa opção, ou a ordem em que você quer as coisas.",
        "extra_placeholder": "opcional",
        "preview": "O que será copiado:",
        "copy": "Copiar escolhas",
        "copied": "Copiado! Cole no chat.",
        "clear": "Limpar",
        "clear_confirm": "Limpar todas as escolhas e notas?",
        "count": "{n} escolhidas",
        "count_one": "1 escolhida",
        "none": "nenhuma",
        "note_line": "nota",
        "not_chosen": "não marcada",
        "more": "Mais",
        "one": "Escolha uma.",
        "many": "Marque quantas quiser.",
        "zoom": "imagem ampliada",
        "intro": "Clique numa imagem para vê-la grande. As escolhas ficam salvas neste navegador; o botão no fim copia tudo para colar no chat.",
    },
    "en": {
        "source": "Where it comes from:",
        "note": "note on {key} (optional)",
        "extra_title": "Anything else?",
        "extra_help": "What is missing, what you would change in an option, or the order you want things in.",
        "extra_placeholder": "optional",
        "preview": "What will be copied:",
        "copy": "Copy choices",
        "copied": "Copied! Paste it in the chat.",
        "clear": "Clear",
        "clear_confirm": "Clear every choice and note?",
        "count": "{n} chosen",
        "count_one": "1 chosen",
        "none": "none",
        "note_line": "note",
        "not_chosen": "not chosen",
        "more": "More",
        "one": "Pick one.",
        "many": "Pick as many as you want.",
        "zoom": "enlarged image",
        "intro": "Click an image to see it large. Your choices are kept in this browser; the button at the end copies everything to paste in the chat.",
    },
}

TYPES = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


def fail(said: str) -> None:
    sys.exit(f"build.py: {said}")


def check(spec: dict, base: Path) -> None:
    """Says what is wrong with the spec, before any HTML: a page that copies the wrong ids is worse
    than no page."""
    if spec.get("lang", "pt-BR") not in LABELS:
        fail(f"lang must be one of {', '.join(LABELS)}")
    if not spec.get("groups"):
        fail("the spec has no groups")
    groups, keys = set(), set()
    for group in spec["groups"]:
        for field in ("id", "title", "kind", "options"):
            if field not in group:
                fail(f"a group has no {field!r}: {group.get('id', group.get('title', '?'))}")
        if group["kind"] not in ("one", "many"):
            fail(f"group {group['id']}: kind is 'one' or 'many'")
        if group["id"] in groups:
            fail(f"two groups are {group['id']}")
        groups.add(group["id"])
        chosen = 0
        for option in group["options"]:
            for field in ("key", "title"):
                if field not in option:
                    fail(f"an option of group {group['id']} has no {field!r}")
            if option["key"] in keys:
                fail(f"two options are {option['key']}")
            keys.add(option["key"])
            chosen += bool(option.get("chosen"))
            if option.get("image") and not (base / option["image"]).is_file():
                fail(f"{option['key']}: no image at {base / option['image']}")
            if option.get("image") and Path(option["image"]).suffix.lower() not in TYPES:
                fail(f"{option['key']}: images are {', '.join(TYPES)}")
        if group["kind"] == "one" and chosen > 1:
            fail(f"group {group['id']} picks one, and {chosen} options say chosen")


def inline(path: Path) -> str:
    kind = TYPES[path.suffix.lower()]
    return f"data:{kind};base64,{base64.b64encode(path.read_bytes()).decode()}"


def build(spec: dict, base: Path) -> str:
    lang = spec.get("lang", "pt-BR")
    text = LABELS[lang]
    esc = html.escape
    title = spec.get("title", "")
    store = spec.get("store") or "choose-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    sections = []
    for group in spec["groups"]:
        kind = "radio" if group["kind"] == "one" else "checkbox"
        cards = []
        for option in group["options"]:
            key = option["key"]
            tag = ""
            if option.get("tag"):
                tone = option.get("tone", "")
                tag = f'<span class="tag tone-{esc(tone)}">{esc(option["tag"])}</span>'
            what = f'<p class="what">{esc(option["what"])}</p>' if option.get("what") else ""
            source = (
                f'<p class="source"><b>{esc(text["source"])}</b> {esc(option["source"])}</p>'
                if option.get("source")
                else ""
            )
            visual = ""
            if option.get("image"):
                alt = option.get("alt") or option["title"]
                visual = f'<img class="shot" src="{inline(base / option["image"])}" alt="{esc(alt)}" loading="lazy">'
            if option.get("code"):
                visual += f'<pre class="code">{esc(option["code"])}</pre>'
            checked = " checked" if option.get("chosen") else ""
            cards.append(f"""
      <article class="option" data-key="{esc(key)}">
        <label class="pick">
          <input type="{kind}" name="{esc(group['id'])}" value="{esc(key)}"{checked}>
          <span class="key">{esc(key)}</span>
          <span class="title">{esc(option['title'])}</span>
          {tag}
        </label>
        {what}
        {source}
        {visual}
        <input class="note" type="text" placeholder="{esc(text['note'].format(key=key))}">
      </article>""")
        help_text = group.get("help") or text[group["kind"]]
        sections.append(f"""
    <section class="group" data-group="{esc(group['id'])}" data-title="{esc(group['title'])}">
      <h2><span class="gid">{esc(group['id'])}</span> {esc(group['title'])}</h2>
      <p class="help">{esc(help_text)}</p>
      <div class="options">{''.join(cards)}
      </div>
    </section>""")
    titles = {option["key"]: option["title"] for group in spec["groups"] for option in group["options"]}
    data = {
        "titles": titles,
        "store": store,
        "heading": spec.get("heading") or title,
        "text": text,
    }
    # Inside a <script>, `</` would end it early.
    data_js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    intro = " ".join(part for part in [spec.get("intro", ""), text["intro"]] if part)
    return f"""<!doctype html>
<html lang="{esc(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>
  :root {{ --bg:#1a1b26; --panel:#24283b; --line:#3b4261; --fg:#c0caf5; --muted:#7f88b0; --accent:#bb9af7; --green:#9ece6a; --yellow:#e0af68; --red:#f7768e; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 1240px; margin: 0 auto; padding: 32px 24px 140px; }}
  h1 {{ margin: 0 0 6px; font-size: 26px; }}
  .intro {{ color: var(--muted); max-width: 900px; }}
  .group {{ margin-top: 40px; }}
  h2 {{ font-size: 20px; margin: 0; display:flex; gap:10px; align-items:center; }}
  .gid {{ background: var(--accent); color: var(--bg); border-radius: 6px; padding: 0 9px; font-weight: 700; }}
  .help {{ color: var(--muted); margin: 4px 0 14px; }}
  .options {{ display: grid; gap: 16px; }}
  .option {{ background: var(--panel); border: 2px solid var(--line); border-radius: 12px; padding: 14px 16px 16px; transition: border-color .15s; }}
  .option.on {{ border-color: var(--accent); }}
  .pick {{ display:flex; gap:10px; align-items:center; cursor:pointer; font-size:17px; }}
  .pick input {{ width:20px; height:20px; accent-color: var(--accent); }}
  .key {{ font-family: ui-monospace, monospace; color: var(--accent); font-weight:700; }}
  .title {{ font-weight: 600; }}
  .tag {{ margin-left:auto; font-size:12px; border-radius: 999px; padding: 2px 10px; border:1px solid currentColor; color: var(--muted); }}
  .tone-good {{ color: var(--green); }} .tone-warn {{ color: var(--yellow); }} .tone-bad {{ color: var(--red); }}
  .what {{ margin: 8px 0 2px; }}
  .source {{ margin: 0 0 10px; color: var(--muted); font-size: 13px; }}
  .shot {{ width:100%; border-radius: 8px; border:1px solid var(--line); cursor: zoom-in; display:block; margin-top: 6px; }}
  .code {{ background: var(--bg); border:1px solid var(--line); border-radius: 8px; padding: 12px; overflow-x:auto; font: 13px/1.5 ui-monospace, monospace; margin: 6px 0 0; }}
  .note {{ margin-top: 10px; width:100%; background: var(--bg); color: var(--fg); border:1px solid var(--line); border-radius: 8px; padding: 8px 10px; font: inherit; }}
  .final {{ margin-top: 48px; background: var(--panel); border: 2px solid var(--accent); border-radius: 12px; padding: 18px; }}
  .final textarea {{ width:100%; min-height: 90px; background: var(--bg); color: var(--fg); border:1px solid var(--line); border-radius: 8px; padding: 10px; font: inherit; }}
  pre#preview {{ background: var(--bg); border:1px solid var(--line); border-radius: 8px; padding: 12px; white-space: pre-wrap; font: 13px/1.5 ui-monospace, monospace; }}
  button {{ background: var(--accent); color: var(--bg); border: 0; border-radius: 8px; padding: 10px 18px; font: 600 15px system-ui, sans-serif; cursor: pointer; }}
  button.ghost {{ background: transparent; color: var(--muted); border:1px solid var(--line); }}
  .bar {{ position: fixed; left:0; right:0; bottom:0; background: rgba(26,27,38,.96); border-top:1px solid var(--line); padding: 10px 24px; display:flex; gap:14px; align-items:center; justify-content:center; }}
  .count {{ color: var(--muted); }}
  .copied {{ color: var(--green); font-weight:600; }}
  .zoom {{ position: fixed; inset:0; background: rgba(0,0,0,.85); display:none; align-items:center; justify-content:center; padding: 24px; cursor: zoom-out; }}
  .zoom img {{ max-width: 100%; max-height: 100%; }}
</style>
</head>
<body>
<main>
  <h1>{esc(title)}</h1>
  <p class="intro">{esc(intro)}</p>
  {''.join(sections)}
  <section class="final">
    <h2>{esc(text['extra_title'])}</h2>
    <p class="help">{esc(text['extra_help'])}</p>
    <textarea id="extra" placeholder="{esc(text['extra_placeholder'])}"></textarea>
    <p class="help">{esc(text['preview'])}</p>
    <pre id="preview"></pre>
    <button id="copy">{esc(text['copy'])}</button> <span id="done" class="copied"></span>
  </section>
</main>
<div class="bar"><span class="count" id="count"></span><button id="copy2">{esc(text['copy'])}</button><button class="ghost" id="reset">{esc(text['clear'])}</button><span id="done2" class="copied"></span></div>
<div class="zoom" id="zoom"><img alt="{esc(text['zoom'])}"></div>
<script>
const DATA = {data_js};
const T = DATA.text;
const groups = [...document.querySelectorAll(".group")];

function state() {{
  const picked = {{}}, notes = {{}};
  for (const input of document.querySelectorAll(".pick input")) if (input.checked) (picked[input.name] ||= []).push(input.value);
  for (const option of document.querySelectorAll(".option")) {{
    const note = option.querySelector(".note").value.trim();
    if (note) notes[option.dataset.key] = note;
  }}
  return {{ picked, notes, extra: document.getElementById("extra").value.trim() }};
}}

function text() {{
  const {{ picked, notes, extra }} = state();
  const lines = [DATA.heading, ""];
  for (const group of groups) {{
    const id = group.dataset.group, keys = picked[id] || [];
    const chosen = keys.length ? keys.map(k => `${{k}} ${{DATA.titles[k]}}`).join("; ") : T.none;
    lines.push(`${{id}}. ${{group.dataset.title}}: ${{chosen}}`);
    for (const option of group.querySelectorAll(".option")) {{
      const k = option.dataset.key;
      if (notes[k]) lines.push(`   ${{T.note_line}} ${{k}}${{keys.includes(k) ? "" : " (" + T.not_chosen + ")"}}: ${{notes[k]}}`);
    }}
  }}
  if (extra) lines.push("", `${{T.more}}: ${{extra}}`);
  return lines.join("\\n");
}}

function refresh() {{
  for (const option of document.querySelectorAll(".option")) option.classList.toggle("on", option.querySelector(".pick input").checked);
  const n = document.querySelectorAll(".pick input:checked").length;
  document.getElementById("count").textContent = n === 1 ? T.count_one : T.count.replace("{{n}}", n);
  document.getElementById("preview").textContent = text();
  localStorage.setItem(DATA.store, JSON.stringify(state()));
}}

function restore() {{
  const saved = JSON.parse(localStorage.getItem(DATA.store) || "null");
  if (!saved) return;
  for (const input of document.querySelectorAll(".pick input")) input.checked = (saved.picked[input.name] || []).includes(input.value);
  for (const option of document.querySelectorAll(".option")) option.querySelector(".note").value = saved.notes[option.dataset.key] || "";
  document.getElementById("extra").value = saved.extra || "";
}}

async function copy(where) {{
  const value = text();
  try {{ await navigator.clipboard.writeText(value); }}
  catch {{
    const area = document.createElement("textarea");
    area.value = value; document.body.appendChild(area); area.select();
    document.execCommand("copy"); area.remove();
  }}
  const done = document.getElementById(where);
  done.textContent = T.copied; setTimeout(() => done.textContent = "", 3000);
}}

const defaults = [...document.querySelectorAll(".pick input")].map(input => input.checked);
document.addEventListener("input", refresh);
document.addEventListener("change", refresh);
document.getElementById("copy").onclick = () => copy("done");
document.getElementById("copy2").onclick = () => copy("done2");
document.getElementById("reset").onclick = () => {{
  if (!confirm(T.clear_confirm)) return;
  localStorage.removeItem(DATA.store);
  document.querySelectorAll(".pick input").forEach((input, at) => input.checked = defaults[at]);
  for (const note of document.querySelectorAll(".note")) note.value = "";
  document.getElementById("extra").value = "";
  refresh();
}};
const zoom = document.getElementById("zoom");
for (const shot of document.querySelectorAll(".shot")) shot.onclick = () => {{ zoom.querySelector("img").src = shot.src; zoom.style.display = "flex"; }};
zoom.onclick = () => zoom.style.display = "none";
document.addEventListener("keydown", e => {{ if (e.key === "Escape") zoom.style.display = "none"; }});
restore();
refresh();
</script>
</body>
</html>
"""


def main() -> None:
    if len(sys.argv) != 3:
        fail("usage: python3 -I build.py <spec.json> <out.html>")
    spec_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{spec_path}: {error}")
    base = spec_path.resolve().parent
    check(spec, base)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(spec, base), encoding="utf-8")
    options = sum(len(group["options"]) for group in spec["groups"])
    print(f"{out} · {len(spec['groups'])} groups · {options} options · {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
