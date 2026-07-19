# Avatar generation recipe

The Avatar's icon is the owner's real photo (`knowledge/pic.jpg`) rebuilt as a **synthetic digital
twin**. It is produced programmatically so any site owner gets a matching twin from their own photo.
Three files are produced into `assets/`:

- `avatar-human.png` — natural square crop of the real photo (the **human** icon).
- `avatar-robot.png` — the twin, square, with a HUD frame (hero / showcase use).
- `avatar-robot-round.png` — the twin tuned for circular chat avatars (inner ring, vignette,
  no corner brackets).

## Crop
Square crop centred on the face. For `pic.jpg` (1500×1500): side ≈ 820px, centred at x≈750, with
the eyes at ≈44% from the top (`top = eyeY − 0.44·side`). Output at 900×900.

## Twin treatment (medium "synthetic chrome")
1. **Duotone** the cropped face through a cool deep indigo to periwinkle ramp:
   `#16183f → #2c2f80 → #5156be → #8286d8 → #babdee → #eceefa`.
2. **Smooth then posterise** luminance (small box-blur radius ~2 to kill JPEG speckle, then quantise
   to ~20 bands) for a paneled, rendered look.
3. **Remove the white background** with a border **flood-fill** on near-white / low-saturation
   pixels (a global threshold punches holes in bright skin — use flood-fill from the edges), feather
   the alpha at the boundary.
4. **Scanlines** — 1px darken every 3px. **Paneling seams** — a faint periwinkle `#8286d8` grid +
   a couple of indigo `#5156be` diagonal accent lines, composited `source-atop` so they only fall
   on the figure.
5. **Glowing eyes** — soft periwinkle `#babdee` radial glow + a bright `#eceefa` core at each eye
   position.
6. **Backdrop** — radial deep-indigo `#16183f` gradient with a faint `#8286d8` grid at low opacity.
7. **HUD frame** (square variant) — indigo `#5156be` corner brackets + one green `#2ab57d` tick.
   **Round variant** — inner green `#2ab57d` ring (inset ~5% from the edge, stroke ~3% of the
   diameter, drawn after the vignette) + vignette instead of corner brackets.

The exact, working implementation used to produce the shipped assets is the canvas script in this
project's build history; the parameters above reproduce it. Tune ramp/levels to taste, but keep the
result **recognisably the person**, clearly **synthetic**, and **cool/indigo** to read as the twin.

## Usage
- Human messages & admin owner chip → `avatar-human.png` in `.avatar-human` (indigo `#5156be` ring).
- Avatar messages → `avatar-robot-round.png` in `.avatar-twin` (green `#2ab57d` ring, matching the
  ring baked into the asset so the two read as one).
- Hero / identity showcase → `avatar-robot.png` (framed square).
