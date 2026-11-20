"""'참고 파일'로 올라온 문서(기획안 등) 글자 꺼내기. PDF 는 Gemini 가 직접 읽으므로 경로만 넘김.
docx·doc·rtf = macOS textutil, pptx = 슬라이드 XML 의 글자, txt·md = 그대로."""
import os, re, subprocess, zipfile

DOC_EXT = ('pdf', 'txt', 'md', 'docx', 'doc', 'rtf', 'pptx')


def doc_text(path, limit=8000):
    ext = path.rsplit('.', 1)[-1].lower()
    try:
        if ext in ('txt', 'md'): return open(path, encoding='utf-8', errors='ignore').read()[:limit]
        if ext in ('docx', 'doc', 'rtf'):
            return subprocess.run(['textutil', '-convert', 'txt', '-stdout', path], capture_output=True, text=True, timeout=60).stdout[:limit]
        if ext == 'pptx':
            z = zipfile.ZipFile(path); out = []
            names = sorted((n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)), key=lambda n: int(re.findall(r'\d+', n)[-1]))
            for k, n in enumerate(names, 1):
                t = ' '.join(re.findall(r'<a:t>([^<]*)</a:t>', z.read(n).decode('utf-8', 'ignore')))
                if t.strip(): out.append(f'[슬라이드 {k}] {t}')
            return '\n'.join(out)[:limit]
    except Exception as e:
        return f'(문서 읽기 실패: {e})'
    return ''
