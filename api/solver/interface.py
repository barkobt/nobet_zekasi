"""Solver sözleşmesi — API ile CP-SAT modeli arasındaki tek arayüz.

Bu dosya iki tarafın da uyduğu kontrattır:
  * `api/solver/model.py`  → gerçek CP-SAT çözücü (Baran yazıyor)
  * `api/solver/stub.py`   → referans haftayı taslağa kopyalayan yer tutucu

`run_solver` SENKRONDUR ve KENDİ veritabanı bağlantısını açar. Sebep: CP-SAT bloklayan
bir kütüphanedir; FastAPI'nin async havuzunu tutmaması gerekir. Router bu fonksiyonu
`BackgroundTasks` ile ayrı bir thread'de çalıştırır.

SORUMLULUK SINIRI (önemli):
  * `solver_runs` satırını status='CALISIYOR' ile AÇAN taraf router'dır — frontend'in
    hemen yoklayabileceği bir run_id'si olsun diye.
  * O satırı SONUÇLANDIRAN (status, finished_at, objective_value, params_snapshot)
    ve `assignments` / `assignment_tasks` / `solver_diagnostics` tablolarına YAZAN
    taraf `run_solver`'dır.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol

SolverStatus = Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "HATA"]
"""solver_runs.status ile aynı sözlük (CALISIYOR hariç: o router'ın açtığı başlangıç durumu)."""


@dataclass(frozen=True)
class SolveResult:
    """Bir koşunun özeti. E-08 metrik tablosu ve E-10 teşhis ekranı bunu okur."""

    run_id: int
    status: SolverStatus
    objective_value: Decimal | None
    assignment_count: int
    diagnostic_count: int
    elapsed_s: float


class SolverCallable(Protocol):
    def __call__(self, draft_id: int, time_limit_s: int = 60) -> SolveResult: ...


def run_solver(draft_id: int, time_limit_s: int = 60) -> SolveResult:
    """Taslağı çözer ve sonucu veritabanına yazar.

    Hangi uygulamanın çağrılacağını `settings.solver_impl` belirler:
      'stub'  → solver.stub.run_solver
      'cpsat' → solver.model.run_solver
    Böylece model.py bitince tek bir ortam değişkeniyle geçilir, çağıran kod değişmez.
    """
    from app.settings import get_settings

    impl = get_settings().solver_impl
    if impl == "cpsat":
        from solver import model  # yalnızca gerektiğinde: ortsolver bağımlılığı stub'da aranmaz

        return model.run_solver(draft_id=draft_id, time_limit_s=time_limit_s)

    from solver import stub

    return stub.run_solver(draft_id=draft_id, time_limit_s=time_limit_s)
