"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FolderOpen } from "lucide-react";
import { useEffect, useState } from "react";

interface FolderPickerProps {
  value: string;
  onChange: (path: string) => void;
  placeholder?: string;
}

declare global {
  interface Window {
    electronAPI?: any;
  }
}

export function FolderPicker({
  value,
  onChange,
  placeholder = "Sélectionner un dossier...",
}: FolderPickerProps) {
  const [isElectronAvailable, setIsElectronAvailable] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.electronAPI) {
      setIsElectronAvailable(true);
      console.log("Frontend: Electron API is available");
    } else {
      setIsElectronAvailable(false);
      console.log("Frontend: Running in web browser mode");
    }
  }, []);

  const handleBrowse = async () => {
    // In a real desktop app (Electron/Tauri), this would open a native folder picker
    // For demonstration, we'll use a prompt
    console.log("Opening folder selector");
    if (!isElectronAvailable) {
      alert("Folder picker is only available in the desktop app");
      return;
    }
    try {
      const selectedFolder = await window.electronAPI.selectFolder();
      console.log("Selected folder", selectedFolder);
      if (selectedFolder) {
        onChange(selectedFolder);
      }
    } catch (e) {
      console.error("Erreur lors de l'ouverture du sélecteur de dossier :", e);
    }
  };

  return (
    <div className="flex gap-2">
      <Input
        type="text"
        value={value}
        placeholder={placeholder}
        className="flex-1 font-mono text-sm"
        readOnly
      />
      <Button
        type="button"
        variant="outline"
        onClick={handleBrowse}
        className="shrink-0 bg-transparent"
      >
        <FolderOpen className="mr-2 h-4 w-4" />
        Parcourir
      </Button>
    </div>
  );
}
