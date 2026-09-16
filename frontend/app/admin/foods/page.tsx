import { permanentRedirect } from "next/navigation";

export default function AdminFoodsPage() {
  permanentRedirect("/foods");
}
