"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ApiError, deleteFood } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import { useSessionAbortSignal } from "./SessionQueryProvider";

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
  const sessionSignal = useSessionAbortSignal();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (foodId: string) => deleteFood(foodId, accessToken, sessionSignal),
    onSuccess: async () => {
      if (sessionSignal.aborted) return;
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["foods"] }),
        queryClient.invalidateQueries({ queryKey: ["food"] }),
        queryClient.invalidateQueries({ queryKey: ["diary-food-picker"] }),
        queryClient.invalidateQueries({ queryKey: ["entries"] }),
        queryClient.invalidateQueries({ queryKey: ["week"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-user"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-user-diary"] })
      ]);
      if (sessionSignal.aborted) return;
      onDeleted?.();
    },
    onError: (error) => {
      if (sessionSignal.aborted) return;
      if (error instanceof ApiError && error.status === 404) {
        onError?.("لم يتم العثور على الطعام. حدّث القائمة وحاول مرة أخرى.");
      } else {
        onError?.(WRITE_ERROR);
      }
    }
  });
}
