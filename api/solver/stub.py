"""Yer tutucu solver: referans haftayı hedef taslağa yayar.

Amacı çizelge üretmek DEĞİL, `model.py` bitmeden uçtan uca akışı çalıştırmaktır:
"Çöz" → solver_runs → assignments → E-09 ızgarası. Böylece API, arayüz ve deploy
zinciri solver'dan bağımsız olarak bugün doğrulanabilir.

Yöntem: 21-27 Eylül referans haftası HAFTA GÜNÜNE göre hedef aya döşenir
(hedef ayın her Pazartesisi referans Pazartesinin kadrosunu alır). Bu, gerçek bir
optimizasyon değildir ama kural yapısı bozulmamış, gerçekçi bir çizelge üretir.
"""

from __future__ import annotations

import time
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from app.settings import get_settings
from solver.interface import SolveResult

REFERANS_TASLAK = "Referans: elle hazırlanan 21-27 Eylül"


def run_solver(draft_id: int, time_limit_s: int = 60) -> SolveResult:
    baslangic = time.monotonic()
    settings = get_settings()

    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Koşu kaydı HEMEN commit edilir. Aksi halde aşağıdaki hata yolundaki
            # rollback bu satırı da geri alır ve teşhis yazılacak run_id kalmaz.
            run_id = _kosuyu_bul_veya_ac(cur, draft_id, time_limit_s)
            conn.commit()
            try:
                atama_sayisi = _referans_haftayi_yay(cur, draft_id)
                teshis_sayisi = _teshisleri_yaz(cur, run_id, draft_id)
                gecen = time.monotonic() - baslangic

                cur.execute(
                    """
                    UPDATE solver_runs
                       SET status          = 'FEASIBLE',
                           finished_at     = CURRENT_TIMESTAMP,
                           objective_value = %s,
                           params_snapshot = %s
                     WHERE id = %s
                    """,
                    (Decimal(0), _parametre_fotografi(cur), run_id),
                )
                conn.commit()
            except Exception as hata:  # noqa: BLE001 — koşu kaydı her hâlükârda kapanmalı
                conn.rollback()
                cur.execute(
                    "UPDATE solver_runs SET status='HATA', finished_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (run_id,),
                )
                cur.execute(
                    """INSERT INTO solver_diagnostics (solver_run_id, severity, message)
                       VALUES (%s, 'uyari', %s)""",
                    (run_id, f"Yer tutucu solver hata verdi: {hata}"),
                )
                conn.commit()
                return SolveResult(
                    run_id=run_id,
                    status="HATA",
                    objective_value=None,
                    assignment_count=0,
                    diagnostic_count=1,
                    elapsed_s=time.monotonic() - baslangic,
                )

    return SolveResult(
        run_id=run_id,
        status="FEASIBLE",
        objective_value=Decimal(0),
        assignment_count=atama_sayisi,
        diagnostic_count=teshis_sayisi,
        elapsed_s=gecen,
    )


def _kosuyu_bul_veya_ac(cur, draft_id: int, time_limit_s: int) -> int:
    """Router zaten 'CALISIYOR' bir satır açtıysa onu kullan; doğrudan çağrıldıysa aç."""
    cur.execute(
        """SELECT id FROM solver_runs
            WHERE draft_id = %s AND status = 'CALISIYOR'
            ORDER BY started_at DESC LIMIT 1""",
        (draft_id,),
    )
    if (satir := cur.fetchone()) is not None:
        return satir["id"]

    cur.execute(
        """INSERT INTO solver_runs (draft_id, status, time_limit_seconds)
           VALUES (%s, 'CALISIYOR', %s) RETURNING id""",
        (draft_id, time_limit_s),
    )
    return cur.fetchone()["id"]


def _referans_haftayi_yay(cur, draft_id: int) -> int:
    """Referans haftayı hedef taslağın ayına hafta gününe göre döşer."""
    # Önceki koşunun ürettikleri gider; elle girilen ve kilitli satırlar kalır.
    cur.execute(
        "DELETE FROM assignments WHERE draft_id = %s AND source = 'solver' AND NOT is_locked",
        (draft_id,),
    )

    # Hedef ayın günleri × referans haftanın aynı hafta günü.
    # ON CONFLICT DO NOTHING: kilitli/manuel bir satır o güne zaten yazılmışsa dokunma.
    cur.execute(
        """
        WITH hedef AS (
            SELECT id AS draft_id, month_start FROM schedule_drafts WHERE id = %s
        ),
        gunler AS (
            SELECT h.draft_id, gs::date AS gun
            FROM hedef h,
                 generate_series(h.month_start,
                                 (h.month_start + INTERVAL '1 month' - INTERVAL '1 day')::date,
                                 INTERVAL '1 day') gs
        ),
        referans AS (
            SELECT a.staff_id, a.shift_type_id, a.work_date,
                   EXTRACT(ISODOW FROM a.work_date)::int AS hafta_gunu
            FROM assignments a
            JOIN schedule_drafts d ON d.id = a.draft_id
            WHERE d.name = %s
        )
        INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date, source)
        SELECT g.draft_id, r.staff_id, r.shift_type_id, g.gun, 'solver'
        FROM gunler g
        JOIN referans r ON r.hafta_gunu = EXTRACT(ISODOW FROM g.gun)::int
        ON CONFLICT (draft_id, staff_id, work_date) DO NOTHING
        """,
        (draft_id, REFERANS_TASLAK),
    )
    atama_sayisi = cur.rowcount

    # Görev rozetleri. staff_competencies filtresi ŞART:
    # migration 010'daki trigger, solver kaynaklı bir atamaya yetkinliksiz görev
    # yazılmasını hata olarak reddeder (referans haftada böyle bir satır var).
    cur.execute(
        """
        WITH yeni AS (
            SELECT a.id, a.staff_id, EXTRACT(ISODOW FROM a.work_date)::int AS hafta_gunu
            FROM assignments a
            WHERE a.draft_id = %s AND a.source = 'solver'
        ),
        referans AS (
            SELECT a.staff_id, t.competency_id,
                   EXTRACT(ISODOW FROM a.work_date)::int AS hafta_gunu
            FROM assignments a
            JOIN assignment_tasks t ON t.assignment_id = a.id
            JOIN schedule_drafts d  ON d.id = a.draft_id
            WHERE d.name = %s
        )
        INSERT INTO assignment_tasks (assignment_id, competency_id)
        SELECT y.id, r.competency_id
        FROM yeni y
        JOIN referans r ON r.staff_id = y.staff_id AND r.hafta_gunu = y.hafta_gunu
        WHERE EXISTS (SELECT 1 FROM staff_competencies sc
                      WHERE sc.staff_id = y.staff_id AND sc.competency_id = r.competency_id)
        ON CONFLICT DO NOTHING
        """,
        (draft_id, REFERANS_TASLAK),
    )
    return atama_sayisi


def _teshisleri_yaz(cur, run_id: int, draft_id: int) -> int:
    """Kapsama eksiklerini E-10'un okuyacağı biçimde teşhis satırına çevirir."""
    cur.execute("DELETE FROM solver_diagnostics WHERE solver_run_id = %s", (run_id,))
    cur.execute(
        """
        INSERT INTO solver_diagnostics (solver_run_id, severity, constraint_id, work_date, message, suggestion)
        SELECT %s,
               'ihlal',
               ntr.constraint_id,
               cov.day,
               -- Not: SQL format() kullanmıyoruz. Onun yer tutucusu psycopg'nin
               -- parametre yer tutucusuyla aynı yazılır ve psycopg yorum içindekini
               -- bile sayar. Düz birleştirme hem okunur hem tuzaksız.
               cov.shift_code || ' ' || cov.slot_code || ': '
                 || cov.assigned || '/' || cov.required
                 || ' (' || (cov.required - cov.assigned) || ' eksik)',
               'İhtiyaç şablonundaki sayıyı gözden geçirin veya yetkin personel ekleyin.'
        FROM v_daily_coverage cov
        JOIN need_periods np        ON np.valid_period @> cov.day
        JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
                                   AND ntr.slot_code = cov.slot_code
        JOIN shift_types st         ON st.id = ntr.shift_type_id AND st.code = cov.shift_code
        WHERE cov.draft_id = %s AND cov.assigned < cov.required
        """,
        (run_id, draft_id),
    )
    return cur.rowcount


def _parametre_fotografi(cur) -> str:
    """Koşu anındaki kural ve parametrelerin JSON kopyası (solver_runs.params_snapshot)."""
    cur.execute(
        """
        SELECT json_build_object(
                 'solver', 'stub',
                 'kurallar', (SELECT json_agg(json_build_object(
                                  'code', c.code, 'catalog_code', c.catalog_code,
                                  'is_hard', c.is_hard, 'weight', c.default_weight))
                              FROM constraints c),
                 'parametreler', (SELECT json_agg(json_build_object(
                                      'key', p.param_key, 'value', p.param_value))
                                  FROM constraint_params p)
               )::text AS foto
        """
    )
    return cur.fetchone()["foto"]
