"""맥 GPU 받아쓰기: venv/mlxw/bin/python -I mlxw.py <소리파일...>  → 파일마다 '시작-끝 문장'(단어 시각은 --words)"""
import sys, mlx_whisper
args = [a for a in sys.argv[1:] if not a.startswith('--')]
words = '--words' in sys.argv
for f in args:
    r = mlx_whisper.transcribe(f, path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='ko', word_timestamps=words)
    if len(args) > 1: print('##', f)
    for s in r['segments']:
        if words:
            for w in s.get('words', []): print(f"{w['start']:6.2f}-{w['end']:6.2f} {w['word'].strip()}")
        else: print(f"{s['start']:6.2f}-{s['end']:6.2f} {s['text'].strip()}")
