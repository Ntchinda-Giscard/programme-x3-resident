"use client";

import { useState, useEffect } from "react";
import { useConnectionStore } from "@/lib/database-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Database, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export function DatabaseConnectionForm() {
  const {
    connectionType,
    odbcConnection,
    sqlConnection,
    odbcSources,
    isLoading,
    setConnectionType,
    setODBCConnection,
    setSQLConnection,
    getOdbcSources,
    saveConnection,
    fetchODBCConnection,
  } = useConnectionStore();

  const [odbcForm, setOdbcForm] = useState(odbcConnection);
  const [sqlForm, setSqlForm] = useState(sqlConnection);
  const [isSaving, setIsSaving] = useState(false);
  const { toast } = useToast();

  // Load ODBC sources and existing connection on mount
  useEffect(() => {
    getOdbcSources();
    fetchODBCConnection();
    console.log("fetching connection", odbcConnection, sqlConnection);
  }, [getOdbcSources, fetchODBCConnection]);

  // Update form state when store values change
  useEffect(() => {
    setOdbcForm(odbcConnection);
  }, [odbcConnection]);

  useEffect(() => {
    setSqlForm(sqlConnection);
  }, [sqlConnection]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (connectionType === "odbc") {
        setODBCConnection(odbcForm);
      } else {
        setSQLConnection(sqlForm);
      }

      await saveConnection();
      toast({
        title: "Paramètres enregistrés",
        description: "Paramètres enregistrée avec succès !",
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Veuillez remplir tous les champ.";
      toast({
        title: "Erreur de validation",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" /> Connexion à la base de données
        </CardTitle>
        <CardDescription>
          Configurez les paramètres de connexion à votre base de données
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <Label>Type de connexion</Label>
          <RadioGroup
            value={connectionType}
            onValueChange={(value) =>
              setConnectionType(value as "odbc" | "sql")
            }
            disabled={isLoading}
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="sql" id="sql" />
              <Label htmlFor="sql" className="font-normal cursor-pointer">
                Connexion SQL
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="odbc" id="odbc" />
              <Label htmlFor="odbc" className="font-normal cursor-pointer">
                Source ODBC
              </Label>
            </div>
          </RadioGroup>
        </div>

        {connectionType === "sql" ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="host">Hôte</Label>
              <Input
                id="host"
                placeholder="localhost"
                value={sqlForm.host}
                onChange={(e) =>
                  setSqlForm({ ...sqlForm, host: e.target.value })
                }
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="port">Port</Label>
              <Input
                id="port"
                placeholder="5432"
                value={sqlForm.port}
                onChange={(e) =>
                  setSqlForm({ ...sqlForm, port: e.target.value })
                }
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="database">Base de données</Label>
              <Input
                id="database"
                placeholder="mabase"
                value={sqlForm.database}
                onChange={(e) =>
                  setSqlForm({ ...sqlForm, database: e.target.value })
                }
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="schemas">Schemas</Label>
              <Input
                id="schemas"
                placeholder="public"
                value={sqlForm.schemas}
                onChange={(e) =>
                  setSqlForm({ ...sqlForm, schemas: e.target.value })
                }
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sql-username">Nom d'utilisateur</Label>
              <Input
                id="sql-username"
                placeholder="admin"
                value={sqlForm.username}
                onChange={(e) =>
                  setSqlForm({ ...sqlForm, username: e.target.value })
                }
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sql-password">Mot de passe</Label>
              <Input
                id="sql-password"
                type="password"
                placeholder="••••••••"
                value={sqlForm.password}
                onChange={(e) =>
                  setSqlForm({ ...sqlForm, password: e.target.value })
                }
                disabled={isLoading}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="dsn">Nom DSN</Label>
              <Select
                value={odbcForm.dsnName}
                onValueChange={(value) =>
                  setOdbcForm({ ...odbcForm, dsnName: value })
                }
                disabled={isLoading}
              >
                <SelectTrigger id="dsn">
                  <SelectValue
                    placeholder={
                      isLoading
                        ? "Chargement..."
                        : odbcSources.length > 0
                        ? "Sélectionnez un DSN"
                        : "Aucune source ODBC disponible"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {odbcSources.map((source) => (
                    <SelectItem key={source.name} value={source.name}>
                      {source.name} ({source.description})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="odbc-database">Base de données</Label>
              <Input
                id="odbc-database"
                placeholder="sage_x3"
                value={odbcForm.database}
                onChange={(e) =>
                  setOdbcForm({ ...odbcForm, database: e.target.value })
                }
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="odbc-schemas">Schemas</Label>
              <Input
                id="odbc-schemas"
                placeholder="public"
                value={odbcForm.schemas}
                onChange={(e) =>
                  setOdbcForm({ ...odbcForm, schemas: e.target.value })
                }
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="odbc-username">Nom d'utilisateur</Label>
              <Input
                id="odbc-username"
                placeholder="admin"
                defaultValue={odbcForm.username}
                value={odbcForm.username}
                onChange={(e) =>
                  setOdbcForm({ ...odbcForm, username: e.target.value })
                }
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="odbc-password">Mot de passe</Label>
              <Input
                id="odbc-password"
                type="password"
                placeholder="••••••••"
                defaultValue={odbcForm.password}
                value={odbcForm.password}
                onChange={(e) =>
                  setOdbcForm({ ...odbcForm, password: e.target.value })
                }
                disabled={isLoading}
              />
            </div>
          </div>
        )}

        <Button
          onClick={handleSave}
          className="w-full mt-4"
          disabled={isSaving || isLoading}
        >
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Enregistrement...
            </>
          ) : (
            "Enregistrer la connexion"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
