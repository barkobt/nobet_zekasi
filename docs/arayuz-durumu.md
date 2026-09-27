# Arayüz Durumu

Son güncelleme: 27 Eylül 2026 · Demo: 1 Ekim 2026

## Canlı adresler

| Katman | Adres |
|---|---|
| Arayüz (Vercel) | https://acibadem-smart-planner.vercel.app |
| API (Railway) | https://nobet-zekasi-api-production.up.railway.app |
| Sağlık kontrolü | `…/api/health` → `sema_guncel` alanı uygulanmamış migration'ı adıyla söyler |

Giriş tek ortak şifreyle; şifre yalnız Vercel ortam değişkeninde (`DEMO_PASSWORD`)
ve yerelde `web/.env.local` içinde durur. Hiçbir dosyaya, loga veya commit'e yazılmaz.

## Biten ekranlar

| Kod | Ekran | Yol | Not |
|---|---|---|---|
| E-00 | Ana Sayfa | `/` | Durum kartları |
| E-09 | Nöbet Çizelgesi | `/cizelge` | Izgara, hücre düzenleme, gün başlığı tooltip'i, Excel çıktısı |
| E-08 | Taslaklar | `/taslaklar` · `/taslaklar/[id]` | Oluştur · çöz · kopyala · uygula (arşivleyerek) · sil |
| E-06 | İhtiyaç | `/ihtiyac` | Şablon satırları, kapsama |
| E-11 | Raporlar | `/raporlar` | Kişi özeti + Eksikler; bölüm başına Excel ve PDF |
| E-04 | Personel | `/personel` | Künye, sözleşme, yetkinlik, müsaitlik, devamsızlık, uyumsuzluk; pasife alma ve silme |
| E-02 | Yetkinlik Matrisi | `/yetkinlik` | Düzenle kipi, rol grupları |
| E-03 | Kural Seti | `/kurallar` | Hard/soft ve ağırlık; `source='yasal'` kilitli |
| E-01 | Vardiya Tanımları | `/vardiyalar` | Salt okunur |

## Çıktılar

| Dosya | Uç nokta | Biçim |
|---|---|---|
| Çizelge | `/drafts/{id}/export.xlsx` | Tek sayfa · A3 yatay · genişlikte 1 sayfa · A sütunu ve başlık her sayfada · altbilgide sayfa no |
| Kişi özeti | `/drafts/{id}/export-ozet.xlsx` | Tek sayfa, dikey |
| Eksikler | `/drafts/{id}/export-eksikler.xlsx` | Tek sayfa, dikey |

PDF ayrı bir kütüphaneyle üretilmiyor: Raporlar ekranındaki "PDF" düğmesi
tarayıcının yazdırma penceresini açar, `@media print` kuralı sol menüyü, üst barı
ve düğmeleri gizler. Aynı hesabı ikinci kez yazmamak için bilinçli tercih.

## Hedef saat

Orantılı hesap **yok**. Tam takvim ayı → C-004 aylık asgari (200 sa), tam 7 gün →
C-003 haftalık referans (50 sa), başka uzunlukta hedef gösterilmez ("—").
İki sayı da `constraint_params`'tan okunur, kodda gömülü değil (`api/app/hedef.py`).

## Bilinen açık eksikler

- **Taslak adı arayüzden değiştirilemiyor.** API'de `PATCH /drafts/{id}` var,
  ekranda karşılığı yok. Ad ancak kopyalarken veya oluştururken giriliyor.
- **`availability_rules` boş.** Personel panelindeki müsaitlik sekmesi canlıda boş
  liste gösteriyor; veri girilmemiş durumda.
- **Referans haftada triyaj rozeti yok** (C4 kararı): kağıt çizelgede triyaj görevi
  kayıtlı olmadığı için o dönemde `TRIYAJ 0/3` görünür. Beklenen davranış.
- **Bilinen 1 uygunluk ihlali** (`v_task_eligibility_violations`): Güven Göl,
  26 Eyl 2026, ambulans. Kağıttaki gerçek; seed'e dokunulmadı.
- **Solver henüz stub.** `SOLVER_IMPL=stub` referans haftayı kopyalar; gerçek
  CP-SAT modeli (`api/solver/model.py`) gelince Railway'de `SOLVER_IMPL=cpsat`.
- **Mobil hedef değil** (DESIGN §8): 1440px ve 1280px'te test ediliyor.

## Ekran görüntüleri

`docs/screenshots/live/` altına `pnpm live-check` ile alınır. Klasör `.gitignore`'da:
gerçek personel adları içeriyor.
