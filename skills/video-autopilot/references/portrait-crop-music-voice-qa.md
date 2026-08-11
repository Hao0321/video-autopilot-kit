# Portrait Crop, Music, Voice, and QA Rules

This reference captures the repeatable workflow for image-first 9:16 teaching videos with Chinese narration and background music.

## 1. Measure before cropping

- Read the storyboard grid's actual pixel dimensions with `ffprobe` or an image library.
- Locate separator lines and crop content rectangles, instead of assuming an even grid or using a center crop.
- Export intermediate panels and inspect a contact sheet before encoding.
- Preserve the complete panel when it is already close to 9:16; use cover crop only when a focal point is known.
- Re-check frames extracted from the formal MP4; a correct source grid does not guarantee correct output framing.

The reference run used a 941×1672 grid. The old 1024×1536 coordinates pulled neighbouring-panel slivers into every shot; using measured separator boundaries fixed the issue.

## 2. Replace rigid music with candidates

- Route new or criticised music to the YT_music ACE-Step workflow.
- Generate three roughly 30-second instrumental candidates first, with explicit mood, tempo, instruments, and negative constraints for vocals, harsh treble, muddy low end, clipping, random noise, static, and abrupt endings.
- Keep only candidates with `status=ok` and `technical_qc=pass` in `summary.json`; retain the job, brief, config, raw/ready files, and summary.
- Select by actual audition, not by peak values alone. When narration exists, duck the music before final loudness normalization.
- Loop shorter music with crossfades and a controlled tail fade.

## 3. Confirm narration before batch generation

- Choose an explicit `zh-TW` voice and create a 20–30 second audition containing Chinese, a number, a domain term, and a natural pause.
- Generate all scene clips only after the user confirms voice, accent, and speed.
- Measure every clip. Pad or trim to the scene target, but compute the last scene's available duration separately so its final sentence is not cut.
- Keep file extensions truthful: Edge TTS output is MP3 unless it has been explicitly transcoded to PCM WAV.

## 4. Deliverable QA

- Use `ffprobe` to verify 1080×1920, 9:16, frame rate, duration, audio stream, and 48 kHz audio.
- Run `audio_qa.py` for -18 to -14 LUFS, True Peak at or below -1 dBFS, and no unexpected silence over 3 seconds.
- Decode the formal MP4 with FFmpeg and inspect opening, middle, ending, and a scene contact sheet.
- Record measured values, selected music candidate, voice ID, user confirmation, and revision filename in `QA.md` and `final_handoff.md`.
