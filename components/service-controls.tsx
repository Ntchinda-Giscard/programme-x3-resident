"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Play, Square, Download, RotateCw, Activity } from "lucide-react";
import { useFolderStore } from "@/lib/store";
import { useToast } from "@/hooks/use-toast";
import { useEffect } from "react";

export function ServiceControls() {
  const {
    serviceStatus,
    startService,
    stopService,
    installService,
    restartService,
    resetService,
    getServiceStatus,
  } = useFolderStore();
  const { toast } = useToast();

  useEffect(() => {
    const fetchStatus = async () => {
      await getServiceStatus();
    };
    fetchStatus();
  }, []);

  const handleStart = async () => {
    try {
      await startService();
      toast({
        title: "Service démarré",
        description: "Le service de traitement a été démarré avec succès.",
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Une erreur inconnue s'est produite.";
      toast({
        title: "Erreur",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const handleStop = async () => {
    try {
      await stopService();
      toast({
        title: "Service arrêté",
        description: "Le service de traitement a été arrêté.",
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Une erreur inconnue s'est produite.";
      toast({
        title: "Erreur",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const handleInstall = async () => {
    toast({
      title: "Installation en cours",
      description: "Installation du service en cours...",
    });
    try {
      await installService();
      toast({
        title: "Service installé",
        description: "Le service a été installé avec succès.",
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Une erreur inconnue s'est produite.";
      toast({
        title: "Erreur",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const handleRestart = async () => {
    try {
      await restartService();
      toast({
        title: "Service redémarré",
        description: "Le service a été redémarré avec succès.",
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Une erreur inconnue s'est produite.";
      toast({
        title: "Erreur",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const handleReset = async () => {
    if (
      !confirm(
        "Êtes-vous sûr de vouloir réinitialiser le service ? Cela arrêtera le service, le désinstallera et supprimera toutes les données locales.",
      )
    ) {
      return;
    }

    toast({
      title: "Réinitialisation en cours",
      description: "Le service est en cours de réinitialisation...",
    });

    try {
      await resetService();
      toast({
        title: "Service réinitialisé",
        description: "Le service a été réinitialisé avec succès.",
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Une erreur inconnue s'est produite lors de la réinitialisation.";
      toast({
        title: "Erreur",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const getStatusBadge = () => {
    switch (serviceStatus) {
      case "running":
        return (
          <Badge className="bg-green-500 hover:bg-green-600">
            <Activity className="mr-1 h-3 w-3" />
            En cours d'exécution
          </Badge>
        );
      case "stopped":
        return (
          <Badge variant="secondary">
            <Square className="mr-1 h-3 w-3" />
            Arrêté
          </Badge>
        );
      case "installing":
        return (
          <Badge className="bg-blue-500 hover:bg-blue-600">
            <Download className="mr-1 h-3 w-3" />
            Installation...
          </Badge>
        );
      case "error":
        return (
          <Badge variant="destructive">
            <Activity className="mr-1 h-3 w-3" />
            Erreur
          </Badge>
        );
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Contrôle du service
            </CardTitle>
            <CardDescription>
              Gérer le service de traitement de fichiers
            </CardDescription>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={handleStart}
            disabled={
              serviceStatus === "running" || serviceStatus === "installing"
            }
          >
            <Play className="mr-2 h-4 w-4" />
            Démarrer
          </Button>
          <Button
            onClick={handleStop}
            variant="destructive"
            disabled={
              serviceStatus === "stopped" || serviceStatus === "installing"
            }
          >
            <Square className="mr-2 h-4 w-4" />
            Arrêter
          </Button>
          <Button
            onClick={handleInstall}
            variant="secondary"
            disabled={serviceStatus === "installing"}
          >
            <Download className="mr-2 h-4 w-4" />
            Installer
          </Button>
          <Button
            onClick={handleRestart}
            variant="outline"
            disabled={
              serviceStatus === "stopped" || serviceStatus === "installing"
            }
          >
            <RotateCw className="mr-2 h-4 w-4" />
            Redémarrer
          </Button>
          <Button
            onClick={handleReset}
            variant="ghost"
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
            disabled={serviceStatus === "installing"}
          >
            <RotateCw className="mr-2 h-4 w-4" />
            Réinitialiser
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
