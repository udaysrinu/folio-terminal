// Vercel serverless function — NSE last prices, no API key, no credentials.
//
// WHY THIS EXISTS
// Yahoo serves NSE prices free and unmetered, but sends no Access-Control-Allow-Origin, so a browser
// refuses to hand the response to page JavaScript. That restriction applies to browsers only: this
// function is not a browser, so it can read Yahoo directly and re-serve the answer with the header
// attached. Nothing here is authenticated — that is the whole point. Compare the alternative, a Kite
// proxy, which would need an access_token that can PLACE AND CANCEL ORDERS.
//
// Deploy: import this repo into Vercel. Vercel serves the static pages AND this function from one
// origin, which means the page's price call is same-origin and the CORS dance below is only needed
// for other hosts (a local dev server, or a GitHub Pages mirror). No env vars, no secrets, nothing
// to rotate.
//
//   GET /api/price?symbols=GRSE,JWL,DYNAMATECH
//   -> {"prices":{"GRSE":2600.1,"JWL":251.85},"missing":["DYNAMATECH"],"asof":"2026-08-17T…"}

const MAX_SYMBOLS = 60;      // one basket is ~25; a cap keeps a stray loop from burning the free tier
const TIMEOUT_MS  = 8000;

// Only these origins may read the response. A wildcard would work — there are no credentials to
// protect — but naming origins stops other sites casually using this endpoint as free infrastructure.
// Same-origin requests send no Origin header and need nothing here. These cover the other hosts the
// page might be served from. A wildcard would be safe — there are no credentials to protect — but
// naming origins stops other sites using this as free infrastructure.
const ALLOWED = [
  'https://sharecase.vercel.app',
  'http://localhost:8899',
  'http://localhost:3000',
];

async function yahooPrice(sym) {
  // v8 chart, not v7 quote: v7 batch now demands a crumb/cookie, v8 needs nothing. One symbol per
  // request, which is fine — they run in parallel and Yahoo is not metering us.
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}.NS`
            + `?range=1d&interval=1d`;
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, {
      signal: ctl.signal,
      // Yahoo 401s requests with no User-Agent
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; sharecase/1.0)' },
    });
    if (!r.ok) return null;
    const j = await r.json();
    const meta = j?.chart?.result?.[0]?.meta;
    const px = meta?.regularMarketPrice;
    // Reject anything that is not a positive number, and anything not priced in rupees — a wrong
    // currency silently mixed into a basket is worse than a missing price.
    if (typeof px !== 'number' || !(px > 0) || meta?.currency !== 'INR') return null;
    return Math.round(px * 100) / 100;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export default async function handler(req, res) {
  const origin = req.headers.origin;
  if (origin && ALLOWED.includes(origin)) res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'GET only' });

  const raw = String(req.query.symbols || '').trim();
  if (!raw) return res.status(400).json({ error: 'pass ?symbols=A,B,C' });

  // Uppercase, dedupe, and keep only plausible NSE tradingsymbols. Series suffixes are real
  // instruments (MTARTECH-BE), so hyphens are allowed through.
  const symbols = [...new Set(
    raw.split(',').map(s => s.trim().toUpperCase()).filter(s => /^[A-Z0-9][A-Z0-9&.\-]{0,19}$/.test(s))
  )];
  if (!symbols.length) return res.status(400).json({ error: 'no valid symbols' });
  if (symbols.length > MAX_SYMBOLS) {
    return res.status(400).json({ error: `at most ${MAX_SYMBOLS} symbols per request`, got: symbols.length });
  }

  const results = await Promise.all(symbols.map(async s => [s, await yahooPrice(s)]));
  const prices = {}, missing = [];
  for (const [s, px] of results) { if (px === null) missing.push(s); else prices[s] = px; }

  // Short cache: prices move, but a page that refetches on every keystroke should not hit Yahoo each
  // time. 60s is well inside "current" for sizing a basket you are about to place by hand.
  res.setHeader('Cache-Control', 'public, max-age=60, s-maxage=60');
  return res.status(200).json({
    prices,
    missing,
    asof: new Date().toISOString(),
    source: 'query1.finance.yahoo.com/v8/finance/chart',
  });
}
