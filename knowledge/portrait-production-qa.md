# Image-first portrait production QA

Use this checklist when a project uses illustrated storyboard panels, generated
images, narration or background music. It complements the current editing
workflow and [production safety principles](production-safety-principles.md).
The creator's brief determines format, language, voice, licensed music and
delivery requirements; the examples below are starting points, not platform
requirements or proof of creative quality.

## Measure panels before cropping

- Read the source image's actual width and height. Record measured separator
  boundaries and content rectangles; do not apply coordinates from another
  image or assume the generator returned the requested dimensions.
- When separators or panel sizes vary, measure each panel individually. Check
  bounds, exclude separator pixels, and retain the intended subject. Inspect
  the extracted panels together before encoding.
- Fit panels to the brief's target aspect ratio. Preserve the complete content
  when possible; a cover crop requires an observed focal region. Review the
  resulting composition and caption safe areas instead of accepting a center
  crop automatically.
- Recheck frames from the encoded candidate and delivered MP4. Correct source
  panels alone do not prove that transforms, captions or exports preserved them.

## Audition narration and music

- Select an explicit supported voice and locale from the creator's approved
  settings. For a new voice or changed delivery, audition a short sample with
  numbers, domain terms and natural pauses before batch production. About
  20 to 30 seconds is a useful sample length. Record approval for that exact voice
  and configuration; existing applicable approval may be reused.
- Keep scene IDs traceable across script, narration, captions and edit plan.
  Measure each audio clip and the final scene's available time separately.
  Adjust timing or rewrite with approval when necessary; do not cut the final
  words merely to fit the scene. Keep extensions consistent with the actual
  codec; renaming an MP3 to WAV is not conversion.
- Choose rights-cleared music or an explicitly authorized, available generation
  provider. When music needs revision, compare several short candidates using
  the brief's mood and instrumentation, then listen for unwanted vocals, harsh
  treble, low-frequency rumble, noise, clipping and abrupt endings.
- A provider's success flag or an existing audio file is not a listening review.
  Verify any provider-specific QC schema against the installed tool. Keep the
  selected candidate's source, rights, configuration and measured QC evidence
  in the protected project; no particular music backend is bundled or required.
- Keep narration intelligible, duck background music where needed, and inspect
  loops, crossfades and the tail in the actual final mix.
- Cloud narration or music requires authority to use that service and spend
  credits. Before sending private text, obtain explicit consent for that
  transfer and send only the necessary approved text, not the source document.

## Verify the actual MP4

Keep probe output, tool identity, exit status and measured audio values in the
project's QA record, bound to the exact artifact hash. A missing measurement is
an unresolved check, not a pass.

```bash
ffprobe -v error -show_streams -show_format -of json INPUT.mp4
ffmpeg -nostdin -v error -xerror -i INPUT.mp4 -map 0:v:0 -map "0:a:0?" -f null -
```

Pass the actual local input path as one argument. Check nonzero process exits
and decode errors. Confirm dimensions, display aspect ratio, frame rate,
duration, audio codec and sample rate against the brief; 1080x1920 and AAC at
48 kHz are example portrait delivery settings, not requirements for every job.
When the brief requires narration or music, a missing audio stream is a failure.

The existing [media delivery QA module](../src/media_delivery_qa.py) provides
`check_loudness`, `detect_long_pauses`, `check_av_sync` and
`final_delivery_qa`; invoke their documented Python interfaces rather than
assuming a separate audio QA script is installed. `check_loudness` defaults to
-14 +/- 1 LUFS and a configured -1 dBTP maximum with an existing 0.3 dB
measurement tolerance. Record the policy and actual values; a stricter delivery
brief needs a direct comparison with its threshold. Review silence against scene
timing. Also inspect opening, middle, ending and scene contact sheets for
panel slivers, cropped subjects, unreadable or overlapping captions, black
frames, flashes and unexpected motion. Contact sheets support continuous
playback and listening review; they do not replace it.

## Keep revisions bounded and local

Follow [storage lifecycle](storage-lifecycle.md): render into `_out/_work/`,
validate the candidate, and use the existing atomic publication path for
`_out/current.mp4`. Recheck the delivered bytes and bind QA to their hash.
Keep revision metadata and necessary QA evidence, not an unbounded sequence of
full `final_vN.mp4` copies. Preserve source files and legacy files; only existing
policy-authorized cleanup may remove registered temporary files. Approved or
published milestones remain subject to the existing bounded storage policy.

Record measured framing, voice configuration and approval, music source and
selection, QA findings, artifact hash and revision decisions in the protected
project. Technical checks do not authorize upload. Publishing still requires
authority for the selected channel, title and visibility.
