Clean 2-Command Workflow
1️⃣ Convert Audio to Tagged Subtitles
Drop your voiceover audio file into srt_generator/input_audio/ and run:

powershell
python srt_generator/audio_to_tagged_srt.py
(Automatically extracts timestamps, runs Gemini 3.6 Flash mascot tagging, and syncs script.srt and voiceover.wav to input/)

2️⃣ Build CapCut Desktop Draft
Drop your two comparison images (image1 & image2) into input/ and run:

powershell
python build_draft.py SupermanVsShazam
(Creates all 6 tracks in CapCut Desktop: Subtitles with LuckiestGuy-Rg font, Mascot overlays at Scale 42%, 1:1 Auto-Cropped Image 1 & Image 2 at Scale 40%, Dotgrid Background, and Audio)