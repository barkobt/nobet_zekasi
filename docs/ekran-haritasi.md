# Ekran Haritası ve Veri Modeli

> Kaynak: Notion "🗺️ Ekran Haritası ve Veri Modeli" (son düzenleme 7 Eylül 2026).
> **Önemli:** Bu belge şema tamamlanmadan önce yazıldı. Tablo adları, yetkinlik
> sayıları veya kurallar `db/migrations` ile çelişirse **veritabanı doğrudur**;
> çelişkiyi raporla, bu belgeye göre şemayı değiştirme.

Orquest (Inditex iş gücü planlama aracı) referans alındı, acil servis gerçekliğine
göre sadeleştirildi. Her ekranın altında onu besleyen tablolar listelidir.

---

## Katman 0 — Kurulum (bir kez yapılır)

### E-01 · Birim ve Vardiya Tanımları
Vardiya tipleri, saatleri, süreleri ve hedef mevcutlar. Çözücünün zaman eksenini belirler.
- Görünüm: basit liste + form
- Orquest karşılığı: Store configuration
- Tablolar: `units`, `shift_types`

### E-02 · Yetkinlik Matrisi
Personel × yetkinlik çapraz tablosu (Orquest Aptitudes ekranının karşılığı).
- Görünüm: satır = kişi, sütun = yetkinlik, hücre = var/yok
- **Kritik:** her sütunun altında toplam gösterilmeli ("triyaj yetkini 4 kişi" görünürse fizibilite riski erken fark edilir)
- Tablolar: `competencies`, `staff_competencies`

### E-03 · Kural Seti (Regulations)
Kısıt kataloğunun çalışan hali. Her kural açılıp kapatılabilir, hard/soft seçilebilir, soft ise ağırlığı değiştirilebilir.
- Neden ayrı ekran: kısıtlar kodda değil veritabanında; "bu ay gece kuralını gevşetelim" dendiğinde deploy gerekmemeli
- Kaynağı "Yasal" olan kurallar gevşetilemez (UI'da kilitli gösterilmeli)
- Orquest karşılığı: Organizational Diagram › Regulations › Default constraints
- Tablolar: `constraints`, `constraint_params`

## Katman 1 — Kadro

### E-04 · Personel Listesi
Solda kişi listesi, sağda sekmeli detay (Orquest People ekranı iskeleti).

| Sekme | İçerik | Tablo |
|---|---|---|
| Künye | Ad, sicil, rol, birim | `staff` |
| Sözleşme | Aylık hedef saat, başlangıç/bitiş | `contracts` |
| Yetkinlikler | Yetkinlik işaretlemesi | `staff_competencies` |
| Müsaitlik | Sadece gündüz / sadece gece / tam; özel gün istekleri | `availability_rules` (+ ilişkili tablolar) |
| Devamsızlık | İzin, rapor, tarih aralığı | `absences` |
| Uyumsuzluk | Kişi çiftleri + ceza puanı | `staff_conflicts` |

### E-05 · İzin ve Talep Yönetimi — FAZ 2
Talep → onay akışı. Onaylı talep çözücüye hard, onaysız talep soft tercih olarak gider.
- Tablolar: `requests`

## Katman 2 — İhtiyacın Tanımlanması

### E-06 · İhtiyaç Şablonu
Bir haftanın vardiya başına kaç kişi ve hangi görev için kaç kişi gerektiğini tanımlar.

Örnek (gündüz):

| Görev | Kişi | Zorunlu yetkinlik |
|---|---|---|
| Genel mevcut | 6 | — |
| Sorumlu | 1 | — (rol şartı) |
| Shift yetkilisi / ekip lideri | 1 | — (rol şartı) |
| Triyaj | min 3 | TRIYAJ |
| Ambulans | 2 | AMBULANS |
| Gözlem | 2 | GOZLEM |

- Orquest karşılığı: Needs Templates
- Tablolar: `need_templates`, `need_template_rows`

### E-07 · Dönem Planlaması — FAZ 2
Hangi haftada hangi şablonun geçerli olduğu (bayram, yoğun sezon istisnaları).
- Tablolar: `need_periods`

## Katman 3 — Çözüm

### E-08 · Taslaklar
Her çözücü çalıştırması bir taslak üretir; taslaklar karşılaştırılır, biri yayınlanır.
- Metrikler: toplam fazla mesai, max–min saat farkı, ihlal edilen soft kısıt sayısı, çözüm süresi, çözüm durumu
- Tablolar: `schedule_drafts`, `solver_runs`

### E-09 · Nöbet Çizelgesi — ANA EKRAN
Satır = personel, sütun = gün, hücre = vardiya + görev (Orquest Assignments ızgarası).
- Hücre: vardiya kısaltması (G/N), görev rozetleri (triyaj, ambulans, gözlem…), izin/rapor durumu
- Sütun başlığı: o gün için `atanan / gereken` — eksik varsa kırmızı (Orquest `275/322` gösterimi gibi)
- Satır sonu: kişinin aylık toplamı ve 200 saate uzaklığı
- Gruplama: rol grubuna göre katlanabilir bölümler
- Manuel müdahale (sonraki faz): hücre değişince sistem hangi kuralın ihlal edildiğini anında söyler, engellemez
- Planlama ufku: çözüm aylık, gösterim haftalık (ay görünümü opsiyonel)
- Tablolar: `assignments`, `assignment_tasks`

### E-10 · Çözüm Teşhisi
Çözücü INFEASIBLE döndüğünde hangi kısıt kümesinin çeliştiğini anlatır.
- Örnek: "14–20 Eylül çözülemedi. C-011 (triyaj) ile C-016 (haftalık dinlenme) çatışıyor: triyaj yetkin 4 kişinin 2'si izinli."
- Tablolar: `solver_diagnostics`

## Katman 4 — Denetim — FAZ 2

### E-11 · Saat Bütçesi ve Fazla Mesai
Kişi başına aylık saat, 200 saat doluluk oranı, fazla mesai. Tablo: `monthly_hour_summary` (view)

### E-12 · Adalet Panosu
Kişi başına gece sayısı, hafta sonu sayısı, toplam saat dağılımı. Tablo: türetilmiş view

## Katman 5 — Ayarlar

### E-13 · Görünür Sayaçlar
Çizelge satır özetinde hangi sayaçların haftalık/aylık görüneceği. Tablo: `visible_counters`

### E-14 · Kurum
Excel çıktılarının başlığında birim adının önünde görünen kurum adı. Tek alan.
Tablo: `app_settings` (`org_name`).

Kurum adı **koda gömülemez**: hastanenin adının üründe geçmemesi yasal bir
gerekliliktir (29.09.2026) ve gömülü metin her değişiklikte yeni dağıtım demektir.
Boş bırakılırsa çıktı başlığında kurum satırı hiç yazılmaz.

---

## MVP Sınırı — 1 Ekim 2026 sunumu

**İçeride:** E-01, E-02, E-03, E-04, E-06, E-08, E-09, E-10
**Dışarıda (faz 2):** E-05, E-07, E-11, E-12

Sunumda kanıtlanacak tek şey: **"Kuralları veriyoruz, sistem çalışan bir çizelge üretiyor."**
E-01 ve E-06 demo için salt okunur olabilir.

## Karara bağlananlar
- Planlama ufku: çözüm aylık, gösterim haftalık.
- Ay geçişi: her koşu önceki ayın son 3 gününü `assignments`'tan değiştirilemez başlangıç bağlamı olarak okur.
- Çoklu görev: bir kişi aynı vardiyada birden fazla görev taşıyabilir (`assignments` ≠ `assignment_tasks`).

## Açık tasarım soruları
- E-09'da elle değişiklik: sadece uyarı mı, yeniden çözüm mü, engelleme mi? (Demo için: sadece uyarı veya salt okunur.)
- O-001 / O-002 ağırlık kalibrasyonu.
