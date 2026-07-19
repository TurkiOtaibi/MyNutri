import { Suspense } from "react";
import { AuthShell } from "@/components/AuthShell";

export default function LoginPage() {
  return <Suspense><AuthShell mode="login" /></Suspense>;
}
