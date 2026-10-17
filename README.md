# MLCD WhisperX Lab Session

This repository contains a small WhisperX-based workflow for transcribing speech from audio/video recordings and exporting timestamped text and ELAN annotations.

> **Important:** No participant or example media files are included in this repository. Place your own media files locally inside the `input/` folder. Research recordings should not be committed to GitHub.

The main script is:

```text
whisper_mlcd_lab_session.py
```

The script transcribes speech, aligns words to the recording, and creates timestamped transcript files and ELAN `.eaf` annotations.

## Repository structure

```text
MLCD_WhisperX_Session/
├── whisper_mlcd_lab_session.py
├── README.md
├── input/
└── transcripts/
```

- `input/` — place the audio/video files you want to process here.
- `transcripts/` — generated automatically when transcription runs.

Keep the original media filenames. Common supported formats include MP4, MOV, WAV, MP3, M4A and FLAC. Video files must contain audio. Each file is processed separately; split recordings are not merged.

---

## 1. Install Miniforge

If Conda is already installed through Miniforge, Miniconda or Anaconda, continue to the next section.

Download Miniforge from the official page:

https://github.com/conda-forge/miniforge#download

### macOS

1. Download the macOS `.sh` installer that matches your computer:
   - `arm64` for Apple Silicon Macs (M1, M2, M3, M4 or newer Apple chips)
   - `x86_64` for Intel Macs
2. Open Terminal.
3. Type `bash` followed by a space, drag the downloaded `.sh` installer into the Terminal window, and press Enter.
4. Follow the installation prompts, accept the default installation folder, and answer `yes` when asked to initialise Conda.
5. Close and reopen Terminal.

### Windows

1. For a standard Intel/AMD 64-bit Windows computer, download `Miniforge3-Windows-x86_64.exe`.
2. Run the installer and keep the option to create Start menu shortcuts enabled.
3. Open **Miniforge Prompt** from the Start menu.
4. Use this prompt for the Windows commands below.

---

## 2. Confirm that Conda is available

In Terminal (macOS) or Miniforge Prompt (Windows), run:

```bash
conda --version
```

A Conda version number should appear.

---

## 3. Install ELAN

Download ELAN for your operating system from:

https://archive.mpi.nl/tla/elan

ELAN is needed to open the `.eaf` annotation files. The `.txt` transcripts can also be opened in a regular text editor.

You do **not** need to install Python separately; it will be installed inside the Conda environment in the next step.

---

## 4. Create the WhisperX environment

Run each command separately in the same Terminal or Conda Prompt window:

```bash
conda create --name mlcd-whisperx python=3.10
conda activate mlcd-whisperx
conda install -c conda-forge ffmpeg
python -m pip install whisperx
```

When Conda asks whether to proceed, type `y` and press Enter.

After activation, you should see something similar to this at the beginning of the prompt:

```text
(mlcd-whisperx)
```

Keep this environment active for the remaining steps.

---

## 5. Prepare the project folder

Clone or download this repository, then place your media files directly inside `input/`.

Example:

```text
MLCD_WhisperX_Session/
├── whisper_mlcd_lab_session.py
├── input/
│   └── recording01.mp4
└── transcripts/
```

Do not place a ZIP file or an additional folder inside `input/`; place the actual media files there.

> Participant/example recordings are intentionally not included in this repository.

---

## 6. Open the project folder in your prompt

### macOS

Type `cd` followed by a space, drag the `MLCD_WhisperX_Session` folder into Terminal, then press Enter.

For example:

```bash
cd ~/Desktop/MLCD_WhisperX_Session
```

### Windows

Open the project folder in File Explorer, copy its full path from the address bar, then enter:

```bat
cd /d "C:\Users\YourName\Desktop\MLCD_WhisperX_Session"
```

If you opened a new Terminal/Prompt window, activate the environment again:

```bash
conda activate mlcd-whisperx
```

---

## 7. Check the setup

From inside `MLCD_WhisperX_Session`, with `mlcd-whisperx` active, run:

```bash
python --version
ffmpeg -version
python whisper_mlcd_lab_session.py --input "input" --check-only
```

Expected results:

- Python 3.10
- FFmpeg version information
- a list of the media files found in `input/`
- a final `Checks passed` message

The check confirms file discovery and basic dependencies. It does **not** load the WhisperX model, decode the media, or test the full transcription workflow.

---

## 8. Run transcription

For Turkish recordings:

```bash
python whisper_mlcd_lab_session.py --input "input" --output "transcripts"
```

Default settings are:

- language: Turkish
- model: `medium`
- device: CPU
- compute type: `int8`
- batch size: `4`
- voice activity detection: Silero

No GPU or CUDA setup is required for this configuration.

The first run may download transcription, voice activity detection, and alignment models, so an internet connection may be required initially. Participant recordings themselves are processed locally.

Processing may take some time. Keep the Terminal/Prompt window open and the computer awake.

### Other languages

For English:

```bash
python whisper_mlcd_lab_session.py --input "input" --output "transcripts" --language en
```

For automatic language detection:

```bash
python whisper_mlcd_lab_session.py --input "input" --output "transcripts" --language auto
```

Language selection applies to every file processed in that run.

### Test one recording first

```bash
python whisper_mlcd_lab_session.py --input "input/recording01.mp4"
```

Replace `recording01.mp4` with the actual filename. Outputs go to `transcripts/` by default.

---

## 9. Output files

For a recording named:

```text
recording01.mp4
```

the `transcripts/` folder will contain files such as:

| Output | Purpose |
|---|---|
| `recording01.mp4.whisperx.txt` | Timestamped transcript readable in a text editor |
| `recording01.mp4.whisperx.eaf` | ELAN annotation file containing the segment-level speech tier |
| `recording01.mp4.whisperx.json` | Aligned segments and word timestamps |

Review wording and timing against the original recording. The EAF and TXT files contain segments, while the JSON file also stores aligned words.

Some words may not receive individual timestamps; missing timestamps should not be interpreted as zero.

If ELAN cannot locate the original media after files are moved, update the media link using **ELAN → Linked Files**.

---

## 10. Returning to the project later

Open Terminal or Miniforge Prompt, activate the environment, navigate to the repository, and run the command again:

```bash
conda activate mlcd-whisperx
python whisper_mlcd_lab_session.py --input "input" --output "transcripts"
```

Existing outputs are preserved. If a TXT, EAF or JSON output already exists for a recording, that recording is skipped.

To regenerate a recording without overwriting an existing corrected output, use a new output directory:

```bash
python whisper_mlcd_lab_session.py --input "input" --output "transcripts_retry"
```

Do not delete manually corrected files unless you are sure they are no longer needed.

If processing is stopped with `Ctrl+C`, completed outputs remain. An unfinished recording starts again from the beginning on the next run; the script does not resume midway through a recording.

At the end of a batch, failed files are listed in the prompt.

---

## Troubleshooting

| Problem | What to try |
|---|---|
| `conda` is not recognised | Windows: use Miniforge Prompt or the Anaconda Prompt from your existing installation. macOS: reopen Terminal after initialisation. |
| macOS still cannot find Conda | If Miniforge was installed in the default folder, run `~/miniforge3/bin/conda init zsh`, then reopen Terminal. For a custom installation folder or another shell, use the corresponding path and shell. |
| Cannot open the `.py` file | Check that the prompt is inside `MLCD_WhisperX_Session` and that the script is named exactly `whisper_mlcd_lab_session.py`. |
| `No module named whisperx` | Activate `mlcd-whisperx`, then run `python -m pip install whisperx`. |
| FFmpeg is missing | Activate `mlcd-whisperx`, then run `conda install -c conda-forge ffmpeg`. |
| No supported media files found | Put the actual audio/video files directly inside `input/`. |
| Model download or alignment fails | Check the internet connection and language setting, then retry. The script reports alignment failures rather than silently exporting unaligned results. |
| `SKIP` / nothing to process | Output files already exist. Use a new `--output` folder if you need to regenerate them. |
| Memory error | Retry with `--batch-size 1`. If needed, use `--model small` with a new output folder. |
| A recording fails or timing is invalid | Read the named file and error message in the prompt. Confirm that the recording plays correctly and contains audible speech. Keep the error message for troubleshooting. |

---

## Data privacy

This repository intentionally excludes research recordings and generated transcripts.

Do not commit participant audio, video, transcripts, annotation files, or other identifiable research data to a public Git repository.

A suitable `.gitignore` should exclude at least:

```gitignore
input/*
!input/.gitkeep

transcripts/*
!transcripts/.gitkeep

*.mp4
*.mov
*.avi
*.mkv
*.mpeg
*.mpg
*.wav
*.mp3
*.m4a
*.flac
*.eaf
*.json
*.srt
*.vtt
```

---

## References

Official setup references used for the original lab guide:

- Miniforge: https://github.com/conda-forge/miniforge
- WhisperX: https://github.com/m-bain/whisperX
- ELAN: https://archive.mpi.nl/tla/elan

The original lab-session setup guide was prepared and checked on 7 October 2026.
