import { create } from "zustand";

interface FolderSettings {
  inputFolder: string;
  outputFolder: string;
}

type ServiceStatus = "stopped" | "running" | "installing" | "error";

interface FolderStore extends FolderSettings {
  serviceStatus: ServiceStatus;
  externalApiUrl: string;
  setExternalApiUrl: (url: string) => void;
  setInputFolder: (path: string) => void;
  setOutputFolder: (path: string) => void;
  saveSettings: () => Promise<void>;
  startService: () => Promise<void>;
  stopService: () => Promise<void>;
  installService: () => Promise<void>;
  restartService: () => Promise<void>;
  resetService: () => Promise<void>;
  getServiceStatus: () => Promise<void>;
  fetchFolderSettings: () => Promise<void>;
}

export const useFolderStore = create<FolderStore>()((set, get) => ({
  inputFolder: "",
  outputFolder: "",
  serviceStatus: "stopped",
  externalApiUrl:
    process.env.NEXT_PUBLIC_EXTERNAL_API_URL || "http://127.0.0.1:8005",
  setExternalApiUrl: (url) => set({ externalApiUrl: url }),
  setInputFolder: (path) => set({ inputFolder: path }),
  setOutputFolder: (path) => set({ outputFolder: path }),
  fetchFolderSettings: async () => {
    const { externalApiUrl } = get();
    try {
      const response = await fetch(`${externalApiUrl}/config/get`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();
      console.log("data", data);
      console.log("response", response);
      if (response.ok && data) {
        set({
          inputFolder: data.source || "",
          outputFolder: data.destination || "",
        });
      } else {
        throw new Error(
          data.detail || "Erreur lors de la récupération des paramètres",
        );
      }
    } catch (error) {
      console.error("Error fetching folder settings:", error);
      throw error;
    }
  },
  saveSettings: async () => {
    const { externalApiUrl, inputFolder, outputFolder } = get();
    if (!inputFolder || !outputFolder) {
      // missing folders — nothing to do
      throw new Error("Veuillez remplir tous les chemins de dossiers.");
    }

    try {
      const response = await fetch(`${externalApiUrl}/config/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: inputFolder,
          destination: outputFolder,
        }),
      });
      const data = await response.json();
      console.log("data", data);
      console.log("response", response);
    } catch (error) {
      console.error("Error saving settings:", error);
      throw error;
    }
  },
  getServiceStatus: async () => {
    const { externalApiUrl } = get();

    try {
      const response = await fetch(`${externalApiUrl}/service/status`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();
      console.log("data", data);
      console.log("response", response);
      if (response.ok && data) {
        set({ serviceStatus: "running" });
      } else {
        set({ serviceStatus: "error" });
        throw new Error(data.detail || "Erreur lors du démarrage");
      }
    } catch (error) {
      console.error("Error saving settings:", error);
      throw error;
    }
  },
  startService: async () => {
    const { externalApiUrl, inputFolder, outputFolder } = get();
    try {
      set({ serviceStatus: "running" });
      const response = await fetch(`${externalApiUrl}/service/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();
      console.log("data", data);
      console.log("response", response);

      if (response.ok && data) {
        set({ serviceStatus: "running" });
      } else {
        set({ serviceStatus: "error" });
        throw new Error(data.detail || "Erreur lors du démarrage");
      }
    } catch (error) {
      set({ serviceStatus: "error" });
      console.error("Error starting service:", error);
      throw error;
    }
  },
  stopService: async () => {
    const { externalApiUrl } = get();
    try {
      const response = await fetch(`${externalApiUrl}/service/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();

      if (response.ok && data) {
        set({ serviceStatus: "stopped" });
      } else {
        set({ serviceStatus: "error" });
        throw new Error(data.detail || "Erreur lors de l'arrêt");
      }
    } catch (error) {
      set({ serviceStatus: "error" });
      throw error;
    }
  },
  installService: async () => {
    const { externalApiUrl, inputFolder, outputFolder } = get();
    try {
      set({ serviceStatus: "installing" });
      const response = await fetch(`${externalApiUrl}/service/install`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();

      if (response.ok && data) {
        set({ serviceStatus: "stopped" });
      } else {
        set({ serviceStatus: "error" });
        throw new Error(data.detail || "Erreur lors de l'installation");
      }
    } catch (error) {
      set({ serviceStatus: "error" });
      throw error;
    }
  },
  restartService: async () => {
    const { externalApiUrl, inputFolder, outputFolder } = get();
    try {
      set({ serviceStatus: "stopped" });
      const response = await fetch(`${externalApiUrl}/service/restart`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();

      if (response.ok && data) {
        set({ serviceStatus: "running" });
      } else {
        set({ serviceStatus: "error" });
        throw new Error(data.detail || "Erreur lors du redémarrage");
      }
    } catch (error) {
      set({ serviceStatus: "error" });
      throw error;
    }
  },
  resetService: async () => {
    const { externalApiUrl } = get();
    try {
      set({ serviceStatus: "installing" }); // Show as installing/busy
      const response = await fetch(`${externalApiUrl}/service/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();

      if (response.ok && data) {
        set({ serviceStatus: "stopped" });
      } else {
        set({ serviceStatus: "error" });
        throw new Error(data.detail || "Erreur lors de la réinitialisation");
      }
    } catch (error) {
      set({ serviceStatus: "error" });
      throw error;
    }
  },
}));
