// 맥 작업기용 저장소 도우미. Vercel Blob → Cloudflare KV 로 갈아탔다(명령 인터페이스는 그대로).
// 기본은 wrangler CLI(로그인 자격증명 재사용). ~/.config/ad-reference/cf.json 에
// {"account_id":"...","namespace_id":"...","token":"..."} 를 넣어두면 REST 로 붙어 훨씬 빠르다.
// node scripts/blob.mjs jobs            → 대기 요청 JSON 배열 출력
// node scripts/blob.mjs done <job>      → 처리한 요청 삭제
// node scripts/blob.mjs status '<json>' → 진행 상태 기록(페이지에 표시)
import fs from 'fs';
import os from 'os';
import path from 'path';
import { execFileSync } from 'child_process';

const NS = 'YOUR_KV_NAMESPACE_ID';
const ACCT = 'YOUR_CF_ACCOUNT_ID';
const CFG = process.env.HOME + '/.config/ad-reference/cf.json';
const C = fs.existsSync(CFG) ? JSON.parse(fs.readFileSync(CFG, 'utf8')) : null;
const useRest = !!(C && C.token);

// ── REST 경로(토큰 있을 때)
const BASE = `https://api.cloudflare.com/client/v4/accounts/${(C && C.account_id) || ACCT}/storage/kv/namespaces/${(C && C.namespace_id) || NS}`;
const H = { Authorization: `Bearer ${C && C.token}` };
const enc = k => encodeURIComponent(k);

// ── wrangler 경로(토큰 없을 때). 로그인해 둔 자격증명을 그대로 쓴다.
const WR = path.join(process.cwd(), 'node_modules/.bin/wrangler');
const wr = args => execFileSync(WR, [...args, '--namespace-id', NS, '--remote'],
  { encoding: 'utf8', env: { ...process.env, CLOUDFLARE_ACCOUNT_ID: ACCT }, maxBuffer: 1 << 28, stdio: ['ignore', 'pipe', 'ignore'] });

async function keys(prefix) {
  if (!useRest) {
    const out = JSON.parse(wr(['kv', 'key', 'list', '--prefix', prefix]));
    return out.map(k => k.name).sort();
  }
  const out = []; let cursor = '';
  do {
    const u = `${BASE}/keys?prefix=${enc(prefix)}&limit=1000${cursor ? `&cursor=${enc(cursor)}` : ''}`;
    const r = await (await fetch(u, { headers: H })).json();
    if (!r.success) throw new Error(JSON.stringify(r.errors));
    out.push(...r.result.map(k => k.name));
    cursor = r.result_info?.cursor || '';
  } while (cursor);
  return out.sort();
}
async function getText(k) {
  if (!useRest) { try { return wr(['kv', 'key', 'get', k]); } catch (e) { return null; } }
  const r = await fetch(`${BASE}/values/${enc(k)}`, { headers: H });
  return r.ok ? await r.text() : null;
}
async function putText(k, v) {
  if (!useRest) {
    const tmp = path.join(os.tmpdir(), 'kv_' + Date.now() + '.txt');
    fs.writeFileSync(tmp, v); try { wr(['kv', 'key', 'put', k, '--path', tmp]); } finally { fs.unlinkSync(tmp); }
    return;
  }
  const fd = new FormData(); fd.append('value', v); fd.append('metadata', JSON.stringify({ at: new Date().toISOString() }));
  const r = await fetch(`${BASE}/values/${enc(k)}`, { method: 'PUT', headers: H, body: fd });
  if (!r.ok) throw new Error(await r.text());
}
async function delKey(k) {
  if (!useRest) { try { wr(['kv', 'key', 'delete', k]); } catch (e) {} return; }
  await fetch(`${BASE}/values/${enc(k)}`, { method: 'DELETE', headers: H });
}

const [cmd, arg] = process.argv.slice(2);
if (cmd === 'jobs') {
  const out = [];
  for (const k of await keys('jobs/')) {
    const t = await getText(k); if (!t) continue;
    out.push({ job: k.slice(5, -5), ...JSON.parse(t) });
  }
  console.log(JSON.stringify(out));
} else if (cmd === 'done') {
  await delKey(`jobs/${arg}.json`);
} else if (cmd === 'fetchup') {   // node blob.mjs fetchup <up> <출력파일> → 조각 합치기
  const parts = await keys(`uploads/${arg}/`);
  const bufs = [];
  for (const k of parts) bufs.push(Buffer.from(await getText(k), 'base64'));   // 조각은 base64 로 올라온다
  fs.writeFileSync(process.argv[4], Buffer.concat(bufs)); console.log(parts.length);
} else if (cmd === 'delup') {
  for (const k of await keys(`uploads/${arg}/`)) await delKey(k);
} else if (cmd === 'cancelled') {   // node blob.mjs cancelled <job> → 1(취소됨)/0
  console.log((await keys(`cancel/${arg}`)).length ? 1 : 0);
} else if (cmd === 'status') {
  await putText('status.json', arg);
}
