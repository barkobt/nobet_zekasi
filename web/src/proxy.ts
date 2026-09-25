import { NextRequest, NextResponse } from "next/server";

/**
 * Demo erişimi: tek ortak şifre → HttpOnly imzalı çerez.
 *
 * Next.js 16'da bu dosya `proxy.ts` adını taşır (eski adı `middleware.ts`).
 * src/app/api/[...path]/route.ts'teki API proxy'siyle karıştırılmamalı: bu dosya
 * erişimi denetler, o dosya isteği Railway'e iletir.
 * Şifre sunucuda kalır; tarayıcıya yalnızca imza gider.
 * DEMO_PASSWORD boşsa koruma kapalıdır (yerel geliştirme).
 */
const COOKIE = "asp_demo";

async function imza(parola: string): Promise<string> {
  const veri = new TextEncoder().encode(`acibadem-smart-planner:${parola}`);
  const ozet = await crypto.subtle.digest("SHA-256", veri);
  return Array.from(new Uint8Array(ozet))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export default async function proxy(req: NextRequest) {
  const parola = process.env.DEMO_PASSWORD;
  if (!parola) return NextResponse.next();

  const beklenen = await imza(parola);
  if (req.cookies.get(COOKIE)?.value === beklenen) return NextResponse.next();

  const giris = new URL("/giris", req.url);
  giris.searchParams.set("devam", req.nextUrl.pathname);
  return NextResponse.redirect(giris);
}

export const config = {
  // /giris, statik dosyalar ve marka varlıkları korumanın dışında.
  matcher: ["/((?!giris|_next/static|_next/image|brand|favicon.ico).*)"],
};
