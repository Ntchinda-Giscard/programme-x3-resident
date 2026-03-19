"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { FieldPairComponent } from "@/components/field-pair";
import { useFormStore } from "@/lib/email-site";
import { validateFieldPair } from "@/lib/validation";
import { useToast } from "@/hooks/use-toast";

export default function SiteEmailConfig() {
  const {
    fields,
    addFieldPair,
    removeFieldPair,
    updateFieldPair,
    resetForm,
    setFields,
    isLoading,
    setIsLoading,
  } = useFormStore();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    // Validate all field pairs
    const validationErrors: Record<string, Record<string, string>> = {};
    let isFormValid = true;

    fields.forEach((field) => {
      const { isValid, errors } = validateFieldPair(
        field.site,
        field.email_address,
      );
      if (!isValid) {
        validationErrors[field.id] = errors;
        isFormValid = false;
      }
    });

    if (!isFormValid) {
      toast({
        title: "Erreur de validation",
        description:
          "Veuillez vérifier tous les champs et corriger les erreurs.",
        variant: "destructive",
      });
      return;
    }

    const payload = fields.map((field) => ({
      site: field.site,
      email_address: field.email_address,
    }));

    setIsSubmitting(true);
    try {
      // const response = await fetch("http://localhost:5001/config/add/address", {
      //   method: "POST",
      //   headers: {
      //     "Content-Type": "application/json",
      //   },
      //   body: JSON.stringify(payload),
      // });

      // if (!response.ok) {
      //   throw new Error("Failed to register");
      // }

      await submitFormData(payload);
      const result = await fetchInitialConfig();

      if (result.success && Array.isArray(result.data)) {
        const newFields = result.data.map((item: any, index: number) => ({
          id: (index + 1).toString(),
          site: item.site,
          email_address: item.email_address,
        }));
        setFields(newFields);
      }

      toast({
        title: "Succès!",
        description: "Vos données ont été enregistrées avec succès.",
        variant: "default",
      });
    } catch (error) {
      console.error("Error:", error);
      toast({
        title: "Erreur",
        description: "Échec de l'enregistrement. Veuillez réessayer.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    const fetchInitialData = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(
          "http://localhost:8005/config/get/address",
        );
        if (!response.ok) {
          throw new Error("Failed to fetch initial data");
        }
        const data = await response.json();

        if (Array.isArray(data) && data.length > 0) {
          const initialFields = data.map((item: any, index: number) => ({
            id: (index + 1).toString(),
            site: item.site,
            email_address: item.email_address,
          }));
          setFields(initialFields);
        }
      } catch (error) {
        console.error("Error fetching initial data:", error);
        toast({
          title: "Erreur",
          description: "Impossible de charger les données initiales.",
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchInitialData();
  }, []);

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-2xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-foreground mb-2">
              Enregistrement Site & Email
            </h1>
            <p className="text-muted-foreground">
              Ajoutez plusieurs paires site et adresse email pour vous
              enregistrer
            </p>
          </div>

          {/* Form Container */}
          <div className="space-y-6">
            {/* Field Pairs List */}
            <div className="space-y-4">
              {fields.map((field, index) => (
                <FieldPairComponent
                  key={field.id}
                  pair={field}
                  onUpdate={updateFieldPair}
                  onRemove={removeFieldPair}
                  isMultiple={fields.length > 1}
                />
              ))}
            </div>

            {/* Add Button */}
            <Button
              onClick={addFieldPair}
              variant="outline"
              className="w-full bg-transparent"
            >
              <Plus className="w-4 h-4 mr-2" />
              Ajouter une paire
            </Button>

            {/* Register Button */}
            <Button
              onClick={handleSubmit}
              disabled={isLoading}
              className="w-full"
              size="lg"
            >
              {isLoading ? "Enregistrement..." : "Enregistrer"}
            </Button>
          </div>
        </div>
      </div>
    </main>
  );
}

export async function fetchInitialConfig() {
  try {
    const response = await fetch("http://localhost:8005/config/get/address", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("[v0] Server fetch error:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

export async function submitFormData(
  payload: Array<{ site: string; email_address: string }>,
) {
  try {
    const response = await fetch("http://localhost:8005/config/add/address", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return { success: true };
  } catch (error) {
    console.error("[v0] Server submit error:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

export async function deleteAddress(site: string) {
  try {
    const response = await fetch(
      `http://localhost:8005/config/delete/address/${site}`,
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return { success: true };
  } catch (error) {
    console.error("[v0] Server delete error:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

// smtp.gmail.com;
// txdp zcoh ucum ezxt
// ntchinda1998 @gmail.com
// giscardntchinda @gmail.com
// 587
