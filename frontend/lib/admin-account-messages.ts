import { ApiError } from "./api";

export type AccountAction = "create" | "retry-create" | "edit" | "password" | "status" | "delete" | "retry-delete";

const failures: Record<AccountAction, string> = {
  create: "تعذر إكمال إنشاء المستخدم. أعد المحاولة.",
  "retry-create": "تعذر إكمال إنشاء المستخدم. أعد المحاولة.",
  edit: "تعذر حفظ تغييرات المستخدم. حاول مرة أخرى.",
  password: "تعذر إعادة تعيين كلمة المرور. حاول مرة أخرى.",
  status: "تعذر تحديث حالة المستخدم. حاول مرة أخرى.",
  delete: "تعذر إكمال حذف المستخدم. حسابه معطّل ويمكنك إعادة المحاولة.",
  "retry-delete": "تعذر إكمال حذف المستخدم. حسابه معطّل ويمكنك إعادة المحاولة.",
};

const successes: Record<AccountAction, string> = {
  create: "تم إنشاء المستخدم.",
  "retry-create": "تم إنشاء المستخدم.",
  edit: "تم حفظ تغييرات المستخدم.",
  password: "تمت إعادة تعيين كلمة المرور.",
  status: "تم تحديث حالة المستخدم.",
  delete: "تم حذف المستخدم نهائيًا.",
  "retry-delete": "تم حذف المستخدم نهائيًا.",
};

export function accountActionErrorMessage(error: unknown, action: AccountAction): string {
  if (error instanceof TypeError || (error instanceof ApiError && error.status === 0)) {
    return "تعذر الاتصال بالخادم. حاول مرة أخرى.";
  }
  if (error instanceof ApiError && error.code !== "CREATION_INCOMPLETE" && error.message !== failures.create && error.message && !error.message.startsWith("API request")) {
    return error.message;
  }
  return failures[action];
}

export function accountActionSuccessMessage(action: AccountAction): string {
  return successes[action];
}
