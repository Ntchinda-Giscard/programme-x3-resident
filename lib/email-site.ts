import { create } from "zustand";

export type FieldPair = {
  id: string;
  site: string;
  email_address: string;
};

type FormStore = {
  fields: FieldPair[];
  addFieldPair: () => void;
  removeFieldPair: (id: string) => void;
  updateFieldPair: (id: string, updates: Partial<FieldPair>) => void;
  setFields: (fields: FieldPair[]) => void;
  resetForm: () => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
};

export const useFormStore = create<FormStore>((set) => ({
  fields: [{ id: "1", site: "", email_address: "" }],
  isLoading: false,

  addFieldPair: () =>
    set((state) => ({
      fields: [
        ...state.fields,
        {
          id: Date.now().toString(),
          site: "",
          email_address: "",
        },
      ],
    })),

  removeFieldPair: (id: string) =>
    set((state) => ({
      fields: state.fields.filter((field) => field.id !== id),
    })),

  updateFieldPair: (id: string, updates: Partial<FieldPair>) =>
    set((state) => ({
      fields: state.fields.map((field) =>
        field.id === id ? { ...field, ...updates } : field
      ),
    })),

  setFields: (fields: FieldPair[]) => set({ fields }),

  resetForm: () => set({ fields: [{ id: "1", site: "", email_address: "" }] }),

  setIsLoading: (loading: boolean) => set({ isLoading: loading }),
}));
