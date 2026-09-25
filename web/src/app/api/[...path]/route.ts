import { NextRequest } from "next/server";

/**
 * API proxy. Tarayıcı yalnızca aynı origin'deki /api/... adresini görür.
 *
 * İki işe yarıyor:
 *  1) DEMO_API_TOKEN ve Railway adresi sunucuda kalır, istemci paketine hiç girmez.
 *  2) İstekler aynı origin'den gittiği için Railway tarafında CORS ayarı gerekmez.
 */
const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

async function proxy(req: NextRequest, path: string[]) {
  const url = new URL(`/api/${path.join("/")}`, API_BASE);
  url.search = req.nextUrl.search;

  const headers = new Headers();
  const ct = req.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  if (process.env.DEMO_API_TOKEN) headers.set("x-demo-token", process.env.DEMO_API_TOKEN);

  const res = await fetch(url, {
    method: req.method,
    headers,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.text(),
    cache: "no-store",
  });

  return new Response(res.body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
