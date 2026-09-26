"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AppShell } from "@/components/shell/AppShell";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type Matrix = components["schemas"]["CompetencyMatrix"];
type Competency = components["schemas"]["Competency"];

const KISA: Record<string, string> = {
  IV: "IV", IM: "İM", HASTA_ILT: "İLET", SHIFT_YETKILISI: "LİDER", SAYIM: "SAYIM",
  TRIYAJ: "TRY", AMBULANS: "AMB", GOZLEM: "GÖZ",
};

export default function YetkinlikSayfasi() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["competency-matrix"],
    queryFn: () => api<Matrix>("/competency-matrix"),
  });

  const degistir = useMutation({
    mutationFn: ({ staffId, code, ver }: { staffId: number; code: string; ver: boolean }) =>
      api<Matrix>(`/people/${staffId}/competencies/${code}?ver=${ver}`, { method: "PUT" }),
    onSuccess: (yeni) => qc.setQueryData(["competency-matrix"], yeni),
  });

  if (isLoading || !data) {
    return (
      <AppShell>
        <h1 className="mb-4" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
          Yetkinlik Matrisi
        </h1>
        <div className="rounded-lg border bg-card p-6">
          <p className="text-muted-foreground">Yükleniyor…</p>
        </div>
      </AppShell>
    );
  }

  // Görev yetkinlikleri önce ve görsel olarak ayrı: bunlar vardiya içinde ATANIR,
  // diğerleri kişinin taşıdığı yetkidir.
  const gruplar: { ad: string; sutunlar: Competency[] }[] = [
    { ad: "Görev", sutunlar: data.tasks },
    { ad: "Yetki", sutunlar: data.qualifications },
  ];
  const tumSutunlar = [...data.tasks, ...data.qualifications];

  return (
    <AppShell>
      <div className="mb-4 flex items-baseline justify-between">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Yetkinlik Matrisi</h1>
        <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          {data.rows.length} kişi
        </span>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full border-collapse" style={{ fontSize: "var(--text-base)" }}>
          <thead>
            <tr>
              <th rowSpan={2} className="sticky left-0 z-20 min-w-[200px] border-b border-r bg-card p-0 text-left align-bottom">
                <span className="block px-3 pb-2 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  Personel
                </span>
              </th>
              {gruplar.map((g, i) => (
                <th
                  key={g.ad}
                  colSpan={g.sutunlar.length}
                  className={"border-b bg-background px-2 py-1.5 text-muted-foreground " + (i > 0 ? "border-l" : "")}
                  style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}
                >
                  {g.ad.toUpperCase()}
                </th>
              ))}
            </tr>
            <tr>
              {gruplar.map((g, gi) =>
                g.sutunlar.map((c, ci) => (
                  <th
                    key={c.code}
                    title={c.name}
                    className={"min-w-[62px] border-b bg-card px-1 py-2 " + (gi > 0 && ci === 0 ? "border-l" : "")}
                    style={{ fontSize: "var(--text-xs)" }}
                  >
                    {KISA[c.code] ?? c.code}
                  </th>
                )),
              )}
            </tr>
          </thead>

          <tbody>
            {data.rows.map((r) => (
              <tr key={r.staff_id} className="group border-b last:border-0">
                <th className="sticky left-0 z-10 border-r bg-card p-0 text-left font-normal group-hover:bg-accent">
                  <div className="flex h-10 items-center gap-2 px-3">
                    <span className="truncate font-medium">{r.full_name}</span>
                    {r.is_orientation && (
                      <span className="shrink-0 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                        ory.
                      </span>
                    )}
                  </div>
                </th>
                {gruplar.map((g, gi) =>
                  g.sutunlar.map((c, ci) => {
                    const var_ = (r.codes ?? []).includes(c.code);
                    return (
                      <td
                        key={c.code}
                        className={"h-10 text-center group-hover:bg-accent " + (gi > 0 && ci === 0 ? "border-l" : "")}
                      >
                        <input
                          type="checkbox"
                          checked={var_}
                          onChange={() =>
                            degistir.mutate({ staffId: r.staff_id, code: c.code, ver: !var_ })
                          }
                          className="size-4 accent-brand"
                          aria-label={`${r.full_name} — ${c.name}`}
                        />
                      </td>
                    );
                  }),
                )}
              </tr>
            ))}
          </tbody>

          <tfoot>
            <tr className="border-t bg-background">
              <th className="sticky left-0 z-10 border-r bg-background p-0 text-left font-normal">
                <span className="block px-3 py-2 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  Toplam
                </span>
              </th>
              {tumSutunlar.map((c, i) => (
                <td
                  key={c.code}
                  className={"px-1 py-2 text-center font-medium " + (i === data.tasks.length ? "border-l" : "")}
                >
                  {c.staff_count}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>

      <p className="mt-2 px-1 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        Sütun altındaki sayı o yetkinliğe sahip aktif personel sayısıdır. Düşük bir sayı
        çizelgenin çözülememesinin en sık sebebidir.
      </p>
    </AppShell>
  );
}
