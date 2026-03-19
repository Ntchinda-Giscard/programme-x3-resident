
import { create } from "zustand";

export interface Message {
  role: "user" | "assistant";
  content: string;
  conversation_id?: string;
}

interface ChatStore {
  messages: Message[];
  conversationId: string | null;
  isLoading: boolean;
  addMessage: (message: Message) => void;
  setConversationId: (id: string) => void;
  sendMessage: (query: string, apiUrl: string) => Promise<void>;
  clearChat: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  conversationId: null,
  isLoading: false,
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setConversationId: (id) => set({ conversationId: id }),
  clearChat: () => set({ messages: [], conversationId: null }),
  sendMessage: async (query, apiUrl) => {
    const { conversationId } = get();
    
    // Add user message immediately
    set((state) => ({ 
      messages: [...state.messages, { role: "user", content: query }],
      isLoading: true 
    }));

    try {
      const response = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) throw new Error("Erreur lors de l'envoi du message");

      const data = await response.json();
      
      set((state) => ({
        messages: [...state.messages, { role: "assistant", content: data.response }],
        conversationId: data.conversation_id,
        isLoading: false
      }));
    } catch (error) {
      console.error("Chat error:", error);
      set({ isLoading: false });
      set((state) => ({
        messages: [...state.messages, { role: "assistant", content: "⚠️ Désolé, une erreur est survenue lors de la communication avec l'assistant." }]
      }));
    }
  },
}));
