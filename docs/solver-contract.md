# Solver Sözleşmesi

`api/solver/model.py` ile API arasındaki anlaşma. İmza `api/solver/interface.py`'de:

```python
def run_solver(draft_id: int, time_limit_s: int = 60) -> SolveResult
```

Senkron, kendi veritabanı bağlantısını açar. Router onu `BackgroundTasks` +
`asyncio.to_thread` ile çalıştırır; CP-SAT blokladığı için async havuzu tutmamalı.

---

## 1. Aralığı nereden okuyacaksın

Taslak artık bir aya değil **tarih aralığına** bağlı (migration 012).

```sql
SELECT period FROM schedule_drafts WHERE id = %s;
```

`period` bir `DATERANGE`'dir ve **`[başlangıç, bitiş)`** biçiminde normalize edilir:
alt sınır **dahil**, üst sınır **dışlayıcı**.

```sql
-- Çözülecek günlerin listesi
SELECT gs::date AS gun
FROM schedule_drafts d,
     generate_series(lower(d.period), upper(d.period) - 1, INTERVAL '1 day') gs
WHERE d.id = %s;
```

Aralık 1 gün de olabilir, 1 ay da. `upper(period) - 1` son çalışılacak gündür.

> **Tuzak:** `upper(period)` aralığa **dahil değildir**. 21–27 Eylül haftası
> `[2026-09-21, 2026-09-28)` olarak durur; 28 Eylül çözülmez.

---

## 2. Önceki günlerin bağlamı

`assignments` tablosu taslağın aralığıyla **kısıtlanmamıştır** — bu kasıtlıdır.

Ardışık gece sınırı (C-002), 2 gece sonrası 24 saat boşluk (C-014) ve haftalık
dinlenme (C-016) kuralları, aralığın **başlamasından önceki** günlere bakmayı
gerektirir. Bu bağlam satırları aynı `draft_id` altında, `period`'un dışında,
`source = 'onceki_ay'` ile durur.

```sql
-- Değiştirilemez başlangıç bağlamı: aralıktan ÖNCEKİ günler
SELECT a.staff_id, a.work_date, st.code AS shift_code, st.crosses_midnight
FROM assignments a
JOIN shift_types st ON st.id = a.shift_type_id
JOIN schedule_drafts d ON d.id = a.draft_id
WHERE a.draft_id = %s
  AND a.work_date < lower(d.period)
ORDER BY a.staff_id, a.work_date;
```

Pratikte son 3 gün yeterlidir (en uzun geriye bakış 2 gece + 1 boşluk günü).

> `v_monthly_hours` bu satırları **saymaz** (`d.period @> h.work_date` filtresi).
> Puantaj yalnızca aralık içini ölçer; bağlam günleri başkasının ayına aittir.

---

## 3. Neye dokunmayacaksın

| Koşul | Anlamı |
|---|---|
| `assignments.is_locked = TRUE` | Kullanıcı kilitledi. Sabit girdi, silme, değiştirme. |
| `assignments.source <> 'solver'` | Elle girilmiş (`manuel`) ya da bağlam (`onceki_ay`). Sabit girdi. |

Kendi ürettiklerini silmek için:

```sql
DELETE FROM assignments
WHERE draft_id = %s AND source = 'solver' AND NOT is_locked;
```

Yazarken `source = 'solver'` kullan. Veritabanı seni iki noktada korur:

- **`uq_assignments_draft_staff_date`** — aynı kişiye aynı gün iki vardiya yazamazsın.
- **`assignment_tasks` trigger'ları** — yetkinliği olmayana görev veremezsin
  (`source='solver'` ise **hata**, `manuel` ise uyarı), ve aynı atamada hem
  TRIYAJ hem GOZLEM olamaz.

---

## 4. Nereye yazacaksın

| Tablo | Ne |
|---|---|
| `solver_runs` | Router satırı `status='CALISIYOR'` ile **açar**; sen `status`, `finished_at`, `objective_value`, `params_snapshot` ile **kapatırsın**. |
| `assignments` | Kişi × gün × vardiya, `source='solver'` |
| `assignment_tasks` | Görev rozetleri — yalnız `competencies.kind='TASK'` olanlar (TRIYAJ, AMBULANS, GOZLEM) |
| `solver_diagnostics` | INFEASIBLE ya da eksik kapsama açıklamaları; `constraint_id` ile kurala bağla |

`status` sözlüğü: `OPTIMAL` · `FEASIBLE` · `INFEASIBLE` · `HATA`.

`params_snapshot` JSONB'ye `{"solver": "cpsat", ...}` yaz. Arayüz `"stub"` gördüğünde
"Referans kopya (solver değil)" etiketini gösteriyor; `"cpsat"` yazınca etiket
kendiliğinden kalkar.

---

## 5. Kuralları nereden okuyacaksın

Kurallar kodda değil veritabanındadır — E-03 ekranı bunları değiştirebiliyor.

```sql
SELECT c.code, c.catalog_code, c.is_hard, c.default_weight, c.scope, c.source,
       p.param_key, p.param_value
FROM constraints c
LEFT JOIN constraint_params p ON p.constraint_id = c.id;
```

- `is_hard = TRUE` → ağırlık `NULL`, ihlal edilemez
- `is_hard = FALSE` → `default_weight > 0`, ihlal cezalandırılır

Vardiya başına kaç kişi gerektiği ihtiyaç şablonundadır ve kurala bağlıdır:

```sql
SELECT st.code AS vardiya, ntr.slot_code, ntr.min_count, c.code AS kural
FROM need_periods np
JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
JOIN shift_types st ON st.id = ntr.shift_type_id
LEFT JOIN constraints c ON c.id = ntr.constraint_id
WHERE np.valid_period @> %s;   -- çözülen gün
```

İş bölümü: **satır** "ne, kaç kişi" der; **kural** "zorunlu mu, cezası ne" der.

---

## 6. Triyaj / gözlem / ambulans modeli

Migration 011'in getirdiği saha kuralları:

1. Sorumlu hemşire ve oryantasyondakiler **hariç**, vardiyadaki her çalışan ya
   TRIYAJ ya GOZLEM görevindedir (`all_crew_triage_or_observation`).
2. TRIYAJ ve GOZLEM **aynı kişide olamaz** (trigger uyguluyor).
3. AMBULANS ikisiyle de birleşebilir: AMB+TRI ve AMB+GÖZ geçerlidir.
4. Ambulans **dönüşlüdür**: gidenler kendi alanlarının sayısından düşmez, ama
   çıktıklarında **triyajda en az 1, gözlemde en az 1** kişi kalmalıdır
   (`min_remaining_after_ambulance`, C-009; parametreler `min_remaining_triage`,
   `min_remaining_observation`).

Sayma kuralları **sende**. Veritabanı yalnızca (2)'yi zorluyor, geri kalanını
`v_daily_coverage` **ölçüyor**:

```sql
SELECT day, shift_code, slot_code, required, assigned,
       qualified,                  -- yetkinliğe sahip kişi (rozetten bağımsız)
       remaining_after_ambulance   -- TRIYAJ/GOZLEM: ambulansa çıkmayanlar
FROM v_daily_coverage
WHERE draft_id = %s;
```

Kendi çözümünü doğrulamak için bu view'a bakabilirsin; `remaining_after_ambulance = 0`
bir C-009 ihlalidir.

---

## 7. Geçiş

`SOLVER_IMPL` ortam değişkeni hangi uygulamanın çağrılacağını seçer:

```
SOLVER_IMPL=stub    → solver/stub.py   (referans haftayı kopyalar)
SOLVER_IMPL=cpsat   → solver/model.py  (gerçek çözücü)
```

Railway'de bu değişkeni `cpsat` yapmak yeterli; API ve arayüz kodu değişmez.
