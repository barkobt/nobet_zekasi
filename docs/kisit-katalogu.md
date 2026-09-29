# Kısıt Kataloğu

> Kaynak: Notion "Kısıt Kataloğu" veritabanı (22 satır, 25 Eylül 2026 itibarıyla).
> **Önemli:** Veritabanı çalışması sırasında bazı kararlar Notion'dan sonra güncellendi.
> `db/seeds` içindeki `constraints` / `constraint_params` verisi ile çelişki varsa
> **veritabanı doğrudur**; çelişkiyi raporla. Bilinen güncellemeler en altta.

Tip: **Hard** = asla ihlal edilemez · **Soft** = ihlal cezalandırılır (ağırlık) · **Tanım** = modelin girdisi, kısıt değil · **Kapsam Dışı** = saklı, varsayılan kapalı
Kaynak: **Yasal** = UI'da gevşetilemez · **Kurumsal** = gevşetilebilir · **Tercih** · **Belirsiz**

| Kod | Tip | Kapsam | Kaynak | Ağırlık | Kural |
|---|---|---|---|---|---|
| C-001 | Tanım | Vardiya | Kurumsal | — | Gündüz 08:30–18:00 (9,5 sa), Gece 18:00–08:30 (14,5 sa); aralarında boşluk yok. Devir teslim çalışma saatine dahil. |
| C-002 | Hard | Kişi | Belirsiz | — | 3 gece üst üste çalışılamaz (2 gece serbest). |
| C-003 | Soft | Hafta | Kurumsal | 10 | Haftalık 50 saat **net** referans değer; sapma cezalandırılır, yasaklanmaz. Hafta Pzt–Paz. |
| C-004 | Hard | Ay | Kurumsal | — | Kişi başı aylık en az 200 saat **net** (mola hariç). İzinli/raporlu günde hedef gün başına 7,5 sa net düşer. Hedeftir, tavan değil. |
| C-005 | Hard | Vardiya | Kurumsal | — | Gündüz EN AZ 6 kişi (fazlası sorun değil), 1'i sorumlu. |
| C-006 | Hard | Vardiya | Kurumsal | — | Gece EN AZ 5 kişi, sorumlu yok. |
| C-007 | Hard | Vardiya | Kurumsal | — | Her vardiyada en az 1 shift yetkilisi (ekip lideri). Ekip lideri triyaj/ambulans da alabilir. |
| C-008 | Hard | Hafta | Kurumsal | — | Sorumlu (tek kişi): hafta içi 08:30–18:00, Cumartesi 08:30–14:00, Pazar izinli. |
| C-009 | Hard | Vardiya | Kurumsal | — | Ambulans görevi için 2 kişi (bkz. güncelleme notu). |
| C-010 | Hard | Vardiya | Kurumsal | — | Gözlem alanında 2 yetkin kişi; triyaj görevindekilerden FARKLI. |
| C-011 | Hard | Vardiya | Kurumsal | — | Triyajda EN AZ 3 yetkin kişi; gözlem görevindekilerden FARKLI. |
| C-012 | Tanım | Kişi | Kurumsal | — | Yetkinlik tanımları (eğitim hemşiresi kaydını tutar). |
| C-013 | Soft | Vardiya | Kurumsal | 40 | Uyumsuz kişiler aynı vardiyaya yazılırsa ceza. |
| C-014 | Hard | Kişi | Kurumsal | — | 2 gece art arda çalışıldıysa 24 saat yasal boşluk zorunlu; 08:30'dan itibaren sayılır. |
| C-015 | Tanım | Kişi | Kurumsal | — | [C-014 ile birleşti] Gündüz→gündüz geçişi serbest; genel "her vardiya arası 24h" kuralı yok. |
| C-016 | Hard | Hafta | Yasal | — | Haftada EN AZ 1 dinlenme olayı: izin günü VEYA 2 gece sonrası 24h boşluk (biri yeterli). |
| C-017 | Hard | Kişi | Kurumsal | — | Sadece gündüz çalışabilen personel geceye yazılamaz. |
| C-018 | Kapsam Dışı | Vardiya | Tercih | — | 24 saatlik vardiya kullanılmaz (`enable_24h` bayrağı, varsayılan kapalı). |
| C-019 | Hard | Vardiya | Kurumsal | — | Ambulans/gözlem görevleri vardiya mevcudunun İÇİNDEN atanır (ayrı kadro değil). |
| C-020 | Hard | Kişi | Kurumsal | — | Oryantasyondaki yeni personel eğitim hemşiresiyle birebir çalışır. |
| O-001 | Soft (amaç) | Ay | Kurumsal | 200 | Aylık 200 saat **net** üzeri fazla mesai toplamını minimize et. |
| O-002 | Soft (amaç) | Ay | Kurumsal | 220 | Kişiler arası saat dağılımını dengele (max–min farkı). **Adalet en önemli başarı kriteri.** |

## Veritabanı çalışmasında sonradan değişenler (şema bunlara göre kuruldu)
- **Ambulans kuralı** artık triyaj havuzuna bağlı değil; bağımsız görev/yetkinlik olarak modellendi.
- **Sayım yetkisi** ile **ekip lideri** ayrı yetkinlikler.
- Süpervizörler ve oryantasyondaki personel günlük mevcut (C-005/C-006) sayımına dahil edilmez.
- Kısa gece vardiya tipi (GECE_0100) kaldırıldı.
- Merve Armut yalnızca gündüz çalışır (C-017 kapsamında).
- **O-006, O-007, O-008 eklendi** (28.09, `seeds/016`):

  | Kod | Kural | Ağırlık |
  |---|---|---|
  | O-006 | Karşılanamayan personel isteği (BEKLEMEDE) | 22.000 |
  | O-007 | Triyajda hasta iletişimi tercihi | 2.200 |
  | O-008 | Ambulans ekibi 1 triyaj + 1 gözlem tercihi | 2.200 |

  O-006'nın ağırlığı hesapla konuldu: bir karşılanmayan istek ≈ saat adaletinde
  5 saatlik bozulma → 10 yarım saat × 2.200 = 22.000.
- **C-011'den HASTA_ILT şartı kaldırıldı** (28.09, `seeds/016`). Triyaj slotu artık
  yalnız TRIYAJ yetkinliği ister; hasta iletişimi şart değil TERCİH (O-007). Şart
  olarak dururken hasta iletişimi olmayan bir triyaj yetkilisi havuzdan tamamen
  düşüyordu.
- **`ambulance_crew_size` eklendi** (28.09, `seeds/016`, katalog kodu yok). C-009
  yalnız "ambulans sonrası alanda kalan" kuralını anlatıyor ve **katı** kaldı;
  ambulans ekip mevcudu (2 kişi) ayrı, gevşetilebilir kurala taşındı. Üst sınır
  katı: araç 2 kişiliktir.
- **Eksik cezaları kademelendi ve kurallar soft'a çevrildi** (28.09, `seeds/016`).
  Solver bu kuralları zaten gevşetiyordu; katalog "Hard" diyordu ama gerçek davranış
  "çok pahalı ama gevşetilebilir". Şema CHECK'i ağırlıklı kuralın soft olmasını
  istediği için `is_hard` artık FALSE ve **gerçek davranış veritabanında görünüyor**:

  | Kural | Eski | Yeni ağırlık |
  |---|---|---|
  | C-005 / C-006 genel mevcut | Hard | **2.000.000** |
  | C-007 ekip lideri | Hard | **1.500.000** |
  | C-011 triyaj | Hard | **1.200.000** |
  | `ambulance_crew_size` ambulans mevcudu | — | **900.000** |
  | C-010 gözlem | Hard | **700.000** |
  | `all_crew_triage_or_observation` | Hard | **600.000** |
  | `count_authority_required` sayım | Hard | **500.000** |
  | **C-009 ambulans sonrası kalan** | Hard | **Hard kaldı** |

  Değerler **hastane teyidi beklemektedir** (açıklamalarına da yazıldı). En küçüğü
  (sayım, 500.000) C-004'ün dakika başına cezasından (20.000) 25 kat büyük:
  bir vardiyada sayım yetkilisinin olmaması, birinin aylık hedefinin 25 dakika
  altında kalmasına bedel.
- **O-003, O-004, O-005 eklendi** (28.09, `seeds/015`): gece adaleti, hafta sonu
  adaleti, ambulans görev dengesi. Üçü de soft.
- **Yumuşak ağırlıklar etkin değerlere çekildi** (28.09, `seeds/015`). Notion'daki
  200/220 istenen önceliği ifade etmiyordu (fazla mesai ile adalet neredeyse eşitti).
  Ağırlık "yarım saat başına ceza" anlamında yazıldı ve sıralamayı kendisi taşıyor
  (birim 29.09'da dakikaya geçti, oranlar `solver/model.py` → `YB_DK` ile korundu):

  | Kod | Eski | Yeni | Kademe |
  |---|---|---|---|
  | O-002 adalet | 220 | **2.200** | 3 |
  | O-003 gece adaleti | — | **2.200** | 3 |
  | O-004 hafta sonu adaleti | — | **2.200** | 3 |
  | O-001 fazla mesai | 200 | 200 | 4 |
  | O-005 ambulans dengesi | — | **200** | 4 |
  | C-003 haftalık 50 sa | 10 | 10 | 5 |

  Kapsama/görev eksiği (100.000.000/kişi) ve C-004 eksik saati katı kurallar olduğu
  için ağırlıkları `constraints`'te değil `solver/model.py`'de.
- **C-021 eklendi** (28.09, `seeds/014`): gece çalışan ertesi gün gündüze yazılamaz.
  Gece 08:30'da biter, gündüz 08:30'da başlar — arada dinlenme yok. C-014 iki gece
  sonrasını düzenliyordu, tek gece sonrası açıkta kalmıştı. Hard, kurumsal
  (24 saatlik vardiya açılırsa gevşetilebilsin diye). **Notion'a da işlenmeli.**

### Molalar mesaiye dahil değil (29.09, `migration 023` + `seeds/030`)

Gündüz molası 80 dk, gece molası 210 dk (Edem). Mesaiden düşülür; ne zaman
kullanıldığı kayıt altına alınmaz.

| | Brüt | Mola | **Net** |
|---|---|---|---|
| Gündüz | 9,5 sa | 80 dk | **8 sa 10 dk** |
| Gece | 14,5 sa | 210 dk | **11 sa** |
| Gündüz (Cmt, sorumlu) | 5,5 sa | 0 dk | **5 sa 30 dk** — *mola değeri hastaneye sorulacak* |

**Net ölçülen:** C-004 (200 sa), C-003 (50 sa), O-001 fazla mesai, O-002 saat
adaleti, personel özeti, raporlar, Excel, solver amaç fonksiyonu.
**Brüt kalan:** vardiya başlangıç/bitiş saati, geç çıkış, `actual_times`'taki ham
veri, dinlenme kuralları (C-002, C-014, C-016, C-021). Mola dinlenme sayılmaz;
saat aralığı gerçek zamandır.

Mola süreleri E-01'den düzenlenebilir, koda gömülü değil.

**Sonucu (Ekim 2026, aynı veri, boş taslaktan çözüm):**

| | Brütle çözülen (#2) | Netle çözülen (#29) |
|---|---|---|
| Adalet farkı | 15,0 sa | **1,3 sa** |
| Kişi başı ortalama (net) | 176,4 sa | **205,2 sa** |
| 3+ gün ardışık boşluk | 9 blok (en uzun 5 gün) | **0 blok** (en uzun 2 gün) |
| Gündüz vardiyasında kadro | 5,1 kişi (gereken 5) | **7,0 kişi** |

Son satır bedeldir: 200 saat **net** hedefine ulaşmak, gündüz vardiyasına şablon
asgarisinin üstünde 2 kişi koymayı gerektiriyor. Ekim'in GENEL talebi net 2.970,8
saat, 18 kişinin hedefi ise 3.600 saat — aradaki 629 saatlik açık kadro
fazlasıyla kapanıyor. **Karar hastanede.**

### İzin (off) desenleri (29.09, `migration 024` + `seeds/031`)

| Kod | Tip | Kapsam | Kural |
|---|---|---|---|
| C-023 | Hard | Hafta | Sadece gündüz çalışan personel haftada **tam 1 gün** izin yapar (6 gün çalışır). 2 ya da 3 değil. |
| C-024 | Hard | Kişi | Üst üste en fazla **2** izinsiz boş gün. 3+ gün blok kullanılmaz. |
| C-025 | **Soft** (800) | Hafta | Gündüz+gece çalışabilen personelin her tam haftasında en az 1 gündüz **ve** en az 1 gece bulunur. |

Hafta **Pazartesi–Pazar takvim haftası** (Edem teyidi), kayan 7 gün değil. İkisi de
yalnız dönemin içinde TAMAMEN kalan haftalara uygulanır: ay başı/sonundaki yarım
haftada "tam 1 izin" kaçınılmaz bir ihlal üretirdi.

**İstisna:** yıllık izin, rapor ve planlayıcının girdiği KESIN boş gün istekleri
her iki kuralın da dışındadır — bloğu uzatabilirler (Edem).

#### C-025 neden gerekti (29.09)

Solver bazı haftalarda gündüz+gece çalışabilen birine haftanın **tamamını gece**
yazıyordu. Gece 11 saat olduğu için tam gece haftası 3-4 vardiyada doluyor, geriye
3-4 boş gün kalıyor; dengelemek için aynı hafta başka birine **tamamen gündüz**
düşüyor. Ölçüm (Ekim 2026, 60 kişi-hafta): **4 yalnız-gece, 17 yalnız-gündüz,
39 karma.** Bir kişide 3 gece + **4 boş gün** çıktı.

C-024 bunu yakalamıyor çünkü 4 boş gün 2+2 olarak bölünebiliyor ve "üst üste en
fazla 2" kuralı sağlanmış oluyor.

Kural **yumuşak**: gerçekten gerekiyorsa tek tip hafta kurulabilir, ama bedeli var.
Sadece-gündüz ve sadece-gece personele uygulanmaz.

#### Hedefe tam ulaşma cezası (C-004 parametresi, 29.09)

`exact_target_penalty = 5000`. Vardiyalar 490 ve 660 dakikalık parçalar:
10 gece + 11 gündüz = 11.990 dk = **199,83 saat**, hedefin 10 dakika altı. Bir
vardiya daha eklemek 208 saate fırlatıyor. Yalnız orantılı ceza varken solver o
10 dakikayı açık bırakmayı tercih ediyordu (Ekim'de 10 kişi 0,2 saat eksikti).
Artık hedefin altında kalmak, açığın büyüklüğünden **bağımsız** sabit bir ceza
daha yazıyor; son adımı atmak kârlı hale geliyor.

#### Kişiye özel desenler — `staff_weekly_patterns`

Üç tür, üçü de katı. Hepsi **veri**; kodda gün, vardiya ya da kişi adı geçmez.

| Tür | Anlamı |
|---|---|
| `SABIT_VARDIYA` | O hafta günü kişi mutlaka bu vardiyada |
| `SABIT_OFF` | O hafta günü kişi mutlaka boş |
| `OFF_OLABILIR` | Haftalık izin günü bu günlerden biri olmak zorunda |

Bugünkü kayıtlar:

- **Halit Güler** (sorumlu): Pzt–Cum `GUNDUZ`, Cmt `GUNDUZ_CMT` (5,5 sa, 14:00 çıkış),
  Paz `SABIT_OFF`. C-008'in ta kendisi — **eskiden `solver/model.py`'de kod olarak
  yazılıydı, artık veri.** Kağıda dönmek istenirse Cumartesi satırının vardiyası
  `GUNDUZ`a çekilir, tek UPDATE.
- **Şükran Ünlü** (eğitim): Cmt ve Paz `OFF_OLABILIR` — haftalık izni hafta sonuna
  düşmek zorunda, hangisi olduğunu solver seçer.

#### Kapsama ile 200 saat havuzu AYRI sorular

`roles.counts_toward_coverage` eklendi (migration 024); kapsama dışı rol artık view'a
ve solver'a gömülü değil. Sorumlu hemşire ve **eğitim hemşiresi** ekip kadrosuna
sayılmaz — çalışırlar ama 5 kişilik ekibin yerine geçmezler.

> **Yakalanan hata:** kod "kapsamaya sayılmıyorsa 200 saat havuzuna da girmez"
> diyordu. Eğitim hemşiresi kapsamadan çıkınca hedefini de kaybetti ve 179,7 saatte
> kaldı. İkisi ayrıldı: havuz dışı kalmanın gerekçesi artık **sabit programlı olmak**
> (çizelgesi veri, solver değiştiremez) ya da **oryantasyonda olmak** (saati eşininkini
> yansıtır) — kapsama değil.

## Bilinen açık sorular
- **GUNDUZ_CMT (5,5 sa kısa Cumartesi) molası kaç dakika?** Bugün 0 kabul edildi.
- **Gündüz vardiyasında 5 yerine 7 kişi kabul edilebilir mi?** Kabul edilmezse
  200 saat net hedefi bu kadroyla ulaşılamaz (yukarıdaki tablo).
- C-016: hafta sınırını aşan 24h boşluk hangi haftaya sayılır.
- C-008: sorumlu izinliyken yerine kim bakar.
