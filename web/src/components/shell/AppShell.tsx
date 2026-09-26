"use client";

import { useEffect, useState } from "react";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

const ANAHTAR = "asp.menu.sabit";

/** DESIGN §4: kabuk tüm ekranlarda sabit. İçerik alanı --bg, 24px iç boşluk. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [sabit, setSabit] = useState(false);
  const [hover, setHover] = useState(false);

  // Sabitleme tercihi tarayıcıda hatırlanır. localStorage gizli pencerede
  // veya site verisi kapalıyken hata atabilir; sessizce varsayılana düşüyoruz.
  useEffect(() => {
    try {
      setSabit(localStorage.getItem(ANAHTAR) === "1");
    } catch {
      /* tercih okunamadı, varsayılan: daraltılmış */
    }
  }, []);

  const sabitDegistir = () => {
    setSabit((v) => {
      try {
        localStorage.setItem(ANAHTAR, v ? "0" : "1");
      } catch {
        /* yazılamadı, yalnız bu oturum için geçerli */
      }
      return !v;
    });
  };

  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar acik={sabit || hover} sabit={sabit} onHover={setHover} onSabit={sabitDegistir} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-auto bg-background p-6">{children}</main>
      </div>
    </div>
  );
}
