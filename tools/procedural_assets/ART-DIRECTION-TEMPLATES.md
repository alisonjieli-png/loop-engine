# Reusable creative briefs

Kind: original prompt templates and review criteria. These are instructions,
not generated media, measured anatomy or a guarantee that a provider can obey
every field. Copy the relevant sections into a task-specific brief; leave out
irrelevant fields rather than sending every template to every model.

## Shared brief

Record these decisions once and keep them stable through revisions:

```yaml
brief_version: creative_direction/v1
deliverable: image | editable_2d | editable_3d | video | slideshow | music
purpose: the message or experience this must communicate
audience: who will see or use it
required_content: exact subjects, text, data and permitted source assets
source_rights: origin and permitted use for each supplied reference
style_anchor: the reference features to preserve, not just a style label
must_preserve: identity, silhouette, palette, proportions, approved layout
may_change: explicitly editable parameters
must_avoid: task-specific unwanted features and failure cases
output_contract: format, dimensions, duration, frame rate, color space, alpha
editable_source: native project and dependencies required with the export
review: technical checks, brief compliance and human visual or listening review
```

A style reference can inform shape or lighting without authorizing copied
characters, logos, textures, voices or music. Keep data and quoted content
separate from tool instructions. Do not upload private project material to a
media provider without the task's existing authority.

## Round creature and plush-like bear

Specify silhouette before surface detail. For a round creature: number of body
lobes, total proportions, attachment locations, face size and visible feet.
For a bear: head-to-body ratio, ear radius and separation, muzzle projection,
arm length, foot size and stance. Ratios need a named denominator, and physical
values need units. Never infer a production rig from a painted pose.

```yaml
character:
  archetype: original round creature or bear; no named franchise
  silhouette: one readable body mass, distinct ears or feet where required
  proportions: specify named ratios relative to total height
  face: eye size, spacing, gaze, muzzle, mouth and permitted expressions
  appendages: exact number, attachment points, symmetry and allowed asymmetry
  palette: named material roles with exact colors and approved variations
surface:
  treatment: flat vector | pixel | low-poly | toon | plush-like
  plush_if_selected: pile length, density, fiber direction, seams and stuffing
  material_response: roughness, highlights, translucency and color-space assumptions
pose:
  stance: rest pose, contact points, balance and visible silhouette
  action: the one action being shown, with timing if animated
camera:
  projection: orthographic or perspective; lens only when meaningful
  framing: full body, margins, view direction and ground relationship
lighting:
  setup: key/fill/rim directions, softness, exposure and background separation
consistency:
  locked: proportions, face placement, palette and material identities
  variation: pose or expression changes without redesigning the character
```

Review limb count, silhouette, face placement, intersections, contacts and
consistency across front, side and three-quarter views. For a mesh, inspect
topology and deformation separately. A fur-looking image is not a reusable
fur system. The current Baltor bear constructor is a flat-shaded blockout;
it does not implement plush fibers or skinning.

## Image and static design

State the focal subject, reading order, layout grid, text hierarchy, safe
margins, palette, contrast, background treatment and negative space. Supply
exact copy separately. Name the intended print or screen dimensions and whether
text and shapes must remain editable.

For pixel art, specify the native pixel grid, palette budget, outline rules,
pixel aspect and integer scaling. For vector work, specify shape vocabulary,
stroke weight at a named output size and gradients only where allowed. For
ASCII or Braille, specify the character ramp, cell dimensions, contrast mapping
and treatment of motion flicker. These are different production methods, not
filters that always preserve the same design.

Ask the renderer or model for an output plus a short list of unmet constraints.
Check text independently: a visually convincing title can still contain the
wrong characters. Negative prompts and seed controls are provider-specific;
an adapter must not silently pretend an unsupported control was applied.

## Motion graphics and video

```yaml
sequence:
  duration_seconds: explicit target and allowable tolerance
  frame_rate: explicit rate, including rational rates where required
  shots:
    - purpose: one narrative beat
      time_range: start and end, with units
      subject_action: what moves and what remains fixed
      camera_action: movement, framing and easing
      text: exact copy, hierarchy and minimum readable hold
      transition: type, overlap, continuity and direction
      sound: cue identity, timing, level and permitted source
  motion_rules: pacing, easing vocabulary and maximum visual density
  delivery: aspect ratios, codecs, audio format, alpha and editable project
```

Use explicit scene and element identifiers so feedback can target one cause.
Render low-cost previews first, inspect transitions and final frames, preserve
earlier candidates, then produce the final output. Test a longer title, a new
image and a different aspect ratio. Shortening a film should re-plan beats,
not merely accelerate every frame. A slideshow and a continuously animated
scene need different temporal checks.

## Presentation and slideshow

Give each slide a communication objective, source-backed claim, audience
takeaway, evidence, exact text, visual form and reading order. Define a deck-wide
grid, font roles, spacing, chart conventions, motion vocabulary and exception
policy. Keep speaker notes separate from visible copy.

For each transition, state whether the viewer should perceive continuity,
comparison, escalation or a new topic. Check overflow, contrast, missing fonts,
data accuracy and reading time. Preserve editable charts and objects when the
delivery contract calls for them; a video export alone does not satisfy that.

## Music and sound

```yaml
music:
  role: background bed, theme, stinger, ambience or synchronized cue
  mood_and_arc: emotional intent and changes over time
  tempo_and_meter: explicit BPM and meter, or intentionally free timing
  instrumentation: roles, textures, register and density
  structure: sections, durations, entrances, exits and transition points
  harmony: key or tonal constraints only when required
  vocals: none, supplied authorized lyrics, or a defined original vocal role
  synchronization: scene markers, hit points and tolerance
  mix: foreground priorities, dynamic range and delivery loudness target
  delivery: sample rate, bit depth, channels, stems and loop boundaries
```

Choose loudness and peak targets for the actual destination; do not label one
number universal. Listen for abrupt endings, clipping, phase problems, repeated
artifacts and masking of speech. A model's claimed BPM or key needs measurement
if synchronization depends on it. Preserve rights and voice permissions, and
do not imply access to stems or editable notes when only a final mix is supplied.

## Targeted revision

Record `element`, `time_or_view`, `observed_problem`, `evidence`, `requested_change`
and `must_preserve`. Re-run the relevant checks and compare with the accepted
previous version. Change configuration when possible. Source edits are reserved
for behavior the existing constructor cannot represent. More words alone are
not an improvement: use the smallest brief that captures the actual decisions.
