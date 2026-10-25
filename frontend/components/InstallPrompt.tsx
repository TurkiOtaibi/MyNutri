"use client";

import { Download } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

function isStandalone() {
  return window.matchMedia("(display-mode: standalone)").matches ||
    Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
}

function subscribeDisplayMode(onChange: () => void) {
  const media = window.matchMedia("(display-mode: standalone)");
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

export function InstallPrompt() {
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const showIPhoneHelp = useSyncExternalStore(subscribeDisplayMode,
    () => /iPhone/i.test(navigator.userAgent) && !isStandalone(), () => false);

  useEffect(() => {
    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      if (!isStandalone()) setPromptEvent(event as BeforeInstallPromptEvent);
    };
    const onInstalled = () => { setPromptEvent(null); setInstalled(true); };

    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (installed) return null;
  if (showIPhoneHelp) return <p className="install-prompt install-help" role="note">
    {'لتثبيت النظام: اضغط زر المشاركة، ثم "إضافة إلى الشاشة الرئيسية".'}
  </p>;
  if (!promptEvent) {
    return null;
  }

  async function install() {
    if (!promptEvent) return;
    await promptEvent.prompt();
    await promptEvent.userChoice;
    setPromptEvent(null);
  }

  return (
    <button className="install-prompt btn primary" type="button" onClick={install}>
      <Download size={17} />
      تثبيت التطبيق
    </button>
  );
}
