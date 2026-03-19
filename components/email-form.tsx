import { Checkbox } from "@/components/ui/checkbox";
import { Loader2, Mail } from "lucide-react";
import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { EmailConfig, useSMTPStore } from "@/lib/email-store";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { useToast } from "@/hooks/use-toast";

export default function EmailForm() {
  const { emailConfig, setEmailConfig, saveSMTPConfig, fetchEmailConfig } =
    useSMTPStore();
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    fetchEmailConfig();
    console.log("fetching email config", emailConfig);
  }, [fetchEmailConfig]);
  const handleSubmit = async (emailConfig: EmailConfig) => {
    try {
      setIsLoading(true);
      setEmailConfig({ ...emailConfig });
      await saveSMTPConfig(emailConfig);
      toast({
        title: "Paramètres enregistrés",
        description: "Paramètres enregistrée avec succès !",
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Veuillez remplir tous les chemins de dossiers avant d'enregistrer.";

      toast({
        title: "Erreur de validation",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };
  return (
    <div>
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5 mr-2" />
            Paramètres SMTP
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="">Serveur SMTP</Label>
              <Input
                value={emailConfig.smtpServer}
                onChange={(e) => setEmailConfig({ smtpServer: e.target.value })}
                className=""
                placeholder="smtp.gmail.com"
              />
            </div>
            <div className="space-y-2">
              <Label className="">Port SMTP</Label>
              <Input
                type="number"
                value={emailConfig.smtpPort}
                onChange={(e) =>
                  setEmailConfig({
                    smtpPort: Number.parseInt(e.target.value) || 587,
                  })
                }
                className=""
                placeholder="587"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="">Email d'Expédition</Label>
              <Input
                type="email"
                value={emailConfig.senderEmail}
                onChange={(e) =>
                  setEmailConfig({ senderEmail: e.target.value })
                }
                className=""
                placeholder="noreply@company.com"
              />
            </div>
            <div className="space-y-2">
              <Label className="">Email Receptrice</Label>
              <Input
                type="email"
                value={emailConfig.receiverEmail}
                onChange={(e) =>
                  setEmailConfig({ receiverEmail: e.target.value })
                }
                className=""
                placeholder="noreply@company.com"
              />
            </div>
            <div className="space-y-2">
              <Label className="">Mot de Passe</Label>
              <Input
                type="password"
                value={emailConfig.senderPassword}
                onChange={(e) =>
                  setEmailConfig({ senderPassword: e.target.value })
                }
                className=""
                placeholder="••••••••"
              />
            </div>
          </div>

          <div className="space-y-3">
            <Label className="">Options de Sécurité</Label>
            <div className="flex space-x-6">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="ssl"
                  checked={emailConfig.useSSL}
                  onCheckedChange={(checked) =>
                    setEmailConfig({ useSSL: checked as boolean })
                  }
                />
                <Label htmlFor="ssl" className="">
                  Utiliser SSL
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="tls"
                  checked={emailConfig.useTLS}
                  onCheckedChange={(checked) =>
                    setEmailConfig({ useTLS: checked as boolean })
                  }
                />
                <Label htmlFor="tls" className="">
                  Utiliser TLS
                </Label>
              </div>
            </div>
          </div>

          <Button
            disabled={isLoading}
            className="mt-4"
            onClick={() => {
              handleSubmit(emailConfig);
            }}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Enregistrement...
              </>
            ) : (
              "Sauvegarder"
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
