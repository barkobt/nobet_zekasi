"use client";

import { useState } from "react";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

/** DESIGN §4: kabuk tüm ekranlarda sabit. İçerik alanı --bg, 24px iç boşluk. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-auto bg-background p-6">{children}</main>
      </div>
    </div>
  );
}
