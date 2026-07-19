# Component Reference

Every class lives in `components.css` and is themed by `tokens.css`. Markup examples are lifted
from the mockups — copy them verbatim and swap content.

## Buttons — `.btn`
Modifiers: `--primary` (green, **submit/important actions only**), `--indigo` (key secondary),
`--secondary` (outline), `--ghost` (quiet), `--icon`, `--sm`, `--lg`. Plus `.btn-send` (the 44px
green send button). Focus ring is indigo.
```html
<button class="btn btn--primary"><svg class="icon icon--sm"><use href="#i-send"/></svg> Submit</button>
<button class="btn-send"><svg class="icon"><use href="#i-send"/></svg></button>
```

## Attention toggle — `.btn-attn`
Sits immediately left of `.btn-send` in the visitor composer. Neutral by
default; clicking adds `.is-on` (amber tint + ring): the next message sent also
pings the human directly via push notification — no special wording needed —
then the button resets to neutral. Uses the `i-spark` icon (the human-attention
mark). Theme-flexible via tokens; amber stays confined to this small control.
```html
<button class="btn-attn" title="Also ping the real human with this message">
  <svg class="icon"><use href="#i-spark"/></svg>
</button>
```

## Fields
`.input`, `.textarea`, `.name-field` (compact inline name/initials field), `.label`. Focus →
indigo ring (`--focus-ring`).

## Switch — `.switch` (Keep chat)
```html
<label class="switch">
  <input type="checkbox" checked>
  <span class="track"><span class="thumb"></span></span>
  <span class="switch-label">Keep chat</span>
</label>
```
On = sky track + sky thumb.

## Badges & status
`.badge` (+ `--attention` amber, `--info` sky, `--unread`, `--dot`, `.badge--dot.is-attention`),
`.chip`, `.kbd` (keyboard key), `.instant-tag` (Qn, sky), `.tool-status` (+ `.is-done`, green
check when returned).

## Avatars
- `.avatar` (+ `--sm` 30, `--lg` 56) — round image holder; set `background-image`.
- `.avatar-initials` — visitor's sky initials token (square, mono).
- `.avatar-twin` — green ring for the Avatar. Use `avatar-robot-round.png`.
- `.avatar-human` — indigo ring + `.spark-badge` for the live human. Use `avatar-human.png`.

## Message bubbles — `.msg`
Wrapper `.msg` + role modifier, containing the avatar element and `.msg-body`
(`.msg-meta` → `.msg-name` / `.msg-time` / tags, then `.bubble`).
- `.msg--visitor` — right aligned, initials token, neutral bubble.
- `.msg--avatar` — left, twin avatar, name "Avatar" in green, `.tool-status` rows allowed above
  the bubble.
- `.msg--human` — left, human avatar, **name-free** `.human-tag` ("The human · live"), indigo
  tinted + glowing bubble. No left-edge bar — the distinction is ring + tint + glow.

## Composer — `.composer`
Flex row: `<textarea>` + `.btn-send`. Auto-grows; focus-within → indigo ring. Always re-focus the
textarea after send.

## Inbox row — `.convo-item`
Grid: avatar / `.convo-main` (`.convo-top > .convo-name`, `.convo-preview`) / `.convo-side`
(time + badge). State classes: `.is-unread` (sky dot), `.is-attention` (amber tint + badge),
`.is-active` (indigo selection indicator). Names truncate with ellipsis; previews single-line.

## Surfaces & utilities
`.card`, `.hairline`, `.eyebrow` (mono caps label), `.display` (serif), `.hud-grid` (decorative
technical grid background), `.scroll` (themed scrollbar).
