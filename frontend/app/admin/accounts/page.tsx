import { redirect } from "next/navigation";

// Account management is merged into the single Users list.
export default function AdminAccountsRoute() { redirect("/admin/users"); }
