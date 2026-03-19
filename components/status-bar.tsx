"use client";

import { useFolderStore } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { Activity, Shield, Database, Wifi, WifiOff, Terminal } from "lucide-react";
import { useEffect, useState } from "react";

export function StatusBar() {
  const { serviceStatus, externalApiUrl } = useFolderStore();
  const [isOnline, setIsOnline] = useState(true);
  const [appStatus, setAppStatus] = useState<any>(null);

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch(`${externalApiUrl}/service/status`, {
          method: "GET",
          signal: AbortSignal.timeout(2000),
        });
        setIsOnline(response.ok);
      } catch (e) {
        setIsOnline(false);
      }
    };

    const fetchElectronStatus = async () => {
      if (typeof window !== "undefined" && (window as any).electronAPI?.getAppStatus) {
        try {
          const status = await (window as any).electronAPI.getAppStatus();
          setAppStatus(status);
        } catch (e) {
          console.error("Failed to fetch Electron status:", e);
        }
      }
    };

    checkConnection();
    fetchElectronStatus();
    
    const interval = setInterval(checkConnection, 10000);
    return () => clearInterval(interval);
  }, [externalApiUrl]);

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 flex h-8 items-center justify-between border-t bg-white px-4 text-[10px] font-medium text-slate-500 shadow-[0_-1px_3px_rgba(0,0,0,0.05)] select-none">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Database className="h-3.5 w-3.5 text-slate-400" />
          <span className="uppercase tracking-wider font-bold text-slate-600">WazaPOS Engine</span>
        </div>
        
        <div className="h-3 w-[1px] bg-slate-200" />
        
        <div className="flex items-center gap-1.5">
          {isOnline ? (
            <Wifi className="h-3 w-3 text-emerald-500" />
          ) : (
            <WifiOff className="h-3 w-3 text-rose-500" />
          )}
          <span>{isOnline ? "API Connected" : "API Offline"}</span>
          <span className="text-[9px] text-slate-400 font-normal">({externalApiUrl})</span>
        </div>

        {appStatus?.isAdmin && (
          <>
            <div className="h-3 w-[1px] bg-slate-200" />
            <div className="flex items-center gap-1.5 text-blue-600">
              <Shield className="h-3 w-3" />
              <span className="font-semibold uppercase">Administrator Mode</span>
            </div>
          </>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-slate-400">Service:</span>
          <div className="flex items-center gap-1.5">
            <div className={`h-1.5 w-1.5 rounded-full ${
              serviceStatus === 'running' ? 'bg-emerald-500 animate-pulse' : 
              serviceStatus === 'error' ? 'bg-rose-500' : 
              serviceStatus === 'installing' ? 'bg-blue-500 animate-bounce' : 
              'bg-slate-300'
            }`} />
            <span className="capitalize text-slate-700">{serviceStatus}</span>
          </div>
        </div>

        <div className="h-3 w-[1px] bg-slate-200" />

        <div className="flex items-center gap-1.5">
          <Terminal className="h-3 w-3 text-slate-400" />
          <span className="text-[9px] text-slate-400 lowercase">
            {appStatus ? `v${appStatus.version}-${appStatus.platform}` : "v1.2.0-web"}
          </span>
        </div>
      </div>
    </div>
  );
}
