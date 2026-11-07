import { FoodDetailsPage } from "@/components/FoodDetailsPage";

type PageProps = {
  params: Promise<{ id: string }>;
};

export const metadata = { title: "تفاصيل الطعام | myNutri" };

export default async function Page({ params }: PageProps) {
  const { id } = await params;
  return <FoodDetailsPage foodId={id} />;
}
