"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { AY_ADI, type Draft } from "@/lib/taslak";

/** Sonraki ayın ilk günü — yeni taslak için makul varsayılan. */
function sonrakiAy() {
  const d = new Date();
  return new Date(Date.UTC(d.getFullYear(), d.getMonth() + 1, 1));
}

export function YeniTaslak() {
  const [acik, setAcik] = useState(false);
  const varsayilan = sonrakiAy();
  const [ay, setAy] = useState(varsayilan.toISOString().slice(0, 7));
  const [ad, setAd] = useState(
    `${AY_ADI[varsayilan.getUTCMonth()]} ${varsayilan.getUTCFullYear()} çizelgesi`,
  );
  const qc = useQueryClient();

  const olustur = useMutation({
    mutationFn: () =>
      api<Draft>("/drafts", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ month_start: `${ay}-01`, name: ad }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["drafts"] });
      setAcik(false);
    },
  });

  return (
    <Dialog open={acik} onOpenChange={setAcik}>
      <DialogTrigger asChild>
        <Button>
          <Plus size={16} strokeWidth={1.75} />
          Yeni taslak
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[380px]">
        <DialogHeader>
          <DialogTitle style={{ fontSize: "var(--text-base)" }}>Yeni taslak</DialogTitle>
        </DialogHeader>

        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="ay" style={{ fontSize: "var(--text-xs)" }}>Ay</Label>
            <Input id="ay" type="month" value={ay} onChange={(e) => setAy(e.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="ad" style={{ fontSize: "var(--text-xs)" }}>Ad</Label>
            <Input id="ad" value={ad} onChange={(e) => setAd(e.target.value)} />
          </div>
          {olustur.isError && (
            <p className="text-danger" style={{ fontSize: "var(--text-xs)" }}>
              Taslak oluşturulamadı.
            </p>
          )}
        </div>

        <DialogFooter>
          <Button onClick={() => olustur.mutate()} disabled={olustur.isPending || !ad.trim()}>
            {olustur.isPending ? "Oluşturuluyor…" : "Oluştur"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
