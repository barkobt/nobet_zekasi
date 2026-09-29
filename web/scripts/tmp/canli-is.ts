import { readFileSync } from "node:fs";
import { chromium, type Page } from "playwright";
const BASE = "https://acibadem-smart-planner.vercel.app";
const P = "DEMO_PASSWORD=";
const sifre = () => readFileSync("/Users/barko/Desktop/nobet_zekasi.nosync/web/.env.local", "utf8")
  .split("\n").find((s) => s.startsWith(P))!.slice(P.length).trim();

const cagir = (s: Page, yol: string, init?: RequestInit) =>
  s.evaluate(async ([y, i]: [string, RequestInit | undefined]) => {
    const r = await fetch("/api" + y, { ...i, cache: "no-store" });
    const g = await r.text();
    return { durum: r.status, govde: g ? JSON.parse(g) : null };
  }, [yol, init] as [string, RequestInit | undefined]);

async function coz(s: Page, id: number, ad: string) {
  const b = await cagir(s, `/drafts/${id}/solve`, {
    method: "POST", headers: { "content-type": "application/json" }, body: "{}",
  });
  if (b.durum !== 202 && b.durum !== 200) {
    console.log(`  ✗ ${ad}: çöz başlatılamadı ${b.durum} ${JSON.stringify(b.govde).slice(0,120)}`);
    return null;
  }
  const runId = b.govde.run_id;
  for (let i = 0; i < 90; i++) {
    await s.waitForTimeout(2000);
    const k = await cagir(s, `/solver-runs/${runId}`);
    if (k.govde?.status !== "CALISIYOR") {
      console.log(`  ✓ ${ad}: ${k.govde.status} · atama=${k.govde.assignment_count} ` +
        `· teşhis=${k.govde.diagnostic_count} · ${k.govde.elapsed_s?.toFixed?.(1)}s`);
      return k.govde;
    }
  }
  console.log(`  ✗ ${ad}: zaman aşımı`);
  return null;
}

async function adalet(s: Page, id: number, bas: string, son: string) {
  const c = await cagir(s, `/drafts/${id}/schedule?from=${bas}&to=${son}`);
  const satir = c.govde.groups.flatMap((g: any) => g.rows).filter((r: any) => r.in_fairness);
  const saat = satir.map((r: any) => r.counters.S).sort((a: number, b: number) => a - b);
  return { fark: +(saat[saat.length - 1] - saat[0]).toFixed(1), havuz: satir.length,
           eksik: c.govde.summary.shortfall_count };
}

async function main() {
  const t = await chromium.launch();
  const ctx = await t.newContext({ viewport: { width: 1440, height: 900 } });
  const s = await ctx.newPage();
  await s.goto(`${BASE}/giris`);
  await s.locator('input[type="password"]').fill(sifre());
  await s.locator('button[type="submit"]').click();
  await s.waitForURL((u) => !u.pathname.startsWith("/giris"), { timeout: 30000 });

  // 1) Yayındaki Ekim'i (4) kopyala
  const k = await cagir(s, "/drafts/4/copy", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ name: "Ekim 2026" }),
  });
  console.log(`  kopya: ${k.durum} id=${k.govde?.id} ad=${k.govde?.name}`);
  const yeni = k.govde.id;

  // 2) İpuçlu çöz, 3 saat farkı tutturana kadar en fazla 3 deneme
  for (let deneme = 1; deneme <= 3; deneme++) {
    await coz(s, yeni, `Ekim kopya (deneme ${deneme})`);
    const a = await adalet(s, yeni, "2026-10-01", "2026-10-31");
    console.log(`     → saat farkı ${a.fark} sa · havuz ${a.havuz} · eksik slot ${a.eksik}`);
    if (a.fark <= 3.0 && a.eksik === 0) { console.log("     kabul"); break; }
  }
  console.log("TASLAK_ID=" + yeni);
  await t.close();
}
main();
