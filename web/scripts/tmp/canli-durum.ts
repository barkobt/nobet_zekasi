import { readFileSync } from "node:fs";
import { chromium } from "playwright";
const BASE = "https://acibadem-smart-planner.vercel.app";
const P = "DEMO_PASSWORD=";
const sifre = () => readFileSync("/Users/barko/Desktop/nobet_zekasi.nosync/web/.env.local", "utf8")
  .split("\n").find((s) => s.startsWith(P))!.slice(P.length).trim();

async function main() {
  const t = await chromium.launch();
  const ctx = await t.newContext({ viewport: { width: 1440, height: 900 } });
  const s = await ctx.newPage();
  await s.goto(`${BASE}/giris`);
  await s.locator('input[type="password"]').fill(sifre());
  await s.locator('button[type="submit"]').click();
  await s.waitForURL((u) => !u.pathname.startsWith("/giris"), { timeout: 30000 });

  const d: any[] = await s.evaluate(async () => {
    const r = await fetch("/api/drafts", { cache: "no-store" });
    return r.json();
  });
  for (const x of d) {
    console.log(`  ${String(x.id).padStart(3)} ${x.name.slice(0, 34).padEnd(34)} ${x.status.padEnd(11)} ` +
      `${x.period_start}→${x.period_end} atama=${String(x.assignment_count).padStart(4)} adalet=${x.fairness_gap}`);
  }
  await t.close();
}
main();
