import { Suspense } from "react";
import { AdminUsersPage } from "@/components/AdminUsersPage";

export const metadata = { title: "إدارة المستخدمين | myNutri" };

export default function AdminUsersRoute() { return <Suspense><AdminUsersPage /></Suspense>; }
