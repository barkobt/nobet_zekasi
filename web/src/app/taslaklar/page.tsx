"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarCheck, Copy, Loader2, Trash2 } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { HataKutusu } from "@/components/HataKutusu";
import { YeniTaslak } from "@/components/taslak/YeniTaslak";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { UygulaPenceresi } from "@/components/taslak/UygulaPenceresi";
import { api } from "@/lib/api";
import { aralikEtiketi, type Draft } from "@/lib/taslak";
import { AY_KISA } from "@/lib/donem";

/** Durum rozeti: taslağın gerçekte ne olduğunu tek kelimeyle söyler. */
function durumRozeti(t: Draft): { ad: string; vurgu?: boolean; suruyor?: boolean } {
  if (t.last_run?.status === "CALISIYOR") return { ad: "Çözülüyor", suruyor: true };
  if (t.status === "yayinlandi") return { ad: "Yayınlandı" };
  if (t.status === "arsiv") return { ad: "Arşiv" };
  if (t.last_run?.is_reference_copy) return { ad: "Referans kopya" };
  if (t.last_run?.status === "INFEASIBLE") return { ad: "Çözülemedi", vurgu: true };
  if (t.last_run) return { ad: "Çözüldü" };
  return { ad: "Taslak" };
}

/** Sekmeler: son güncellenme zamanına göre. Arşiv ayrı sekme DEĞİL — arşivlenmiş
 *  taslak hangi zaman aralığındaysa orada, "Arşiv" rozetiyle görünür. */
const SEKMELER = [
  { anahtar: "7",   ad: "Son 7 gün",  gun: 7 },
  { anahtar: "30",  ad: "Son 30 gün", gun: 30 },
  { anahtar: "eski", ad: "Eski",      gun: null },
] as const;

const SAYFA_BOYU = 10;

const gunFarki = (iso: string | null | undefined) =>
  iso === null || iso === undefined
    ? Number.POSITIVE_INFINITY
    : (Date.now() - +new Date(iso)) / 86400000;

const kisaTarih = (iso: string | null | undefined) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.getDate()} ${AY_KISA[d.getMonth()]} ${d.getFullYear()}`;
};

export default function TaslaklarSayfasi() {
  const router = useRouter();
  const qc = useQueryClient();
  const [silinecek, setSilinecek] = useState<Draft | null>(null);
  const [uygulanacak, setUygulanacak] = useState<Draft | null>(null);
  const [sekme, setSekme] = useState<string>("7");
  const [sayfa, setSayfa] = useState(0);

  // Süren bir çözüm varsa liste kendini yeniler: rozet "Çözülüyor"dan sonuca
  // kendiliğinden geçer, sayfayı yenilemek gerekmez (01.10).
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["drafts"], queryFn: () => api<Draft[]>("/drafts"),
    refetchInterval: (q) =>
      q.state.data?.some((t) => t.last_run?.status === "CALISIYOR") ? 2000 : false,
  });

  // Bir koşu bittiğinde o taslağa ait öteki ekranlar (ızgara, rapor, teşhis) da
  // eskir; liste sonucu gösterdiği anda onlar da tazelenir.
  const [surenler, setSurenler] = useState<string>("");
  const simdiSurenler = (data ?? [])
    .filter((t) => t.last_run?.status === "CALISIYOR")
    .map((t) => t.id)
    .join(",");
  if (simdiSurenler !== surenler) {
    if (surenler) {
      const biten = surenler.split(",").filter((id) => !simdiSurenler.split(",").includes(id));
      if (biten.length) qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "drafts" });
    }
    setSurenler(simdiSurenler);
  }

  const sil = useMutation({
    mutationFn: (id: number) => api<void>(`/drafts/${id}`, { method: "DELETE" }),
    onSuccess: (_bos, id) => {
      // Satır beklemeden düşsün; ardından liste sunucudan tazelenir.
      qc.setQueryData<Draft[]>(["drafts"], (eski) => eski?.filter((t) => t.id !== id));
      qc.invalidateQueries({ queryKey: ["drafts"] });
      setSilinecek(null);
    },
  });

  const kopyala = useMutation({
    mutationFn: (t: Draft) =>
      api<Draft>(`/drafts/${t.id}/copy`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ name: `${t.name} (kopya)` }),
      }),
    onSuccess: (yeni) => {
      qc.invalidateQueries({ queryKey: ["drafts"] });
      router.push(`/taslaklar/${yeni.id}`);
    },
  });

  // Sekmeye düşen taslaklar, en yeni üstte.
  const tumu = (data ?? []).slice().sort(
    (a, b) => gunFarki(a.updated_at) - gunFarki(b.updated_at),
  );
  const sekmeninleri = (anahtar: string) => {
    const s2 = SEKMELER.find((x) => x.anahtar === anahtar)!;
    return s2.gun === null
      ? tumu.filter((t) => gunFarki(t.updated_at) > 30)
      : tumu.filter((t) => gunFarki(t.updated_at) <= s2.gun!);
  };
  const secili = sekmeninleri(sekme);
  const eski = sekme === "eski";
  const sayfaSayisi = Math.max(1, Math.ceil(secili.length / SAYFA_BOYU));
  const gorunen = eski
    ? secili.slice(sayfa * SAYFA_BOYU, (sayfa + 1) * SAYFA_BOYU)
    : secili;

  // Bilgi satırı: bu sekmedeki taslakların güncellenme aralığı.
  const tarihler = secili.map((t) => t.updated_at).filter(Boolean) as string[];
  const bilgi = tarihler.length
    ? `Güncellenme: ${kisaTarih(tarihler[tarihler.length - 1])} – ${kisaTarih(tarihler[0])}`
    : "Bu aralıkta taslak yok.";

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Taslaklar</h1>
        <YeniTaslak />
      </div>

      <div className="mb-1 flex items-center gap-1 border-b">
        {SEKMELER.map((x) => (
          <button
            key={x.anahtar}
            type="button"
            onClick={() => { setSekme(x.anahtar); setSayfa(0); }}
            className={
              "-mb-px border-b-2 px-3 pb-2 pt-1 " +
              (sekme === x.anahtar
                ? "border-brand font-medium"
                : "border-transparent text-muted-foreground hover:text-foreground")
            }
          >
            {x.ad}
            <span className="ml-1.5 opacity-60" style={{ fontSize: "var(--text-xs)" }}>
              {sekmeninleri(x.anahtar).length}
            </span>
          </button>
        ))}
      </div>
      <p className="mb-3 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        {bilgi}
      </p>

      <div className="rounded-lg border bg-card">
        {error ? (
          <HataKutusu hata={error} onTekrar={() => refetch()} kisa />
        ) : isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : !data?.length ? (
          <div className="flex flex-col items-center gap-3 p-10">
            <p className="text-muted-foreground">Henüz taslak yok.</p>
            <YeniTaslak />
          </div>
        ) : gorunen.length === 0 ? (
          <p className="p-6 text-muted-foreground">Bu aralıkta taslak yok.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[300px]">Taslak</TableHead>
                <TableHead className="w-[230px]">Dönem</TableHead>
                <TableHead className="w-[140px]">Durum</TableHead>
                <TableHead className="w-[150px]">Son güncelleme</TableHead>
                <TableHead className="w-[130px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {gorunen.map((t) => {
                const rozet = durumRozeti(t);
                return (
                  <TableRow
                    key={t.id}
                    className="h-11 cursor-pointer"
                    onClick={() => router.push(`/taslaklar/${t.id}`)}
                    tabIndex={0}
                    onKeyDown={(e) => e.key === "Enter" && router.push(`/taslaklar/${t.id}`)}
                  >
                    <TableCell className="font-medium">{t.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {aralikEtiketi(t.period_start, t.period_end)}
                      <span className="ml-1.5 opacity-60" style={{ fontSize: "var(--text-xs)" }}>
                        {t.day_count} gün
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={"h-5 gap-1 rounded-sm px-1.5 font-normal " + (rozet.vurgu ? "text-danger" : "")}
                        style={{ fontSize: "var(--text-xs)" }}
                      >
                        {rozet.suruyor && (
                          <Loader2 size={12} strokeWidth={1.75} className="animate-spin" />
                        )}
                        {rozet.ad}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {kisaTarih(t.updated_at)}
                    </TableCell>

                    {/* Üç ikon: menüyü açmadan tek tıkla. Yayındaki çizelge silinemez. */}
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-0.5">
                        <IkonDugme
                          etiket="Kopyala"
                          onTikla={() => kopyala.mutate(t)}
                          bekliyor={kopyala.isPending}
                        >
                          <Copy size={16} strokeWidth={1.75} />
                        </IkonDugme>

                        <IkonDugme
                          etiket={t.status === "yayinlandi" ? "Zaten yayında" : "Yayınla"}
                          onTikla={() => setUygulanacak(t)}
                          pasif={t.status === "yayinlandi"}
                        >
                          <CalendarCheck size={16} strokeWidth={1.75} />
                        </IkonDugme>

                        <IkonDugme
                          etiket={
                            t.status === "yayinlandi"
                              ? "Yayındaki çizelge silinemez"
                              : "Sil"
                          }
                          onTikla={() => setSilinecek(t)}
                          pasif={t.status === "yayinlandi"}
                          tehlike
                        >
                          <Trash2 size={16} strokeWidth={1.75} />
                        </IkonDugme>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>

      {eski && sayfaSayisi > 1 && (
        <div className="mt-3 flex items-center justify-end gap-2">
          <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
            Sayfa {sayfa + 1} / {sayfaSayisi}
          </span>
          <Button variant="outline" size="sm" disabled={sayfa === 0}
                  onClick={() => setSayfa((p) => p - 1)}>
            Önceki
          </Button>
          <Button variant="outline" size="sm" disabled={sayfa + 1 >= sayfaSayisi}
                  onClick={() => setSayfa((p) => p + 1)}>
            Sonraki
          </Button>
        </div>
      )}

      {uygulanacak && (
        <UygulaPenceresi
          taslak={uygulanacak}
          acik
          onKapat={() => setUygulanacak(null)}
        />
      )}

      <AlertDialog open={silinecek !== null} onOpenChange={(a) => !a && setSilinecek(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontSize: "var(--text-base)" }}>
              {silinecek?.name} silinsin mi?
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontSize: "var(--text-xs)" }}>
              Taslağın {silinecek?.assignment_count} ataması ve çalıştırma geçmişi de
              silinecek. Geri alınamaz.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Vazgeç</AlertDialogCancel>
            <AlertDialogAction onClick={() => silinecek && sil.mutate(silinecek.id)}>
              Sil
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}

/** Satır sonundaki ikon düğme: tooltip'li, pasifken de tooltip açılır. */
function IkonDugme({
  etiket, onTikla, pasif, tehlike, bekliyor, children,
}: {
  etiket: string;
  onTikla: () => void;
  pasif?: boolean;
  tehlike?: boolean;
  bekliyor?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {/* Pasif düğme tooltip tetiklemez; sarmalayıcı span o yüzden burada. */}
        <span className="inline-flex">
          <Button
            variant="ghost"
            size="icon"
            aria-label={etiket}
            disabled={pasif || bekliyor}
            onClick={onTikla}
            className={tehlike && !pasif ? "text-danger hover:text-danger" : ""}
          >
            {children}
          </Button>
        </span>
      </TooltipTrigger>
      <TooltipContent>{etiket}</TooltipContent>
    </Tooltip>
  );
}
