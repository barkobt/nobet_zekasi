# HANDOFF — Clinorq geçişi + kural düzeltmeleri (29 Eylül 2026)

> Bu dosyayı repo köküne `docs/HANDOFF-clinorq.md` olarak koy. `/clear` sonrası Claude Code'a ilk mesaj:
> **"docs/HANDOFF-clinorq.md'yi oku ve sırayla uygula. Her bölüm sonunda dur, özet ver."**

## 0. Mevcut durum (önceki oturumdan)
- Canlı: Ekim 2026 yayında, adalet farkı 3,0 sa, eksik 0. SOLVER_WORKERS=8, SOLVER_NO_IMPROVEMENT_S=60.
- Açık iş: `seeds/028` Neon'a uygulanmadı (karşılaştırma rakamları canlıda doğru çıksın diye).
- "Kopyala → çöz" kaynağın kalitesini miras alır; kötü çizelgeden başlanıyorsa boş taslak açılır (docs/deploy.md).
- Deploy CLI ile: `railway up`, `vercel --prod` (git push deploy etmez).

---

## 1. Yeniden markalama: Acıbadem → **Clinorq** (YASAL ZORUNLULUK, 1 Ekim sunumundan önce)
Hastane; isim, logo, hiçbir marka öğesinin kullanılmamasını istedi (ceza riski).

**Kural:** Ürün/UI/kod/dokümanda "Acıbadem", "Smart Planner", "Nöbet Zekâsı" ürün adı olarak geçmeyecek. Ürün adı her yerde **Clinorq** (yazımda küçük harf wordmark: `clinorq`).

**Yapılacaklar**
1. `grep -rni "acıbadem\|acibadem\|smart planner\|nöbet zekâsı\|nobet zekasi"` → tam liste çıkar, önce listeyi göster.
2. Logo seti: zip'i `web/public/brand/` altına aç (klasörler: symbol, wordmark, stacked, horizontal, app-icon, favicon).
   - Sol panel/sidebar: açık zeminde `horizontal/clinorq-horizontal-color.svg`, daraltılmış panelde `symbol/clinorq-symbol-color.svg`; koyu zeminde `-reverse` varyantları.
   - Favicon: `favicon/favicon.svg` (+ Next.js `app/icon.svg`); apple-touch/manifest: `app-icon/clinorq-appicon-blue.svg`.
   - Giriş (şifre) ekranı: `stacked/clinorq-stacked-color.svg`.
3. `<title>`, metadata, tooltip/hover metinleri, boş durum metinleri, e-posta/Excel/PDF başlıkları ve dosya adları (ör. export dosya adı), footer.
4. Renk token'ları (DESIGN.md'ye işle): Lacivert `#0B1F3A`, Mavi `#1D7BEA` (koyu zeminde `#3A92F7`), Teal `#0F8A85` (koyu zeminde `#1FB0A7`), koyu zemin `#0B2447`. Font: Sora (logo); UI fontu DESIGN.md'deki gibi kalabilir.
5. Seed/DB'de görünen kurum adı: hastane adı UI'da görünmeyecek → kurum adını ayar tablosunda düzenlenebilir alan yap, varsayılan nötr bir değer ("Acil Servis" vb.). **(Baran'a sor: kurum adı alanı tamamen boş mu, nötr mü?)**
6. Altyapı adları (Baran CLI'da yapacak, Code komutları hazırlasın):
   - GitHub repo → `clinorq` (GitHub eski URL'yi yönlendirir; lokal `git remote set-url` güncelle)
   - Vercel proje/domain → `clinorq` (ör. clinorq.vercel.app) — **eski linki sunumdan önce ekiptekilerle yeniden paylaş**
   - Railway servis adı → `clinorq-api`; CORS/proxy'deki URL'leri güncelle
   - DB adı `nobet_app` iç isim; değiştirmek zorunlu değil, riskli (bağlantı dizeleri). Sunum sonrasına bırak.
7. `docs/` içindeki ekran görüntüleri (`docs/screenshots/live/canli-*.png`) eski adı içeriyorsa yenile.
8. Sunum dosyası (1 Ekim) — başlık "Acıbadem Smart Planner" idi → "Clinorq" yap, hastane logosu varsa kaldır.

**Kabul:** grep sonucu (git geçmişi hariç) sıfır; canlıda sekme ikonu, sol panel, giriş ekranı Clinorq.

---

## 2. Molalar mesaiye dahil DEĞİL → net saat hesabı (şema değişikliği)
**Bulgu:** Molaları mesaiden saydık. Brüt saatle 200 sa hedefi 3–4 günde doluyor → kalan günler boş kalıyor → 3 gün üst üste boşluklar bunun doğrudan sonucu.

**Kural (Edem):**
- Gündüz vardiyası mola: **1 sa 20 dk (80 dk)**
- Gece vardiyası mola: **3 sa 30 dk (210 dk)**
- Molanın ne zaman kullanıldığı bilinmiyor/önemsiz (günlük shift detayıyla ilgilenmiyoruz) → sadece süreden düşülür.

**Tasarım**
- Yeni migration: `shift_types.break_minutes INT NOT NULL DEFAULT 0` + UI'dan düzenlenebilir (hardcode yok ilkesi).
- `net_minutes = (bitiş − başlangıç) − break_minutes`. Tek bir SQL fonksiyonu/view'da tanımla (ör. `v_shift_types_net`), her yer oradan okusun.
- **Net kullanılacak yerler:** aylık 200 sa hedef, haftalık 50 sa referans, adalet farkı, personel özet/raporlar, Excel/PDF, solver amaç fonksiyonu.
- **Brüt kalacak yerler:** vardiya arası dinlenme / gece→gündüz (24 sa) kontrolü — mola dinlenme sayılmaz, saat aralığı gerçek zamandır.
- İzin/rapor kredisi **7,5 sa/gün NET** ✅ (Edem teyit etti, 29 Eylül).
- Aylık 200 sa hedef **NET** ✅ (teyitli). 50 sa haftalık referans da net saatle ölçülür.

**Sonra:** Ekim'i **boş taslaktan** yeniden çöz (kopyalama değil), saat farkı/eksik tablosunu yenile, karşılaştırma belgesini güncelle.

---

## 3. İzin (off) desenleri
**Kural (Edem):**
- **Sadece gündüz çalışanlar:** haftada **tam 1 off**, haftanın herhangi bir günü. 2 veya 3 değil.
- **Diğer herkes:** off'lar **1 veya 2 günlük bloklar** halinde.
- **3+ gün üst üste boşluk kullanılmıyor.** İstisna: yıllık izin, rapor, planlayıcının girdiği "kesin off" istekleri (bunlar bloğu uzatabilir).

**Tasarım (DB'den düzenlenebilir kural olarak, katalog kodu ile)**
- `C-xxx max_consecutive_off = 2` — ardışık izinsiz boş gün sayısı ≤ 2 (istek/izin günleri hariç sayılır). Katı yap; çözümsüzlük olursa gevşek + yüksek ceza.
- `C-xxx day_only_weekly_off = 1` — gündüz-only personelde haftalık izinsiz boş gün tam 1 (Merve Armut istisnası: kişisel isteğiyle gece çalışabilir, kural yine geçerli).
- Mevcut "haftada en az 1 off" + "tek gece sonrası off sayılır" kuralları korunur.
- Hafta sınırı: **takvim haftası, Pazartesi–Pazar** ✅ (teyitli; kayan 7 gün değil).
- Kontrolcüye (validator) ikisini de ekle; kağıt Eylül karşılaştırmasında yeni ihlal sayılarını ayrı raporla.

---

## 4. Sıra ve bitiş
1. Bölüm 1 (markalama) → deploy → canlıda kontrol.
2. Bölüm 2 migration + hesaplar → test.
3. Bölüm 3 kurallar → Ekim'i boş taslaktan çöz → canlıya al.
4. `seeds/028` + yeni migration'ları Neon'a uygula (komutları ver).
5. Ekran görüntülerini yenile, docs/deploy.md ve karşılaştırma belgesini güncelle.

## Edem'den teyitli cevaplar (29 Eylül)
1. 200 sa aylık hedef → **net** (molasız).
2. İzin/rapor günü kredisi → **7,5 sa net**.
3. Gündüz-only "haftada 1 off" → hafta **Pazartesi–Pazar**.

Açık kalan tek soru (Baran'a): kurum adı arayüzde tamamen boş mu, nötr bir ad mı?
