"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ApiError, deleteFood } from "@/lib/api";
import { useAuth } from "./AuthProvider";

const WRITE_ERROR = "تعذر الاتصال بالخادم. لم يتم حفظ التغييرات.";

export function useFoodDelete({
  onDeleted,
  onError
}: {
  onDeleted?: () => void;
  onError?: (message: string) => void;
}) {
  const { session } = useAuth();
  const accessToken = session?.access_token;
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (foodId: string) => deleteFood(foodId, accessToken),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["foods"] });
      onDeleted?.();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 404) {
        onError?.("لم يتم العثور على الطعام. حدّث القائمة وحاول مرة أخرى.");
      } else {
        onError?.(WRITE_ERROR);
      }
    }
  });
}
