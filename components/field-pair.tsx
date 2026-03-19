"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import { validateFieldPair } from "@/lib/validation";
import { useToast } from "@/hooks/use-toast";
import type { FieldPair } from "@/lib/email-site";
import { deleteAddress } from "./site-email-config";

interface FieldPairProps {
  pair: FieldPair;
  onUpdate: (id: string, updates: Partial<FieldPair>) => void;
  onRemove: (id: string) => void;
  isMultiple: boolean;
}

export function FieldPairComponent({
  pair,
  onUpdate,
  onRemove,
  isMultiple,
}: FieldPairProps) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isDeleting, setIsDeleting] = useState(false);
  const { toast } = useToast();

  const handleSiteChange = (value: string) => {
    onUpdate(pair.id, { site: value });
    if (errors.site) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors.site;
        return newErrors;
      });
    }
  };

  const handleEmailChange = (value: string) => {
    onUpdate(pair.id, { email_address: value });
    if (errors.email_address) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors.email_address;
        return newErrors;
      });
    }
  };

  const validateOnBlur = (field: "site" | "email_address") => {
    const { isValid, errors: newErrors } = validateFieldPair(
      pair.site,
      pair.email_address
    );

    if (!isValid) {
      setErrors(newErrors);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    const result = await deleteAddress(pair.site);

    if (result.success) {
      toast({
        title: "Succès",
        description: `Le site "${pair.site}" a été supprimé.`,
        variant: "default",
      });
      onRemove(pair.id);
    } else {
      toast({
        title: "Erreur",
        description: "Impossible de supprimer ce site. Veuillez réessayer.",
        variant: "destructive",
      });
    }

    setIsDeleting(false);
  };

  return (
    <div className="flex flex-col gap-4 p-4 border border-border rounded-lg bg-card">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-foreground">Site</label>
          <Input
            placeholder="Entrez le nom du site"
            value={pair.site}
            onChange={(e) => handleSiteChange(e.target.value)}
            onBlur={() => validateOnBlur("site")}
            className={errors.site ? "border-destructive" : ""}
          />
          {errors.site && (
            <p className="text-xs text-destructive">{errors.site}</p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-foreground">
            Adresse Email
          </label>
          <Input
            type="email"
            placeholder="Entrez votre adresse email"
            value={pair.email_address}
            onChange={(e) => handleEmailChange(e.target.value)}
            onBlur={() => validateOnBlur("email_address")}
            className={errors.email_address ? "border-destructive" : ""}
          />
          {errors.email_address && (
            <p className="text-xs text-destructive">{errors.email_address}</p>
          )}
        </div>
      </div>

      {isMultiple && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDelete}
          disabled={isDeleting}
          className="self-start text-destructive hover:bg-destructive/10"
        >
          <X className="w-4 h-4 mr-2" />
          {isDeleting ? "Suppression..." : "Supprimer"}
        </Button>
      )}
    </div>
  );
}
