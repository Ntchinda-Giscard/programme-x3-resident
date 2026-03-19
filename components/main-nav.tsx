"use client";

import { cn } from "@/lib/utils";
import { Database, FolderTree, Settings, Mail, ShieldCheck } from "lucide-react";
import { TabsList, TabsTrigger } from "@/components/ui/tabs";

export function MainNavbar() {
  return (
    <header 
      style={{ WebkitAppRegion: "drag" } as any}
      className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60 select-none"
    >
      <div className="container mx-auto flex h-16 max-w-4xl items-center justify-between px-6">
        <div className="flex items-center gap-2 font-bold text-xl tracking-tight">
          <div className="rounded-md bg-primary p-1 text-primary-foreground">
            <FolderTree className="h-5 w-5" />
          </div>
          <span>WazaConnect</span>
        </div>

        <div style={{ WebkitAppRegion: "no-drag" } as any}>
          <TabsList className="bg-transparent border-none h-12 gap-1">
            <TabsTrigger 
              value="dossier" 
              className="data-[state=active]:bg-muted data-[state=active]:shadow-none px-4 py-2"
            >
              <FolderTree className="mr-2 h-4 w-4" />
              Dossiers
            </TabsTrigger>
            <TabsTrigger 
              value="database" 
              className="data-[state=active]:bg-muted data-[state=active]:shadow-none px-4 py-2"
            >
              <Database className="mr-2 h-4 w-4" />
              Base SQL
            </TabsTrigger>
            <TabsTrigger 
              value="email" 
              className="data-[state=active]:bg-muted data-[state=active]:shadow-none px-4 py-2"
            >
              <Mail className="mr-2 h-4 w-4" />
              E-mails
            </TabsTrigger>
            <TabsTrigger 
              value="site-email" 
              className="data-[state=active]:bg-muted data-[state=active]:shadow-none px-4 py-2"
            >
              <Settings className="mr-2 h-4 w-4" />
              Sites
            </TabsTrigger>
          </TabsList>
        </div>
      </div>
    </header>
  );
}
