// 팀원 맥 원격 제작용 Blob 도우미 (2026-11-10). 토큰은 ~/.config/ad-reference/blob_token (출력 안 함)
// node scripts/remote.mjs push <키> <파일>     → 큰 파일 올리기(작업 꾸러미 tar)
// node scripts/remote.mjs pull <키> <파일>     → 받기. 없으면 종료 코드 2
// node scripts/remote.mjs getjson <키>        → JSON 출력, 없으면 null
// node scripts/remote.mjs putjson <키> '<json>'
// node scripts/remote.mjs del <키>
import { get, del, put } from '@vercel/blob';
import fs from 'fs';
const T = fs.readFileSync(process.env.HOME + '/.config/ad-reference/blob_token', 'utf8').trim();
const [cmd, key, arg] = process.argv.slice(2);
const opt = { access: 'private', token: T, addRandomSuffix: false, allowOverwrite: true };
async function fetchBlob(k) {
  try { const r = await get(k, { access: 'private', token: T }); return r && r.stream ? r : null; }
  catch (e) { if (/not.?found|404/i.test(String(e))) return null; throw e; }
}
if (cmd === 'push') {
  await put(key, fs.createReadStream(arg), { ...opt, multipart: true, contentType: 'application/x-tar' });
} else if (cmd === 'pull') {
  const r = await fetchBlob(key); if (!r) process.exit(2);
  const w = fs.createWriteStream(arg);
  for await (const c of r.stream) w.write(c);
  await new Promise(ok => w.end(ok));
} else if (cmd === 'getjson') {
  const r = await fetchBlob(key);
  console.log(r ? await new Response(r.stream).text() : 'null');
} else if (cmd === 'putjson') {
  await put(key, arg, { ...opt, contentType: 'application/json' });
} else if (cmd === 'del') {
  await del(key, { token: T }).catch(() => {});
} else { console.error('알 수 없는 명령 ' + cmd); process.exit(1); }
