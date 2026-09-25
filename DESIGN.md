# Acıbadem Smart Planner — Tasarım Dili

> Bu belge arayüzün TEK tasarım kaynağıdır. `docs/mockups/` altındaki HTML taslakları
> yalnızca **düzen (layout) referansıdır**: renk, yazı tipi, ikon seti ve içerikleri
> oradan ALINMAZ. Bu belge ile bir taslak çelişirse bu belge geçerlidir.

## 1. İlke: az laf, çok iş

Bu bir **operasyon aracı**, pazarlama sayfası değil. Sorumlu hemşire ekrana bakıp
3 saniyede "eksik var mı, kim nerede, kural bozuldu mu" cevabını almalı.

- Her ekranın **tek bir ana sorusu** vardır (bkz. §6). O soruya hizmet etmeyen kart eklenmez.
- **Renk bilgi taşır, süs değildir.** Nötr zemin + tek marka rengi + yalnızca durum bildiren renkler.
- Gradient, gölge yığını, emoji, "AI" rozeti, animasyonlu nabız noktası **yok**.
- Metin kısa: buton 1–2 kelime, kart başlığı en fazla 4 kelime, açıklama cümlesi yok.
- Yoğunluk tercih edilir (Orquest gibi), ama nefes alan boşluklarla: 8px ızgara.
- Lüks hissi süslemeden değil, **tutarlılıktan** gelir: aynı radius, aynı çizgi, aynı hizalama her yerde.

## 2. Renk token'ları

CSS değişkeni olarak `web/src/app/globals.css` içinde tanımlanır, shadcn/ui temasına bağlanır.
Bileşenlerde **hex kodu yazılmaz**, yalnızca token kullanılır.

> `--brand` logo zemininden ölçüldü (#1D265F). Kurumsal kimlik kılavuzundaki resmi değer
> (acibadem.com.tr › Kurumsal Bilgiler › Kurumsal Kimlik) farklıysa yalnızca bu token güncellenir.

| Token | Değer | Kullanım |
|---|---|---|
| `--brand` | `#1D265F` (Acıbadem logo laciverti) | Sol menü + logo bloğu zemini, birincil buton, aktif sekme çizgisi |
| `--brand-hover` | `#28337A` | Birincil buton hover, menü öğesi hover zemini |
| `--brand-soft` | `#EDEEF6` | Aktif satır / seçili hücre zemini |
| `--accent` | `#1C7ED6` | Link, odak halkası, bugün vurgusu. Başka hiçbir şey |
| `--bg` | `#F5F7FA` | Sayfa zemini |
| `--surface` | `#FFFFFF` | Kart / tablo zemini |
| `--border` | `#E3E8EF` | Tüm ayırıcı çizgiler (1px) |
| `--text` | `#0F1B2D` | Ana metin |
| `--text-muted` | `#5B6B7F` | Etiket, yardımcı metin |
| `--ok` | `#1E8E5A` | Kapsama tam, kural sağlandı |
| `--warn` | `#C77700` | Soft kural ihlali, sınırda |
| `--danger` | `#C62828` | Eksik kadro, hard kural ihlali, INFEASIBLE |
| `--ok-soft` / `--warn-soft` / `--danger-soft` | ilgili rengin %8 opaklığı | Rozet ve hücre zemini |

**Oran kuralı:** ekranın ~%85'i nötr, ~%10 marka, ~%5 durum rengi. Durum renkleri yalnızca
gerçekten bir durum bildiriyorsa kullanılır. "Tam kadro" satırları yeşile boyanmaz;
yalnızca **eksik** olan kırmızı görünür (sessiz başarı, gürültülü sorun).

Vardiya renkleri (tek yerde tanımlı, tüm ekranlarda aynı):
- **Gündüz (G)**: açık zemin `--surface` + `--brand` metin
- **Gece (N)**: `--brand` zemin + beyaz metin
- **İzin / rapor**: `--bg` zemin + `--text-muted` metin, desen yok

## 3. Tipografi

- Yazı tipi: **Inter** (tek aile). Sayılar için `font-variant-numeric: tabular-nums` zorunlu.
- Ölçek: 12 / 13 / 14 / 16 / 20 / 28 px. Başka boyut yok.
- Ağırlık: 400 metin, 500 etiket, 600 başlık ve vurgulu sayı. 700+ yok.
- BÜYÜK HARF yalnızca 11–12px bölüm etiketlerinde (letter-spacing 0.04em). Başlıklarda yok.
- Monospace font yok. Sayısal hizalama tabular-nums ile sağlanır.

## 4. Kabuk (tüm ekranlarda sabit)

- **Sol menü (`--brand` zemin, tam yükseklik):** genişken 224px (ikon + etiket), daraltılınca 64px
  (yalnız ikon, tooltip). En üstte 56px yüksekliğinde **logo bloğu** (§4.1). Aktif öğe: beyaz metin +
  sol 3px `--accent` çizgi. Menü öğeleri = MVP ekranları (§6).
- **Üst bar (56px, `--surface`, alt çizgi):** sol menünün sağından başlar. Solda sayfa adı / birim seçici
  ("Erişkin Acil Servis"), sağda dönem gezgini (‹ Ekim 2026 ›), bildirim, kullanıcı rolü.
  Logo üst barda **değil**, sol menünün tepesindedir: lacivert sütun kesintisiz yukarı çıkar.

### 4.1 Logo bloğu

Kaynak dosyalar `docs/brand/` altındadır (tek doğruluk kaynağı). `web/` iskeleti kurulunca
ikisi de **`web/public/brand/` altına kopyalanır** ve arayüz yalnızca oradan (`/brand/...`) okur.
Dosyalar Acıbadem SVG'sinden geometrisi korunarak ayrıldı: **yeniden çizilmez, renk/oran değiştirilmez,
yerine başka logo (taslaklardaki görseller, "A" kutusu) konmaz.**
- `acibadem-mark.svg`: "Λ" işareti, beyaz, şeffaf zemin, kare (viewBox 90×90)
- `acibadem-wordmark.svg`: "ACIBADEM" yazısı, beyaz, şeffaf zemin (viewBox 636.65×76.43)

Bileşen: `web/src/components/shell/BrandLogo.tsx` (tek yerde; başka hiçbir yerde logo kullanılmaz).

| Durum | Görünüm |
|---|---|
| Menü genişken, normal | İşaret (24px) + yanında "Smart Planner" (14px/600, beyaz) |
| Menü genişken, hover / odak | İşaret ve "Smart Planner" solar, yerine ACIBADEM yazısı (14px yükseklik) belirir |
| Menü daraltılmışken | Yalnız işaret (24px), ortalı. Hover dönüşümü yok, tooltip: "Acıbadem Smart Planner" |

- Geçiş: iki katman üst üste (`position: absolute`), yalnız `opacity` + 4px `translateX`,
  **200ms ease-out**. Genişlik değişmez (layout kayması olmaz). CSS ile yapılır, animasyon kütüphanesi yok.
- `prefers-reduced-motion: reduce` → geçiş anlık (süre 0).
- Logo bloğu bir link: tıklanınca E-09'a gider. `aria-label="Acıbadem Smart Planner — Nöbet Çizelgesi"`.
- Logo üzerine rozet, sürüm numarası, gölge veya parıltı eklenmez.
- **İçerik alanı:** `--bg` zemin, 24px iç boşluk, maksimum genişlik yok (ızgaralar tam genişlik kullanır).
- **Sayfa başlığı satırı:** solda başlık (20px/600), sağda en fazla 1 birincil + 2 ikincil buton.

## 5. Bileşen kuralları

- Radius: kart 8px, buton/input 6px, rozet 4px. Başka değer yok.
- Kart: `--surface` + 1px `--border`, gölge yok. Kart başlığı 14px/600, altında 1px çizgi.
- Butonlar: birincil (`--brand` dolgu), ikincil (çerçeveli), hayalet (sadece metin). Ekranda **tek** birincil buton.
- İkonlar: **lucide-react**, 16px (tablo/rozet) ve 20px (menü), stroke 1.75. Material Symbols / FontAwesome kullanılmaz.
- Tablolar: satır yüksekliği 40px, zebra yok, hover'da `--brand-soft`. Başlık 12px `--text-muted`, sticky.
- Rozet (görev / yetkinlik): 20px yükseklik, 12px metin, `--brand-soft` zemin. Görev rozetleri kısaltma kullanır:
  **TRY** (triyaj), **AMB** (ambulans), **GÖZ** (gözlem). Tam adı tooltip'te.
- KPI: büyük sayı (28px/600) + tek satır etiket. Açıklama, trend oku veya "geçen aya göre" metni yok
  (gerçek veri olmadıkça).
- Boş durum: tek cümle + tek eylem butonu.

## 6. Ekranlar ve tek soruları (MVP)

| Ekran | Ana soru | Düzen referansı |
|---|---|---|
| E-09 Nöbet Çizelgesi (**ana ekran**) | "Bu hafta/ay kim hangi vardiyada, eksik var mı?" | `mockups/05` ızgara iskeleti |
| E-08 Taslaklar | "Hangi taslak daha iyi?" | `mockups/02` sadeliği + metrik tablosu |
| E-10 Çözüm Teşhisi | "Neden çözülemedi, hangi kuralı gevşetmeliyim?" | yok, E-08 kart dilinde |
| E-04 Personel | "Bu kişinin sözleşmesi, yetkinliği, müsaitliği ne?" | `mockups/08` tablo + Orquest sol liste/sağ sekme |
| E-02 Yetkinlik Matrisi | "Her yetkinlikte kaç kişim var?" | Orquest Aptitudes, sütun altı toplamlarıyla |
| E-03 Kural Seti | "Hangi kural açık, hangisi gevşetilebilir?" | tablo; Yasal kurallar kilit ikonuyla |
| E-06 İhtiyaç Şablonu | "Vardiya başına kaç kişi/görev gerekiyor?" | `mockups/06` zaman çizelgesi, iki vardiyaya indirgenmiş |
| E-01 Vardiya Tanımları | "Vardiyalar ve saatleri neler?" | basit liste |

Ana sayfa (dashboard) MVP'de **yoktur**. Uygulama doğrudan E-09 ile açılır.
`mockups/01, 03, 04, 07` (dashboard ve hasta akışı projeksiyonu) kapsam dışıdır.

### E-09 detay
- Satır = personel (rol grubuna göre katlanabilir bölümler: Sorumlu & Eğitim, Ekip Liderleri, Hemşireler).
- Sütun = gün. Başlıkta gün adı + tarih + iki küçük sayaç: `G 6/6` ve `N 5/5` (**kişi** sayısı, saat değil).
  Eksikse sayaç `--danger`, tamsa `--text-muted`.
- Hücre: vardiya çipi (**G** veya **N**) + altında görev rozetleri (TRY/AMB/GÖZ). İzin/rapor gri metin.
  **Saat aralığı yazılmaz** (vardiyalar sabit: G 08:30–18:00, N 18:00–08:30).
- Satır sonu: aylık toplam saat ve 200 saat hedefine göre fark (`+12` / `−8`).
- Alt bar: toplam atanan saat, fazla mesai, adalet farkı (max–min), ihlal sayısı.

## 7. İçerik kuralları (kesin)

Taslaklardaki şu içerikler **gerçek değil**, arayüze girmez:
- "Orquest" adı hiçbir yerde geçmez (referans üründür, bizim ürünümüz değil).
- Kırmızı/Sarı/Yeşil alan, resüsitasyon, pediatri, eczane gibi **bizde olmayan birimler/görevler**.
- 3 vardiya (08–16 / 16–00 / 00–08) modeli. Bizde **2 vardiya** var.
- Hasta akışı tahmini, "AI projeksiyon güvenilirliği", yatak doluluğu, maliyet indeksi.
- "Sağlık Bakanlığı uyumlu", "4857 sayılı kanun", "akreditasyon uyumlu" gibi **doğrulanmamış uyum iddiaları**.
- 48 personel, sicil no, kıdem yılı gibi uydurma veriler. Tüm sayılar API'den gelir; gelmiyorsa gösterilmez.
- Sürüm rozetleri (v4.2), "Canlı sistem" nabız göstergeleri.
- Taslaklardaki `lh3.googleusercontent.com` logo görselleri ve "A" harfli kutu. Logo yalnızca §4.1'deki dosyalardır.

Terimler: *vardiya* (shift değil), *taslak*, *yetkinlik*, *ekip lideri*, *sorumlu hemşire*,
*eğitim hemşiresi*, *oryantasyon*. Arayüz dili Türkçe; tarih biçimi `21 Eyl 2026`, sayı `4.158`.

## 8. Erişilebilirlik ve kalite çıtası

- Metin kontrastı en az 4.5:1. Durum bilgisi yalnızca renkle verilmez (ikon veya metin eşlik eder).
- Klavye ile gezilebilir; odak halkası `--accent` 2px.
- 1440px ve 1280px genişlikte test edilir (demo laptop). Mobil hedef değil.
