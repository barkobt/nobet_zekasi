import { redirect } from "next/navigation";

/** DESIGN §6: uygulama doğrudan E-09 ile açılır; dashboard yok. */
export default function Home() {
  redirect("/cizelge");
}
