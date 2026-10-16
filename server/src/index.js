// 作業のおとも、棒人間のゴースト置き場（Cloudflare Workers + KV）
//
// 受け付けるのは数字だけ。名前などの自由な文字は受け付けない。
//   POST /ghost   本文: id=16桁の16進&c=線の色(RGB)&p=ポモドーロ数&m=作業分数&f=よくやった動きの番号
//   GET  /ghosts?n=1&me=自分のid   直近24時間のゴーストを最大3人、ランダムに返す（id は返さない）
//     1行1人「色,ポモドーロ数,作業分数,動きの番号,見本なら1」。本物の参加者がいないときは見本を返す
//
// KV には "recent" という1件だけを置き、最大60人・24時間分を入れておく（無料枠の書き込み回数を節約するため）。
// 無料枠（KV の書き込みは1日1000回）を使い切られないように、次のようにしている。
//   ・同じ IP からの書き込みは1分に1回まで（Cache API に印を置く。IP そのものは保存しない）
//   ・同じ id で、前回から10分たっていなくて数字も同じなら、書き込まない
//   ・一覧は毎回最新を読む（古い一覧に上書きして、ほかの人の分を消さないように。読み出しの無料枠は1日10万回）
//   ・KV が上限や混雑で失敗しても 200 を返し、アプリ側は何もしない（見本のゴーストを返す）
//
// フレンド（特定の人と数字だけを見せ合う。メッセージは送れない）
//   POST /friends  本文: id=…&c=…&p=…&m=…&f=…&w=1なら自分の数字を書く&fr=フレンドコードをカンマで（5人まで）
//     1行目「me 自分のフレンドコード」。つづいてフレンドごとに1行
//       「f コード 色 ポモドーロ数 作業分数 動きの番号 何分前か」… おたがいに登録している
//       「w コード」… 相手がまだこちらを登録していない（数字は返さない）
//       「x コード」… そのコードの人がいない
//   フレンドコードは id から計算する8文字（I・L・O・U を使わない英数字）。コードから id はわからない
//   KV には1人1件「u:コード」を置く（id・数字・登録したフレンドのコード）

const DAY = 24 * 60 * 60 * 1000;
const MAX_KEEP = 60;
const SAMPLE_ACTS = [0, 3, 4, 5];

function num(params, key, max) {
  const v = parseInt(params.get(key) || "0", 10);
  return Number.isFinite(v) ? Math.max(0, Math.min(max, v)) : 0;
}

function text(body, status = 200) {
  return new Response(body, {
    status,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

async function readList(env) {
  try {
    const list = await env.GHOSTS.get("recent", { type: "json" });
    return Array.isArray(list) ? list : [];
  } catch (e) {
    return [];
  }
}

// IP ごとの書き込みの間かくを見る。IP はハッシュにしてキャッシュのキーに使うだけで、保存はしない
async function tooSoon(req, ctx, kind = "boutimer:") {
  const ip = req.headers.get("cf-connecting-ip") || "";
  if (!ip) return false;
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(kind + ip));
  const key = Array.from(new Uint8Array(digest).slice(0, 12), (b) => b.toString(16).padStart(2, "0")).join("");
  const cacheKey = new Request("https://throttle.boutimer/" + key);
  const cache = caches.default;
  if (await cache.match(cacheKey)) return true;
  ctx.waitUntil(cache.put(cacheKey, new Response("1", { headers: { "cache-control": "max-age=60" } })));
  return false;
}

const B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
const CODE_RE = /^[0-9A-HJKMNP-TV-Z]{8}$/;

// id からフレンドコード（8文字・40ビット）を作る
async function codeOf(id) {
  const h = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode("boutimer-friend:" + id)));
  let bits = 0n;
  for (let i = 0; i < 5; i++) bits = (bits << 8n) | BigInt(h[i]);
  let s = "";
  for (let i = 0; i < 8; i++) s = B32[Number(bits & 31n)] + s, (bits >>= 5n);
  return s;
}

async function readUser(env, code) {
  try {
    return await env.GHOSTS.get("u:" + code, { type: "json" });
  } catch (e) {
    return null;
  }
}

async function friends(req, env, ctx, now) {
  const raw = await req.text();
  if (raw.length > 300) return text("too long", 413);
  const p = new URLSearchParams(raw);
  const id = (p.get("id") || "").toLowerCase();
  if (!/^[0-9a-f]{16}$/.test(id)) return text("bad id", 400);
  const me = await codeOf(id);
  const fr = [...new Set((p.get("fr") || "").toUpperCase().split(",").map((s) => s.trim()).filter((s) => CODE_RE.test(s) && s !== me))].slice(0, 5);
  const old = await readUser(env, me);
  if (old && old.id !== id) return text("code taken", 409);
  const write = p.get("w") === "1";
  const rec = old ? { ...old } : { id, c: 0, p: 0, m: 0, f: 0, t: 0, fr: [] };
  if (write) Object.assign(rec, { c: num(p, "c", 0xffffff), p: num(p, "p", 99), m: num(p, "m", 1440), f: num(p, "f", 40), t: now });
  rec.fr = fr;
  // 変わったときだけ書く。数字の書きこみは同じ IP から1分に1回まで（フレンドの登録の変更はいつでも書く）
  const frChanged = !old || (old.fr || []).join(",") !== fr.join(",");
  const numChanged = write && (!old || old.c !== rec.c || old.p !== rec.p || old.m !== rec.m || old.f !== rec.f || now - old.t > 10 * 60 * 1000);
  if (frChanged || (numChanged && !(await tooSoon(req, ctx, "friend:")))) {
    try {
      await env.GHOSTS.put("u:" + me, JSON.stringify(rec));
    } catch (e) {
      // 書けなくても、フレンドの数字を返すのは続ける
    }
  }
  const rows = ["me " + me];
  for (const code of fr) {
    const u = await readUser(env, code);
    if (!u) rows.push("x " + code);
    else if (!(u.fr || []).includes(me)) rows.push("w " + code);
    else rows.push(["f", code, u.c, u.p, u.m, u.f, u.t ? Math.max(0, Math.floor((now - u.t) / 60000)) : -1].join(" "));
  }
  return text(rows.join("\n"));
}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const now = Date.now();

    if (req.method === "POST" && url.pathname === "/ghost") {
      const raw = await req.text();
      if (raw.length > 200) return text("too long", 413);
      const p = new URLSearchParams(raw);
      const id = (p.get("id") || "").toLowerCase();
      if (!/^[0-9a-f]{16}$/.test(id)) return text("bad id", 400);
      const g = { id, c: num(p, "c", 0xffffff), p: num(p, "p", 99), m: num(p, "m", 1440), f: num(p, "f", 40), t: now };
      if (await tooSoon(req, ctx)) return text("ok");
      let list = await readList(env);
      const old = list.find((x) => x.id === id);
      if (old && now - old.t < 10 * 60 * 1000 && old.c === g.c && old.p === g.p && old.m === g.m && old.f === g.f) return text("ok");
      list = list.filter((x) => x.id !== id && now - x.t < DAY);
      list.unshift(g);
      try {
        await env.GHOSTS.put("recent", JSON.stringify(list.slice(0, MAX_KEEP)));
      } catch (e) {
        // 無料枠の上限や、同時の書き込み（1秒に1回まで）で失敗したときは、黙ってあきらめる
        return text("busy");
      }
      return text("ok");
    }

    if (req.method === "POST" && url.pathname === "/friends") return friends(req, env, ctx, now);

    if (req.method === "GET" && url.pathname === "/ghosts") {
      const me = (url.searchParams.get("me") || "").toLowerCase();
      const n = Math.max(1, Math.min(3, parseInt(url.searchParams.get("n") || "1", 10) || 1));
      const list = (await readList(env)).filter((x) => x && x.id !== me && now - x.t < DAY);
      for (let i = list.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [list[i], list[j]] = [list[j], list[i]];
      }
      const rows = list.slice(0, n).map((x) => [x.c, x.p, x.m, x.f, 0].join(","));
      // 誰もいないときは見本のゴースト（色・数字は固定）を返す
      if (rows.length === 0) rows.push([0x2a6a8a, 4, 100, SAMPLE_ACTS[Math.floor(Math.random() * 4)], 1].join(","));
      return text(rows.join("\n"));
    }

    return text("boutimer ghost", 404);
  },
};
