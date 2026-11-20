"""직접 추가한 레퍼런스 삭제. 사용: python3 -I delref.py job.json
custom_refs.json 에서 빼고 딸린 파일(원본·썸네일·장면컷·참고 에셋)도 같이 지운다."""
import json, os, sys, glob, shutil

R = '/Users/daun/ad-reference/'
job = json.load(open(sys.argv[1]))
rid = str(job.get('id', ''))
if not rid.isdigit():
    print('잘못된 id', rid); sys.exit(1)

p = R + 'data/custom_refs.json'
cr = json.load(open(p)) if os.path.exists(p) else []
hit = [x for x in cr if str(x['id']) == rid]
if not hit:
    print('없는 레퍼런스', rid); sys.exit(0)

json.dump([x for x in cr if str(x['id']) != rid], open(p, 'w'), ensure_ascii=False, indent=1)

for f in (glob.glob(R + f'data/custom/{rid}.*') + glob.glob(R + f'data/custom/{rid}_f*.jpg')
          + [R + f'site/m/L{rid}.jpg', R + f'data/ref_{rid}.jpg', R + f'data/ref_{rid}_sheet.jpg']
          + glob.glob(R + f'site/m/L{rid}.*')):
    try: os.remove(f)
    except OSError: pass
shutil.rmtree(R + f'data/custom_assets/{rid}', ignore_errors=True)

print('삭제 완료', rid, hit[0].get('name', ''))
