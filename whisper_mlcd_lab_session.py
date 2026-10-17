#!/usr/bin/env python3
"""Local speech transcription and word alignment with WhisperX.

Setup (inside an activated conda environment):
    conda install -c conda-forge ffmpeg
    python -m pip install whisperx

Run:
    python whisper_mlcd_lab_session.py --input "input" --output "transcripts"
    python whisper_mlcd_lab_session.py --input "recording.mp4" --language en

Produces timestamped TXT, an ELAN EAF with one speech tier, and JSON with
aligned words. EAF annotations remain segment-level; word timing is in JSON.
Defaults: medium model, Turkish, CPU/int8, batch size 4, Silero VAD.
No speaker identification, face analysis, epochs, gestures or joining.
Each input file is transcribed separately. Model weights may be downloaded on
first use; participant media is processed locally. Review text and timing before
research use. Completed outputs are never overwritten. Python 3.10 recommended.
"""

import argparse
from datetime import datetime
import math
import json
import mimetypes
import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET


EXTENSIONS = {'.mp4', '.mov', '.m4v', '.mkv', '.avi', '.mpeg', '.mpg',
              '.webm', '.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma'}


def timestamp(milliseconds):
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}'


def clean_segments(raw_segments):
    """Preserve model timing; reject invalid or overlapping speech intervals."""
    segments = []
    previous_end = 0
    for raw in raw_segments:
        text = str(raw['text']).strip()
        if not text:
            continue
        start, end = float(raw['start']), float(raw['end'])
        if not all(math.isfinite(v) for v in (start, end)) or start < 0 or end <= start:
            raise ValueError('Invalid speech timestamps; no output was written.')
        start_ms, end_ms = round(start * 1000), round(end * 1000)
        if end_ms <= start_ms or start_ms < previous_end:
            raise ValueError('Overlapping or zero-length speech segments; review the recording.')
        segments.append((start_ms, end_ms, text))
        previous_end = end_ms
    return segments


def make_eaf(media, destination, segments):
    root = ET.Element('ANNOTATION_DOCUMENT', AUTHOR='',
                      DATE=datetime.now().astimezone().isoformat(),
                      VERSION='3.0', FORMAT='3.0')
    header = ET.SubElement(root, 'HEADER', MEDIA_FILE='', TIME_UNITS='milliseconds')
    mime = mimetypes.guess_type(media.name)[0] or 'application/octet-stream'
    attributes = dict(MEDIA_URL=media.as_uri(), MIME_TYPE=mime, TIME_ORIGIN='0')
    try:
        attributes['RELATIVE_MEDIA_URL'] = Path(os.path.relpath(media, destination.parent)).as_posix()
    except ValueError:
        pass  # Windows media and output may be on different drives.
    ET.SubElement(header, 'MEDIA_DESCRIPTOR', **attributes)
    ET.SubElement(header, 'PROPERTY', NAME='lastUsedAnnotationId').text = str(len(segments))
    order = ET.SubElement(root, 'TIME_ORDER')
    slots = {}
    for milliseconds in sorted({v for start, end, _ in segments for v in (start, end)}):
        slot_id = f'ts{len(slots) + 1}'
        slots[milliseconds] = slot_id
        ET.SubElement(order, 'TIME_SLOT', TIME_SLOT_ID=slot_id, TIME_VALUE=str(milliseconds))
    tier = ET.SubElement(root, 'TIER', TIER_ID='speech', LINGUISTIC_TYPE_REF='speech')
    for index, (start, end, text) in enumerate(segments, 1):
        annotation = ET.SubElement(ET.SubElement(tier, 'ANNOTATION'), 'ALIGNABLE_ANNOTATION',
                                   ANNOTATION_ID=f'a{index}',
                                   TIME_SLOT_REF1=slots[start], TIME_SLOT_REF2=slots[end])
        ET.SubElement(annotation, 'ANNOTATION_VALUE').text = text
    ET.SubElement(root, 'LINGUISTIC_TYPE', LINGUISTIC_TYPE_ID='speech',
                  TIME_ALIGNABLE='true', GRAPHIC_REFERENCES='false')
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def export_transcript(media, output, result, model_name):
    # Keep the input extension in output names to distinguish recording.wav/mp4.
    txt_path = output / f'{media.name}.whisperx.txt'
    eaf_path = output / f'{media.name}.whisperx.eaf'
    json_path = output / f'{media.name}.whisperx.json'
    if any(p.exists() for p in (txt_path, eaf_path, json_path)):
        raise FileExistsError('Output already exists. Choose a new --output folder to rerun.')
    segments = clean_segments(result.get('segments', []))
    eaf = make_eaf(media, eaf_path, segments)
    lines = [f'Source: {media.name}', f'Model: {model_name}',
             f'Language: {result.get("language", "unknown")}',
             'Timing: WhisperX alignment; manual review required. Word times are in JSON.', '']
    lines.extend(f'[{timestamp(start)} --> {timestamp(end)}] {text}'
                 for start, end, text in segments)
    if not segments:
        lines.append('[No speech segments returned.]')
    # Exclusive creation protects pre-existing manually corrected outputs.
    json_bytes = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    created = []
    try:
        for path, content in ((txt_path, ('\n'.join(lines) + '\n').encode('utf-8')),
                              (eaf_path, eaf), (json_path, json_bytes)):
            with path.open('xb') as handle:
                created.append(path)
                handle.write(content)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return len(segments)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', type=Path, required=True, help='Media file or folder (not recursive).')
    parser.add_argument('--output', type=Path, help='Default: transcripts folder beside the media files.')
    parser.add_argument('--model', default='medium', help='Whisper model name (default: medium).')
    parser.add_argument('--language', default='tr', help='Language code, e.g. tr, en; auto for detection.')
    parser.add_argument('--batch-size', type=int, default=4, help='Transcription batch size (default: 4).')
    parser.add_argument('--check-only', action='store_true', help='Check files and dependencies without transcription.')
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error('--batch-size must be at least 1')
    source = args.input.expanduser().resolve()
    if source.is_file():
        files = [source] if source.suffix.lower() in EXTENSIONS else []
        base = source.parent
    elif source.is_dir():
        files = sorted((p for p in source.iterdir() if p.is_file()
                        and not p.name.startswith('.') and p.suffix.lower() in EXTENSIONS),
                       key=lambda p: p.name.lower())
        base = source
    else:
        parser.error(f'Input not found: {source}')
    if not files:
        parser.error('No supported audio/video files found in the input.')
    if shutil.which('ffmpeg') is None:
        parser.error('FFmpeg is missing. In the active environment run: conda install -c conda-forge ffmpeg')
    try:
        import whisperx
        # Resolve lazy API imports too, so check-only catches missing dependencies.
        for name in ('load_model', 'load_audio', 'load_align_model', 'align'):
            if not callable(getattr(whisperx, name, None)):
                raise ImportError(f'WhisperX API missing: {name}')
    except ImportError as exc:
        parser.error(f'{exc}\nInstall in the active environment: python -m pip install whisperx')
    output = (args.output or base / 'transcripts').expanduser().resolve()
    print(f'Found {len(files)} media file(s). Output: {output}', flush=True)
    pending = []
    for media in files:
        exists = any((output / f'{media.name}.whisperx.{suffix}').exists() for suffix in ('txt', 'eaf', 'json'))
        print(f'{"SKIP (existing output)" if exists else "READY"}: {media.name}', flush=True)
        if not exists:
            pending.append(media)
    if args.check_only:
        print('Checks passed. Media decoding, model loading and transcription have not been tested.')
        return 0
    if not pending:
        print('Nothing to process. To regenerate outputs, choose a new --output folder.')
        return 0
    output.mkdir(parents=True, exist_ok=True)
    print(f'Loading {args.model} on CPU. First use may download model weights.', flush=True)
    language = None if args.language.lower() == 'auto' else args.language
    model = whisperx.load_model(args.model, 'cpu', compute_type='int8',
                                language=language, vad_method='silero')
    alignment_models = {}
    failures = []
    for index, media in enumerate(pending, 1):
        print(f'\n[{index}/{len(pending)}] {media.name}', flush=True)
        try:
            audio = whisperx.load_audio(str(media))
            raw = model.transcribe(audio, batch_size=args.batch_size, language=language)
            detected_language = raw.get('language') or language
            if raw.get('segments'):
                if not detected_language:
                    raise ValueError('No language available for alignment.')
                if detected_language not in alignment_models:
                    # Retain only one alignment model to limit memory on laptops.
                    alignment_models.clear()
                    alignment_models[detected_language] = whisperx.load_align_model(
                        language_code=detected_language, device='cpu')
                align_model, metadata = alignment_models[detected_language]
                print(f'Aligning words ({detected_language})...', flush=True)
                result = whisperx.align(raw['segments'], align_model, metadata, audio,
                                        'cpu', return_char_alignments=False)
            else:
                result = {'segments': [], 'word_segments': []}
            result['language'] = detected_language
            result['_session'] = {'engine': 'whisperx', 'model': args.model,
                                   'device': 'cpu', 'compute_type': 'int8',
                                   'vad': 'silero', 'batch_size': args.batch_size,
                                   'source': str(media)}
            count = export_transcript(media, output, result, args.model)
            print(f'Saved TXT + EAF + JSON: {count} speech segment(s).', flush=True)
        except Exception as exc:
            failures.append((media.name, str(exc)))
            print(f'ERROR: {media.name}: {exc}', file=sys.stderr, flush=True)
    if failures:
        print('\nFailed files (rerun the same command after resolving errors):', file=sys.stderr)
        for name, error in failures:
            print(f'  {name}: {error}', file=sys.stderr)
        return 1
    print(f'\nCompleted. Review transcripts and timestamps in: {output}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nInterrupted. Completed outputs are preserved; unfinished files restart on rerun.', file=sys.stderr)
        raise SystemExit(130)
