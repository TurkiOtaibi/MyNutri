import { FoodFormPage } from "@/components/FoodFormPage";

export const metadata = { title: "إضافة طعام | myNutri" };

export default function Page() {
  return <FoodFormPage mode="create" />;
}
