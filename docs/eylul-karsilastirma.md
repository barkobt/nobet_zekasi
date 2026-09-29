# Eylül 2026 — kağıt çizelge ile sistem çizelgesi

Aynı kadro, aynı izinler, aynı dönem (31 Ağustos – 29 Eylül 2026).
Tek fark: biri elle hazırlandı, diğerini çözücü kurdu.

Kağıt çizelge `docs/kagit-cizelge/` altındaki fotoğraflardan birebir aktarıldı
(387 atama, 441 görev rozeti). Sistem çizelgesi **sıfırdan** çözüldü: kağıttan
kopyalama yok, başlangıç ipucu verilmedi.

---

## 1. Özet

| Ölçü | Kağıt | Sistem |
|---|---:|---:|
| Kural ihlali (katı) | **22** | **0** |
| Ambulans mevcudu eksik olan vardiya | **18** | **0** |
| Gözlem mevcudu eksik olan vardiya | **21** | **0** |
| Triyaj mevcudu eksik olan vardiya | **4** | **0** |
| Ambulans çıkınca alan boş kalan vardiya | **1** | **0** |
| Saat farkı (en çok − en az) | **70,0 sa** | **31,5 sa** |
| Gece farkı | **14** | **12** |
| Geçersiz acil takviye | 5 | 0 |

> **29.09.2026 — bu tablodaki sayılar 28.09 kural setine aittir.** O tarihten sonra
> molalar mesaiden çıktı (net saat, `migration 023`) ve iki yeni izin kuralı eklendi
> (C-023, C-024 + kişiye özel desenler, `migration 024`). Yeni kural setiyle ölçüm
> §7'de; aşağıdaki tablo kayıt olarak duruyor, **güncellenmedi**.

Bütün sayılar kontrolcünün (`uv run python -m solver.validate`) çıktısından;
iki çizelge aynı kurallarla, aynı programla ölçüldü. Ham `v_daily_coverage`
görünümü kullanılmadı: o görünüm "kağıtta görev belirtilmemiş" durumunu
bilmiyor ve kağıdı olduğundan kötü gösteriyor (bkz. §5.6).

Saat ve gece farkının gerçek okunuşu için §4'e bakın: sistemdeki 31,5 saatlik
fark **dağıtım adaletsizliği değil**, izin ve çalışma tipi farkıdır.

---

## 2. Kural ihlalleri

Kontrolcü (`uv run python -m solver.validate`) ikisini de aynı kurallarla ölçtü.

### Kağıtta bulunan 22 katı ihlal

| Kural | Sayı | Örnek |
|---|---:|---|
| C-017 çalışma tipi | 6 | Merve Armut 5 kez gece çalışmış (kayıtta sadece gündüz) |
| C-002 en fazla 2 gece üst üste | 3 | Muhammet Edem 19–21 Eylül 3 gece |
| C-014 2 gece sonrası boş gün | 3 | Muhammet Edem 21 Eylül |
| C-021 gece sonrası gündüz | 4 | Fatih Sırcan 22 Eylül |
| C-009 ambulans sonrası alan | 1 | 21 Eylül gecesi gözlemde kimse kalmamış |
| C-022 geçersiz takviye | 5 | Güven Göl 26 Eylül (ekip zaten 6/5, üstelik ambulansa çıkmış) |

C-022 satırlarının 7'sinden 2'si **meşru takviye** sayıldı (Ayşe Kartal 27-28 Eylül:
eşi yokken ekip 4/5'ti, eklenince 5/5 oldu) — onlar uyarı, ihlal değil.

Bunların yanında **57 gevşetilebilir slot eksiği** var (kadro yetmemiş).

### Yetkinlik kaydıyla uyuşmayan rozetler (12 uyarı, ihlal değil)

Kağıtta işaretli olup da kişinin kayıtlı yetkinliğinde bulunmayan rozetler.
Elle yazıldığı için **uyarı** sayılıyor, hata değil:

| Kişi | Rozet | Kaç gün |
|---|---|---:|
| Muhammet Edem | AMBULANS | 10 |
| Zehra Kutucu | AMBULANS | 1 |
| Güven Göl | AMBULANS | 1 |

Üçü de kağıtta **pembe ile işaretli**, yani gerçekten ambulansa çıkmışlar.
Muhammet ve Zehra'nın ambulans yetkisi **hastaneye soruldu**; cevap gelene
kadar yetkinlik kayıtlarına dokunulmuyor. Yetki varsa bu 11 uyarı düşecek ve
geriye yalnız Güven Göl'ün bilinen istisnası kalacak.

### Sistemde bulunan ihlal

Yok. Her çözümün sonunda kontrolcü kendiliğinden koşuyor; katı ihlal bulursa
çözüm teşhisinin (E-10) en üstüne kırmızı satır yazıyor. Bu çizelgede yazmadı.

---

## 3. Kadro eksikleri

Sayılar kontrolcüden: bir vardiyanın bir slotu gerekenin altındaysa bir satır.

| Slot | Gereken | Kağıt: kaç vardiyada eksik | Sistem |
|---|---|---:|---:|
| Ambulans | 2 kişi | **18** | 0 |
| Gözlem | en az 2 | **21** | 0 |
| Triyaj | en az 3 | **4** | 0 |
| Genel mevcut | 5 kişi | 1 | 0 |
| Ekip lideri | en az 1 | 0 | 0 |
| Sayım yetkilisi | en az 1 | 0 | 0 |

Sistem çizelgesinde kadro eksiği **sıfır**: aynı 20 kişiyle, aynı izinlerle,
her vardiyanın her slotu dolduruldu.

**Ambulans çıkınca alan boşalması** kağıtta 1 vardiyada oldu (21 Eylül gecesi,
gözlemde kimse kalmadı). Sistemde C-009 katı kural olduğu için 0.

> Triyaj ve gözlem sayıları **en fazla bu kadar** demektir. Kağıtta 56 satırda
> kişinin hangi alanda olduğu yazmıyor (§5.6); o kişiler alan sayımına
> girmiyor. Gerçek eksik bu sayılardan **az** olabilir, çok olamaz.

## 4. Saat ve gece dağılımı

### Kağıt

| Kişi | Saat | Gece |
|---|---:|---:|
| Muhammet Edem | 260,0 | 14 |
| Murat Sığınç | 254,5 | 11 |
| Havva Abravcı | 252,0 | 12 |
| Mediha Aydoğan | 250,5 | 14 |
| Eda Karakuş | 240,0 | 10 |
| … | … | … |
| Zehra Kutucu | 197,0 | 9 |
| Engin Sümer | 191,5 | 6 |
| Sevda Koç | 190,0 | 0 |

En çok çalışan ile en az çalışan arasında **70 saat** fark var — yaklaşık
7 gündüz vardiyası. Gece farkı **14**: biri 14 gece nöbet tutmuş, biri hiç.

### Sistem

| Kişi | Saat | Gece |
|---|---:|---:|
| 13 kişi (gece çalışabilen, izinsiz) | **221,5** | **12** |
| Şükran Ünlü *(sadece gündüz)* | 218,5 | 0 |
| Merve Armut *(sadece gündüz)* | 218,5 | 0 |
| Sevda Koç *(sadece gündüz, 7 gün izinli)* | 190,0 | 0 |

**Gece çalışabilen ve ay boyu izinsiz 13 kişinin hepsi tam olarak aynı:
221,5 saat ve 12 gece. Aralarındaki fark 0.**

Toplam 31,5 saatlik fark şuradan geliyor:
- **Sevda Koç 190 saat** — 7 gün yıllık izinli. Hedefi izin günü başına 7,5 saat
  düşürüldüğü için 147,5 saate indi; 190 saat zaten hedefinin 42,5 saat üstünde.
- **Şükran ve Merve 218,5 saat** — yalnız gündüz çalışıyorlar. Gündüz vardiyası
  9,5 saat, gece 14,5 saat; gece tutamayan biri aynı sayıda vardiyayla daha az
  saat toplar. Bu bir dağıtım tercihi değil, vardiya sürelerinin sonucudur.

Aynı ayrım kağıtta da var ama orada **gece çalışabilenler arasında bile** fark
büyük: Muhammet Edem 260 saat / 14 gece, Engin Sümer 191,5 saat / 6 gece.

---

## 5. Sayım ilkeleri (hastane ile kararlaştırıldı)

Bu belgedeki bütün sayılar şu kurallarla hesaplandı:

1. **Eğitim günleri çalışılmış sayıldı.** Engin Sümer'in 10–11 Eylül'deki
   "EĞİTİM" yazan günleri gündüz vardiyası + triyaj olarak aktarıldı. Temkinli
   seçim: kağıdı olduğundan **iyi** gösterir, kötü değil.
2. **GECE_0100 tam gece sayıldı.** Kağıtta 7 kez geçen 18:00–01:00 (7 saat)
   vardiyası, gece mevcuduna tam kişi olarak yazıldı — oysa gece yarısından
   sonra sahada değiller. Yine temkinli: kağıdın kadro eksiği olduğundan
   **az** görünür. (Sistem bu vardiyayı hiç kullanmıyor, pasif.)
3. **Ayrılan ve ay içinde başlayan personel kapsamaya girer, adalete girmez.**
   Efe Mutlu (20 Eylül'de ayrıldı), Çağla Sarıtaş (6 Eylül'de ayrıldı),
   Serpil Demir (7 Eylül'de başladı), Ayşe Kartal (14 Eylül), Güven Göl
   (21 Eylül) o gün sahada çalıştıkları için **mevcuda sayılıyorlar**, ama ayın
   tamamını çalışmadıkları için **saat/gece adaleti ve 200 saat karşılaştırmasına
   girmiyorlar**. Adalet havuzu bu yüzden iki tarafta da 16 kişi.
4. **Sorumlu hemşire ve oryantasyondakiler adalet havuzunda değil.** Sorumlunun
   programı sabit, oryantasyondakiler eğitmenlerini gölgeliyor.
5. **Kağıtta belirtilmeyen görev, ihlal sayılmaz.** Kağıtta bir kişinin
   hangi alanda (triyaj / gözlem) olduğu her zaman yazmıyor — renk işareti yoksa
   bilmiyoruz. İlk aktarımda "renk yoksa triyaj" varsaymıştık; bu, TRIYAJ
   yetkinliği olmayan Eda Karakuş ve Derya Torun'a 8 gün triyaj rozeti yazdı ve
   kontrolcü bunları "yetkinliksiz rozet" diye işaretledi. İhlal kağıdın değil
   **bizim varsayımımızın** ürünüydü. O 8 rozet kaldırıldı (`seeds/028`), satırlar
   rozetsiz bırakıldı — GOZLEM'e çevrilmedi, o da başka bir varsayım olurdu.
   Kontrolcü artık kağıttan gelen ve alanı yazılmamış satırı ne "rozetsiz
   çalışan" (D-4) sayıyor ne de o vardiyada alanın boşaldığını iddia ediyor (D-9).
6. **İzin günü hedefi düşürür.** Aylık 200 saatlik hedef, izin/rapor günü başına
   7,5 saat iner (hastane onaylı). Hem çözücü hem ekran aynı hesabı yapıyor.

---

## 6. Ne kanıtlıyor

Aynı kadro ve aynı izinlerle:

- Kağıtta **22 kural ihlali** var, sistemde **hiç yok**.
- Kağıtta **18 vardiyada ambulans, 21 vardiyada gözlem, 4 vardiyada triyaj
  mevcudu eksik**; sistemde hiçbirinde.
- Kağıtta 1 kez **ambulans çıkınca alan boş kalmış** (21 Eylül gecesi),
  sistemde hiç.
- Gece çalışan 13 kişinin saati ve gece sayısı kağıtta **191,5–260 saat /
  6–14 gece** arasında dağılmış; sistemde **hepsi 221,5 saat ve 12 gece**.

Kağıdı hazırlayan sorumlu hemşire hatalı çalışmadı — bu kadar kuralı elle,
aynı anda tutmak mümkün değil. Sistemin yaptığı, aynı kuralları her hücrede
aynı anda kontrol edebilmek.

---

## 7. Yeni kural setiyle yeniden ölçüm (29.09.2026)

29.09'da iki şey değişti:

1. **Molalar mesaiye dahil değil** (`migration 023`): gündüz 80 dk, gece 210 dk
   düşülüyor. Net süreler gündüz 8 sa 10 dk, gece 11 sa. Aylık 200 saat hedefi,
   haftalık 50 saat referansı, adalet farkı ve raporlar net saatle ölçülüyor.
2. **İzin desenleri** (`migration 024`): C-023 (gündüzcü haftada tam 1 izin),
   C-024 (üst üste en fazla 2 izinsiz boş gün) ve kişiye özel haftalık desenler
   (sorumlunun sabit programı, eğitim hemşiresinin hafta sonu izni).

### Yeni kuralların Eylül'de bulduğu ihlaller

| Kural | Kağıt Eylül | Sistem Eylül |
|---|---:|---:|
| A-6 izin günü penceresi | 1 | 4 |
| A-7 sabit haftalık desen | 4 | 0 |
| C-023 gündüzcü haftada tam 1 izin | 8 | 9 |
| C-024 ardışık izin sınırı | 2 | 8 |
| **Yeni ihlal toplamı** | **15** | **21** |
| **Katı ihlal toplamı (yeni set)** | **37** | **21** |

**Sistem Eylül'ün 21 ihlali bir model hatası DEĞİL:** o taslak bu kurallar
yokken çözüldü. Kontrolcü "modelde hata var" diyor çünkü solver ürünü bir
çizelgede katı ihlal normalde hata demektir — burada yalnızca taslağın eski
olduğunu gösteriyor. Eylül yeniden çözülmedi; sunumun konusu Ekim.

### Ekim 2026 — yeni kural setiyle (canlıda yayında)

Boş taslaktan, kopyalama ve ipucu olmadan çözüldü.

| Ölçü | Brütle çözülen (eski Ekim) | **Netle çözülen (yayındaki)** |
|---|---:|---:|
| Çözüm durumu | FEASIBLE | **OPTIMAL** (40 sn) |
| Atama | 386 | 453 |
| Eksik kadro | 23 | **0** |
| Kişi başı net saat (ortalama) | 176,4 sa | **206,4 sa** |
| 200 saat altında kalan kişi | 20 | **0** |
| Adalet farkı | 15,0 sa | **8,2 sa** |
| 3+ gün ardışık boşluk | 9 blok (en uzun 5 gün) | **0 blok** (en uzun 2 gün) |
| Kontrolcü | — | **24 kuralda temiz** |

Adalet farkındaki 8,2 saatin tamamı yapısaldır: eğitim hemşiresi haftada zorunlu
6 gün çalıştığı için 212,3 saate çıkıyor. Ekibin kendi içindeki yayılım **1,33 saat**.

### Bedeli: gündüz kadrosu

| Vardiya | Şablon asgarisi | Çözümdeki ekip |
|---|---:|---:|
| Gündüz | 5 | **6,19** |
| Gece | 5 | 5,03 |

Sebep aritmetik: gece talebi 155 vardiya, 13 dönen kişiye bölününce kişi başı
12 gece = 132 sa net. 200'e ulaşmak için 9 gündüz daha gerekiyor. Üç gündüzcü de
25'er gün çalışınca toplam 192 gündüz-gün çıkıyor; talep 155. **Karar hastanede**
(bkz. `kisit-katalogu.md` → açık sorular).
