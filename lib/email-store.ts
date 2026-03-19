import { create } from "zustand";

export interface EmailConfig {
  smtpServer: string;
  smtpPort: number;
  senderEmail: string;
  receiverEmail: string;
  senderPassword: string;
  useSSL: boolean;
  useTLS: boolean;
  timeout?: number;
  retryAttempts?: number;
  subject?: string;
  message?: string;
}

interface AppState {
  externalApiUrl: string;
  emailConfig: EmailConfig;
  setEmailConfig: (config: Partial<EmailConfig>) => void;
  saveSMTPConfig: (config: Partial<EmailConfig>) => Promise<void>;
  fetchEmailConfig: () => Promise<void>;
}

export const useSMTPStore = create<AppState>((set, get) => ({
  externalApiUrl:
    process.env.NEXT_PUBLIC_EXTERNAL_API_URL || "http://127.0.0.1:8005",
  emailConfig: {
    smtpServer: "",
    smtpPort: 0,
    senderEmail: "",
    receiverEmail: "",
    senderPassword: "",
    useSSL: false,
    useTLS: false,
  },
  setEmailConfig: async (config) => {
    set((state) => ({
      emailConfig: { ...state.emailConfig, ...config },
    }));
  },
  saveSMTPConfig: async (config) => {
    const { externalApiUrl } = get();
    try {
      const response = await fetch(`${externalApiUrl}/email/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          smtpServer: config.smtpServer,
          smtpPort: config.smtpPort,
          senderEmail: config.senderEmail,
          receiverEmail: config.receiverEmail,
          senderPassword: config.senderPassword,
          useSSL: config.useSSL,
          useTLS: config.useTLS,
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
  fetchEmailConfig: async () => {
    const { externalApiUrl } = get();
    try {
      const response = await fetch(`${externalApiUrl}/email/get`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();
      console.log("data", data);
      console.log("response", response);
      if (response.ok && data) {
        set({
          emailConfig: {
            smtpServer: data.smtpServer || "",
            smtpPort: data.smtpPort || 0,
            senderEmail: data.senderEmail || "",
            receiverEmail: data.receiverEmail || "",
            senderPassword: data.senderPassword || "",
            useSSL: data.useSSL || false,
            useTLS: data.useTLS || false,
          },
        });
      } else {
        throw new Error(
          data.detail || "Erreur lors de la récupération des paramètres"
        );
      }
    } catch (error) {
      console.error("Error fetching email settings:", error);
      throw error;
    }
  },
}));
