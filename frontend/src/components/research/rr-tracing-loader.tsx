// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { Check, Database, RefreshCw, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getRRTracingCatalog } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { StoredRRTracing } from "@/types/research";

const DEFAULT_USER_ID = "demo-user";

function formatTracingLabel(tracing: StoredRRTracing): string {
  const source = tracing.source_file || "RR tracing";
  const dateText = tracing.measurement_date || "Unknown date";
  return `${source} • ${dateText}`;
}

export function RRTracingLoader(): React.JSX.Element {
  const activeUserId = useAppStore((state) => state.activeUserId);
  const rrTracingSelection = useAppStore((state) => state.rrTracingSelection);
  const setRRTracingSelection = useAppStore((state) => state.setRRTracingSelection);
  const clearRRTracingSelection = useAppStore((state) => state.clearRRTracingSelection);

  const userId = activeUserId ?? DEFAULT_USER_ID;
  const [open, setOpen] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);
  const [tracings, setTracings] = React.useState<StoredRRTracing[]>([]);
  const [selectedMeasurementId, setSelectedMeasurementId] = React.useState<string>("");

  const loadCatalog = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await getRRTracingCatalog(userId, 500);
      setTracings(response.tracings);
      if (response.tracings.length === 0) {
        setSelectedMeasurementId("");
        return;
      }
      if (
        rrTracingSelection &&
        rrTracingSelection.user_id === userId &&
        response.tracings.some((item) => item.measurement_id === rrTracingSelection.measurement_id)
      ) {
        setSelectedMeasurementId(rrTracingSelection.measurement_id);
        return;
      }
      setSelectedMeasurementId(response.tracings[0].measurement_id);
    } finally {
      setIsLoading(false);
    }
  }, [rrTracingSelection, userId]);

  React.useEffect(() => {
    if (!open) {
      return;
    }
    void loadCatalog();
  }, [loadCatalog, open]);

  const selectedTracing = React.useMemo(
    () => tracings.find((item) => item.measurement_id === selectedMeasurementId) ?? null,
    [selectedMeasurementId, tracings],
  );

  const activeLabel = React.useMemo(() => {
    if (!rrTracingSelection || rrTracingSelection.user_id !== userId) {
      return "Auto (latest)";
    }
    return rrTracingSelection.source_file || rrTracingSelection.measurement_id;
  }, [rrTracingSelection, userId]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="hidden lg:flex items-center gap-2">
          <Database className="h-4 w-4" />
          <span>RR Tracing</span>
          <Badge variant="secondary" className="max-w-[180px] truncate">
            {activeLabel}
          </Badge>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Select Stored RR Tracing</DialogTitle>
          <DialogDescription>
            Apply one tracing across research endpoints so every page analyzes the same recording.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void loadCatalog()}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                clearRRTracingSelection();
                setOpen(false);
              }}
            >
              <XCircle className="h-4 w-4 mr-2" />
              Clear Selection
            </Button>
          </div>

          <Select value={selectedMeasurementId} onValueChange={setSelectedMeasurementId}>
            <SelectTrigger>
              <SelectValue placeholder={isLoading ? "Loading tracings..." : "Choose a tracing"} />
            </SelectTrigger>
            <SelectContent>
              {tracings.map((item) => (
                <SelectItem key={item.measurement_id} value={item.measurement_id}>
                  {formatTracingLabel(item)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="max-h-40 overflow-y-auto rounded-md border p-3 text-sm text-muted-foreground">
            {selectedTracing ? (
              <div className="space-y-1">
                <p><strong>Source:</strong> {selectedTracing.source_file || "Unknown"}</p>
                <p><strong>Beats:</strong> {selectedTracing.n_intervals}</p>
                <p><strong>Date:</strong> {selectedTracing.measurement_date}</p>
                <p><strong>Quality:</strong> {selectedTracing.quality_status}</p>
                <p><strong>Cached Analysis:</strong> {selectedTracing.has_cached_analysis ? "Yes" : "No"}</p>
              </div>
            ) : (
              <p>No tracing selected.</p>
            )}
          </div>

          <div className="flex justify-end">
            <Button
              disabled={!selectedTracing}
              onClick={() => {
                if (!selectedTracing) {
                  return;
                }
                setRRTracingSelection({
                  user_id: userId,
                  measurement_id: selectedTracing.measurement_id,
                  file_hash: selectedTracing.file_hash ?? null,
                  source_file: selectedTracing.source_file ?? null,
                  selected_at: new Date().toISOString(),
                });
                setOpen(false);
              }}
            >
              <Check className="h-4 w-4 mr-2" />
              Apply Tracing
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
