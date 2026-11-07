import { Suspense } from "react";
import { AuthShell } from "@/components/AuthShell";

export const metadata = { title: "تسجيل الدخول | myNutri" };

export default function LoginPage() {
  return <Suspense><AuthShell /></Suspense>;
}
