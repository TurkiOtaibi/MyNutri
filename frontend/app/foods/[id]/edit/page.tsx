import { FoodFormPage } from "@/components/FoodFormPage";

type PageProps = {
  params: Promise<{ id: string }>;
};

export const metadata = { title: "تعديل الطعام | myNutri" };

export default async function Page({ params }: PageProps) {
  const { id } = await params;
  return <FoodFormPage mode="edit" foodId={id} />;
}
