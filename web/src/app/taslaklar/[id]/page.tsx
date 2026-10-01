"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Loader2, Menu, Play } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { HataKutusu } from "@/components/HataKutusu";
import { Izgara } from "@/components/cizelge/Izgara";
import { DonemGezgini } from "@/components/cizelge/DonemGezgini";
import { DetayDugmesi, useDetaylar } from "@/components/cizelge/DetayDugmesi";
import { TaslakPaneli } from "@/components/taslak/TaslakPaneli";
import { ExcelDugmesi } from "@/components/ExcelDugmesi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, sunucuAciklamasi } from "@/lib/api";
import { sayi, type Schedule } from "@/lib/cizelge";
import { aralikEtiketi, type Draft, type SolveAccepted } from "@/lib/taslak";
import { aralik, iso as isoGun, type Olcek } from "@/lib/donem";


export default function TaslakSayfasi({ params }: { params: Promise<{ id: string }> }) {
  const draftId = Number(use(params).id);
  const qc = useQueryClient();
  const [panel, setPanel] = useState(false);

  // staleTime 0: sayfaya her girişte taslağın SON koşusu sunucudan okunur.
  const { data: taslak } = useQuery({
    queryKey: ["draft", draftId],
    queryFn: () => api<Draft>(`/drafts/${draftId}`),
    staleTime: 0,
  });

  // Görünen aralık DÖNEME KIRPILMAZ: hafta her zaman Pazartesi–Pazar, ay her zaman
  // 1'inden sonuna. Aralığa düşen dönem dışı günler taralı ve salt okunur gelir
  // (içerikleri yayınlanmış çizelgeden).
  const [olcek, setOlcek] = useState<Olcek>("hafta");
  // Çapa kullanıcı gezmediyse taslağın ilk günü. Türetiliyor, effect ile
  // senkronlanmıyor: taslak gelene kadar null, geldiğinde doğru haftaya düşer.
  const [secilenCapa, setCapa] = useState<Date | null>(null);
  const capa =
    secilenCapa ?? (taslak ? new Date(taslak.period_start + "T00:00:00Z") : null);

  const [gorunenBas, gorunenSon] = capa ? aralik(capa, olcek) : [null, null];
  const bas = gorunenBas ? isoGun(gorunenBas) : null;
  const son = gorunenSon ? isoGun(gorunenSon) : null;

  const { acik: detaylar } = useDetaylar();

  // ÖNBELLEK ANAHTARINDA KOŞU VAR (01.10): yeni bir koşu bitince anahtar değişir
  // ve önceki koşunun ızgarası ASLA gösterilmez — yenisi gelene kadar "yükleniyor".
  // Eskiden önbellekteki eski çizelge görünüyor, yenisi arkadan geliyordu:
  // "çözüldü" yazarken tablo hâlâ eskiydi.
  const kosuAnahtari = taslak
    ? `${taslak.last_run?.id ?? 0}:${taslak.last_run?.status ?? ""}`
    : null;
  const { data: cizelge, isLoading, error: hata } = useQuery({
    queryKey: ["schedule", draftId, bas, son, kosuAnahtari],
    queryFn: () => api<Schedule>(`/drafts/${draftId}/schedule?from=${bas}&to=${son}`),
    enabled: !!bas && !!son && kosuAnahtari !== null,
  });

  // Herhangi bir veri yeniden okunacaksa TÜM önbellek eskir: rapor, liste, teşhis
  // da bu taslağın sayılarını gösteriyor.
  const tazele = () => {
    qc.invalidateQueries();
  };

  // ÇÖZÜM TAKİBİ TEK YERDE: TASLAKLAR LİSTESİ (Baran, 01.10).
  //   · "Çöz" → koşu sunucuda başlar, kullanıcı listeye gider; orada "Çözülüyor"
  //     rozeti görünür ve satır kilitlidir.
  //   · Çözülürken taslak AÇILMAZ: adresi doğrudan yazılsa bile listeye döner.
  //     Yarım sonuç görülmez, elle değişiklik solver'ın yazdığıyla çakışmaz.
  //   · Çözüldüğünde liste (otomatik ya da Yenile ile) sonucu gösterir; taslak
  //     açılınca ızgara o koşunun sonucuyla gelir (önbellek anahtarında koşu var).
  const router = useRouter();
  const suruyor = taslak?.last_run?.status === "CALISIYOR";
  useEffect(() => {
    if (suruyor) router.replace("/taslaklar");
  }, [suruyor, router]);

  const coz = useMutation({
    mutationFn: () =>
      api<SolveAccepted>(`/drafts/${draftId}/solve`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({}),
      }),
    onSuccess: () => {
      // Listeye "Çözülüyor" ile girilsin: listenin ve bu taslağın önbelleği düşer.
      qc.removeQueries({ queryKey: ["drafts"] });
      qc.removeQueries({ queryKey: ["draft", draftId] });
      router.push("/taslaklar");
    },
  });

  const calisiyor = coz.isPending || coz.isSuccess || suruyor;

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-baseline gap-3">
          <Button variant="ghost" size="icon" asChild aria-label="Taslaklara dön">
            <Link href="/taslaklar"><ChevronLeft size={16} strokeWidth={1.75} /></Link>
          </Button>
          <h1 className="truncate" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
            {taslak?.name ?? "…"}
          </h1>
          {taslak && (
            <span className="shrink-0 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              {aralikEtiketi(taslak.period_start, taslak.period_end)}
            </span>
          )}
          {taslak?.last_run?.is_reference_copy && (
            <Badge variant="secondary" className="h-5 shrink-0 rounded-sm px-1.5 font-normal"
                   style={{ fontSize: "var(--text-xs)" }}>
              Referans kopya
            </Badge>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {capa && (
            <DonemGezgini olcek={olcek} capa={capa} onCapa={setCapa} onOlcek={setOlcek} />
          )}

          <ExcelDugmesi draftId={draftId} aralik={bas && son ? [bas, son] : null} />

          <Button onClick={() => coz.mutate()} disabled={calisiyor} className="ml-1">
            {calisiyor ? (
              <><Loader2 size={16} strokeWidth={1.75} className="animate-spin" />Başlatılıyor…</>
            ) : (
              <><Play size={16} strokeWidth={1.75} />Çöz</>
            )}
          </Button>

          <Button variant="outline" size="icon" onClick={() => setPanel(true)} aria-label="Taslak menüsü">
            <Menu size={16} strokeWidth={1.75} />
          </Button>
        </div>
      </div>

      {/* Çöz reddedildiyse (yayında, başka koşu sürüyor) sunucunun cümlesi. */}
      {coz.isError && (
        <p className="px-6 pb-2 text-danger" style={{ fontSize: "var(--text-xs)" }} role="alert">
          {sunucuAciklamasi(coz.error) ?? "Çözüm başlatılamadı."}
        </p>
      )}

      {calisiyor && !coz.isError ? (
        <div className="rounded-lg border bg-card p-6">
          <p className="text-muted-foreground">Çözülüyor — Taslaklar ekranına dönülüyor…</p>
        </div>
      ) : hata ? (
        <HataKutusu hata={hata} onTekrar={() => tazele()} kisa />
      ) : isLoading || !cizelge ? (
        <div className="rounded-lg border bg-card p-6">
          <p className="text-muted-foreground">Yükleniyor…</p>
        </div>
      ) : (
        <>
          <Izgara data={cizelge} draftId={draftId} onDegisti={tazele} detaylar={detaylar} />

          {/* Alt bar: GÖRÜNEN dönemin toplamları. Sağda detay anahtarı. */}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-1 px-1">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
              <Ozet etiket="Toplam saat" deger={`${sayi(cizelge.summary.total_hours)} sa`} />
              <Ozet etiket="Toplam gece" deger={String(cizelge.summary.total_nights ?? 0)} />
              <Ozet etiket="Eksik vardiya" deger={String(cizelge.summary.shortfall_count)}
                    vurgu={cizelge.summary.shortfall_count > 0} />
            </div>
            <DetayDugmesi />
          </div>

          {(cizelge.notes ?? []).length > 0 && (
            <div className="mt-2 px-1">
              {(cizelge.notes ?? []).map((n) => (
                <p key={n} className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  {n}
                </p>
              ))}
            </div>
          )}
        </>
      )}

      {taslak && (
        <TaslakPaneli acik={panel} onKapat={() => setPanel(false)} taslak={taslak} />
      )}
    </AppShell>
  );
}

function Ozet({ etiket, deger, vurgu }: { etiket: string; deger: string; vurgu?: boolean }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>{etiket}</span>
      <span className={vurgu ? "font-semibold text-danger" : "font-medium"}>{deger}</span>
    </span>
  );
}
