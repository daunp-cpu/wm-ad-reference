// 맥 작업기용 Blob 도우미. 토큰은 ~/.config/ad-reference/blob_token (출력 안 함)
// node scripts/blob.mjs jobs            → 대기 요청 JSON 배열 출력
// node scripts/blob.mjs done <job>      → 처리한 요청 삭제
// node scripts/blob.mjs status '<json>' → 진행 상태 기록(페이지에 표시)
import { list, get, del, put } from '@vercel/blob';
import fs from 'fs';
const T = fs.readFileSync(process.env.HOME + '/.config/ad-reference/blob_token', 'utf8').trim();
const [cmd, arg] = process.argv.slice(2);
if (cmd === 'jobs') {
  const out = [];
  for (const b of (await list({ prefix: 'jobs/', token: T })).blobs.sort((a, b) => a.pathname.localeCompare(b.pathname))) {
    const r = await get(b.pathname, { access: 'private', token: T });
    out.push({ job: b.pathname.slice(5, -5), ...JSON.parse(await new Response(r.stream).text()) });
  }
  console.log(JSON.stringify(out));
} else if (cmd === 'done') {
  await del(`jobs/${arg}.json`, { token: T });
} else if (cmd === 'fetchup') {   // node blob.mjs fetchup <up> <출력파일> → 조각 합치기
  const parts = (await list({ prefix: `uploads/${arg}/`, token: T })).blobs.sort((a, b) => a.pathname.localeCompare(b.pathname));
  const bufs = [];
  for (const b of parts) { const r = await get(b.pathname, { access: 'private', token: T }); bufs.push(Buffer.from(await new Response(r.stream).arrayBuffer())) }
  fs.writeFileSync(process.argv[4], Buffer.concat(bufs)); console.log(parts.length);
} else if (cmd === 'delup') {
  for (const b of (await list({ prefix: `uploads/${arg}/`, token: T })).blobs) await del(b.pathname, { token: T });
} else if (cmd === 'cancelled') {   // node blob.mjs cancelled <job> → 1(취소됨)/0
  console.log((await list({ prefix: `cancel/${arg}`, token: T })).blobs.length ? 1 : 0);
} else if (cmd === 'status') {
  await put('status.json', arg, { access: 'private', token: T, addRandomSuffix: false, allowOverwrite: true, contentType: 'application/json' });
}
