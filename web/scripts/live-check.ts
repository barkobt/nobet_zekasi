/**
 * Canlı doğrulama: dağıtılmış siteye girer ve verilen sayfaların 1440px
 * ekran görüntüsünü alır.
 *
 *   pnpm live-check                      → varsayılan sayfa listesi
 *   pnpm live-check /personel /kurallar  → yalnız verilenler
 *   BASE_URL=... pnpm live-check         → başka bir dağıtım
 *
 * ŞİFRE: web/.env.local içindeki DEMO_PASSWORD'dan okunur. Hiçbir yere
 * yazılmaz, loglanmaz, ekran görüntüsüne girmez (giriş sayfası çekilmez).
 * Görüntüler docs/screenshots/live/ altına kaydedilir; o klasör .gitignore'da
 * çünkü gerçek personel adları içeriyor.
 */
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const BURASI = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(BURASI, "..");
const KOK = resolve(WEB, "..");
const CIKTI = join(KOK, "docs", "screenshots", "live");

const BASE_URL = process.env.BASE_URL ?? "https://acibadem-smart-planner.vercel.app";
const GENISLIK = 1440;
const YUKSEKLIK = 900;

const VARSAYILAN_SAYFALAR = [
  "/",
  "/cizelge",
  "/taslaklar",
  "/personel",
  "/yetkinlik",
  "/kurallar",
  "/ihtiyac",
  "/vardiyalar",
];

/**
 * .env.local'ı elle oku: script Next çalışma zamanının dışında koşuyor.
 * LIVE_DEMO_PASSWORD verilmişse o kazanır — canlıdaki şifre yereldekinden
 * farklı olabilir ve yerel geliştirme şifresini değiştirmek gerekmesin.
 */
function sifreyiOku(): string {
  if (process.env.LIVE_DEMO_PASSWORD) return process.env.LIVE_DEMO_PASSWORD;
  const yol = join(WEB, ".env.local");
  if (!existsSync(yol)) {
    throw new Error("web/.env.local bulunamadı. DEMO_PASSWORD oradan okunuyor.");
  }
  for (const satir of readFileSync(yol, "utf8").split("\n")) {
    const [ad, ...kalan] = satir.split("=");
    if (ad?.trim() === "DEMO_PASSWORD") {
      const deger = kalan.join("=").trim();
      if (deger) return deger;
    }
  }
  throw new Error("web/.env.local içinde DEMO_PASSWORD boş.");
}

/** Sayfa yolunu dosya adına çevirir: "/" → "ana-sayfa", "/taslaklar/2" → "taslaklar-2" */
const dosyaAdi = (yol: string) =>
  yol === "/" ? "ana-sayfa" : yol.replace(/^\//, "").replace(/\//g, "-");

async function main() {
  const sayfalar = process.argv.slice(2);
  const hedefler = sayfalar.length > 0 ? sayfalar : VARSAYILAN_SAYFALAR;
  const sifre = sifreyiOku();

  mkdirSync(CIKTI, { recursive: true });

  const tarayici = await chromium.launch();
  const baglam = await tarayici.newContext({
    viewport: { width: GENISLIK, height: YUKSEKLIK },
    deviceScaleFactor: 1,
    locale: "tr-TR",
  });
  const sayfa = await baglam.newPage();

  // Giriş. Şifre yalnız burada kullanılır; ekran görüntüsü alınmaz.
  await sayfa.goto(`${BASE_URL}/giris`, { waitUntil: "domcontentloaded" });
  await sayfa.fill("#parola", sifre);
  await Promise.all([
    sayfa.waitForURL((u) => !u.pathname.startsWith("/giris"), { timeout: 20_000 }),
    sayfa.click('button[type="submit"]'),
  ]);
  console.log(`giriş tamam → ${BASE_URL}`);

  let hata = 0;
  for (const yol of hedefler) {
    const url = `${BASE_URL}${yol}`;
    try {
      const yanit = await sayfa.goto(url, { waitUntil: "networkidle", timeout: 30_000 });
      const durum = yanit?.status() ?? 0;

      // Veri gelene kadar bekle: "Yükleniyor…" kalırsa görüntü boş çıkar
      await sayfa
        .waitForFunction(() => !document.body.innerText.includes("Yükleniyor…"), { timeout: 15_000 })
        .catch(() => { /* bazı sayfalar bu metni hiç göstermiyor */ });

      const dosya = join(CIKTI, `${dosyaAdi(yol)}.png`);
      await sayfa.screenshot({ path: dosya });

      const hataVar = await sayfa.getByText(/alınamadı|Bir hata/i).count();
      const isaret = durum === 200 && hataVar === 0 ? "✓" : "✗";
      if (isaret === "✗") hata++;
      console.log(`  ${isaret} ${yol.padEnd(14)} ${durum}  → ${dosya.replace(KOK + "/", "")}`);
    } catch (e) {
      hata++;
      console.log(`  ✗ ${yol.padEnd(14)} ${(e as Error).message.split("\n")[0]}`);
    }
  }

  await tarayici.close();
  console.log(hata === 0 ? "\nHepsi geçti." : `\n${hata} sayfada sorun var.`);
  process.exit(hata === 0 ? 0 : 1);
}

main().catch((e) => {
  // Hata metninde şifre geçmez: yalnız kendi mesajlarımızı basıyoruz.
  console.error((e as Error).message);
  process.exit(1);
});
