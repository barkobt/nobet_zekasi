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
| Kadro eksiği olan vardiya | **30** | **0** |
| Eksik kişi (toplam) | **38** | **0** |
| Ambulans çıkınca alan boş kalan vardiya | **3** | **0** |
| Saat farkı (en çok − en az) | **70,0 sa** | **31,5 sa** |
| Gece farkı | **14** | **12** |
| Geçersiz acil takviye | 5 | 0 |

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

Bunların yanında **65 gevşetilebilir slot eksiği** var (kadro yetmemiş).
Ayrıca 20 rozet, yetkinliği olmayan kişiye verilmiş — elle yazıldığı için
uyarı sayıldı, hata değil.

### Sistemde bulunan ihlal

Yok. Her çözümün sonunda kontrolcü kendiliğinden koşuyor; katı ihlal bulursa
çözüm teşhisinin (E-10) en üstüne kırmızı satır yazıyor. Bu çizelgede yazmadı.

---

## 3. Kadro eksikleri

Sayılar `v_daily_coverage` görünümünden: bir vardiyanın bir slotu gerekenin
altındaysa bir satır. (Kontrolcü çıktısı aynı eksikleri gün×vardiya kırılımıyla
sayar, o yüzden orada satır sayısı farklı görünür.)

| Slot | Kağıt: kaç vardiyada | Kağıt: toplam eksik kişi | Sistem |
|---|---:|---:|---|
| Gözlem (en az 2) | 21 | 23 | 0 |
| Ambulans (2 kişi) | 7 | 13 | 0 |
| Genel mevcut (5 kişi) | 1 | 1 | 0 |
| Triyaj (en az 3) | 1 | 1 | 0 |

Sistem çizelgesinde kadro eksiği **sıfır**: aynı 20 kişiyle, aynı izinlerle,
her vardiyanın her slotu dolduruldu.

**Ambulans çıkınca alan boşalması** kağıtta 3 vardiyada oldu — ambulansa çıkan
2 kişi gidince triyajda ya da gözlemde kimse kalmadı. Sistemde C-009 katı kural
olduğu için bu 0.

---

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
5. **İzin günü hedefi düşürür.** Aylık 200 saatlik hedef, izin/rapor günü başına
   7,5 saat iner (hastane onaylı). Hem çözücü hem ekran aynı hesabı yapıyor.

---

## 6. Ne kanıtlıyor

Aynı kadro ve aynı izinlerle:

- Kağıtta **22 kural ihlali** var, sistemde **hiç yok**.
- Kağıtta **30 vardiyada kadro eksik**, sistemde **hiçbirinde**.
- Kağıtta 3 kez **ambulans çıkınca alan boş kalmış**, sistemde hiç.
- Gece çalışan 13 kişinin saati ve gece sayısı kağıtta **191,5–260 saat /
  6–14 gece** arasında dağılmış; sistemde **hepsi 221,5 saat ve 12 gece**.

Kağıdı hazırlayan sorumlu hemşire hatalı çalışmadı — bu kadar kuralı elle,
aynı anda tutmak mümkün değil. Sistemin yaptığı, aynı kuralları her hücrede
aynı anda kontrol edebilmek.
