import { readFileSync } from "node:fs";
import { chromium, type Page } from "playwright";
const BASE = "https://acibadem-smart-planner.vercel.app";
const P = "DEMO_PASSWORD=";
const sifre = () => readFileSync("/Users/barko/Desktop/nobet_zekasi.nosync/web/.env.local", "utf8")
  .split("\n").find((s) => s.startsWith(P))!.slice(P.length).trim();
const cagir = (s: Page, y: string) =>
  s.evaluate(async (yol: string) => (await fetch("/api" + yol, { cache: "no-store" })).json(), y);

async function main() {
  const t = await chromium.launch();
  const ctx = await t.newContext();
  const s = await ctx.newPage();
  await s.goto(`${BASE}/giris`);
  await s.locator('input[type="password"]').fill(sifre());
  await s.locator('button[type="submit"]').click();
  await s.waitForURL((u) => !u.pathname.startsWith("/giris"), { timeout: 30000 });

  const d = await cagir(s, "/drafts/10");
  console.log("  son koşu:", JSON.stringify(d.last_run));
  const kural = await cagir(s, "/constraints");
  const onemli = kural.filter((k: any) =>
    ["O-002", "O-003", "C-004", "monthly_min_hours"].includes(k.catalog_code ?? k.code));
  for (const k of onemli)
    console.log(`  ${k.code} ${k.catalog_code ?? ""} hard=${k.is_hard} ağırlık=${k.default_weight}`);
  const p = await cagir(s, "/people?durum=hepsi");
  console.log("  personel:", p.length, "· aktif:", p.filter((x: any) => x.is_active).length);
  await t.close();
}
main();
