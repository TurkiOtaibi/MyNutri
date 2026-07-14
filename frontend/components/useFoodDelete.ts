"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ApiError, deleteFood } from "@/lib/api";

const WRITE_ERROR = "تعذر الاتصال بالخادم. لم يتم حفظ التغييرات.";

export function useFoodDelete({
  onDeleted,
  onError
}: {
  onDeleted?: () => void;
  onError?: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteFood,
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
