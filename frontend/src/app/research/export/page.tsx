// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Download,
  FileText,
  FileJson,
  FileSpreadsheet,
  RefreshCw,
  CheckCircle,
  Settings,
  Calendar,
} from "lucide-react";
import { PageWrapper } from "@/components/layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { exportHRVData } from "@/lib/research-api";
import type { ExportRequest, ExportResponse } from "@/types/research";

const DEMO_USER_ID = "demo-user";

function FormatCard({
  format,
  icon: Icon,
  name,
  description,
  selected,
  onSelect,
}: {
  format: string;
  icon: React.ElementType;
  name: string;
  description: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      className={`p-4 rounded-lg border cursor-pointer transition-all ${
        selected ? "border-primary bg-primary/5 ring-2 ring-primary/20" : "hover:border-primary/50"
      }`}
      onClick={onSelect}
    >
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${selected ? "bg-primary/10" : "bg-muted"}`}>
          <Icon className={`h-6 w-6 ${selected ? "text-primary" : "text-muted-foreground"}`} />
        </div>
        <div className="flex-1">
          <p className="font-medium">{name}</p>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        {selected && <CheckCircle className="h-5 w-5 text-primary" />}
      </div>
    </div>
  );
}

function OptionCheckbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="rounded border-gray-300 text-primary focus:ring-primary"
      />
      <span className="text-sm">{label}</span>
    </label>
  );
}

export default function ExportPage() {
  const [format, setFormat] = React.useState<"csv" | "json" | "markdown">("csv");
  const [options, setOptions] = React.useState({
    include_timeseries: false,
    include_frequency: true,
    include_nonlinear: true,
    include_hrf: true,
    date_range_days: 30,
  });
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<ExportResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await exportHRVData(DEMO_USER_ID, {
        format,
        ...options,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;

    const blob = new Blob([result.data], { type: result.content_type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = result.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <PageWrapper
      title="Export Center"
      description="Download HRV Data and Reports"
    >
      <div className="space-y-6">
        {/* Format Selection */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Export Format
              </CardTitle>
              <CardDescription>
                Choose the output format for your data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-3">
                <FormatCard
                  format="csv"
                  icon={FileSpreadsheet}
                  name="CSV"
                  description="Spreadsheet-compatible format"
                  selected={format === "csv"}
                  onSelect={() => setFormat("csv")}
                />
                <FormatCard
                  format="json"
                  icon={FileJson}
                  name="JSON"
                  description="Structured data format"
                  selected={format === "json"}
                  onSelect={() => setFormat("json")}
                />
                <FormatCard
                  format="markdown"
                  icon={FileText}
                  name="Markdown"
                  description="Human-readable report"
                  selected={format === "markdown"}
                  onSelect={() => setFormat("markdown")}
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Options */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-info" />
                Export Options
              </CardTitle>
              <CardDescription>
                Configure what data to include
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 sm:grid-cols-2">
                <div className="space-y-3">
                  <p className="font-medium text-sm">Data Domains</p>
                  <OptionCheckbox
                    label="Time Domain (SDNN, RMSSD, pNN50)"
                    checked={true}
                    onChange={() => {}}
                  />
                  <OptionCheckbox
                    label="Frequency Domain (VLF, LF, HF, LF/HF)"
                    checked={options.include_frequency}
                    onChange={(c) => setOptions({ ...options, include_frequency: c })}
                  />
                  <OptionCheckbox
                    label="Nonlinear (SD1, SD2, DFA, Entropy)"
                    checked={options.include_nonlinear}
                    onChange={(c) => setOptions({ ...options, include_nonlinear: c })}
                  />
                  <OptionCheckbox
                    label="HRF (PIP, IALS, PSS, PAS)"
                    checked={options.include_hrf}
                    onChange={(c) => setOptions({ ...options, include_hrf: c })}
                  />
                  <OptionCheckbox
                    label="Raw RR Time Series"
                    checked={options.include_timeseries}
                    onChange={(c) => setOptions({ ...options, include_timeseries: c })}
                  />
                </div>
                <div className="space-y-3">
                  <p className="font-medium text-sm">Date Range</p>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <Input
                      type="number"
                      value={options.date_range_days}
                      onChange={(e) =>
                        setOptions({ ...options, date_range_days: Number(e.target.value) })
                      }
                      min={1}
                      max={365}
                      className="w-24"
                    />
                    <span className="text-sm text-muted-foreground">days</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Export data from the last {options.date_range_days} days
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Export Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="flex justify-center"
        >
          <Button
            size="lg"
            onClick={handleExport}
            disabled={loading}
            className="px-8"
          >
            {loading ? (
              <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
            ) : (
              <Download className="h-5 w-5 mr-2" />
            )}
            Generate Export
          </Button>
        </motion.div>

        {/* Error */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card className="border-danger">
              <CardContent className="pt-4">
                <p className="text-danger">{error}</p>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Result */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card className="border-success">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-success">
                  <CheckCircle className="h-5 w-5" />
                  Export Ready
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{result.format.toUpperCase()}</Badge>
                      <span className="text-sm">{result.filename}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {result.records_exported} records | {result.date_range}
                    </p>
                  </div>
                  <Button onClick={handleDownload}>
                    <Download className="h-4 w-4 mr-2" />
                    Download File
                  </Button>
                </div>

                {/* Preview for text formats */}
                {(result.format === "markdown" || result.format === "json") && (
                  <div className="mt-4">
                    <p className="text-sm font-medium mb-2">Preview:</p>
                    <pre className="p-4 rounded-lg bg-muted text-xs overflow-auto max-h-64">
                      {result.data.slice(0, 2000)}
                      {result.data.length > 2000 && "\n\n... (truncated)"}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Export Guidelines</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
              <p>
                • <strong>CSV:</strong> Best for spreadsheet analysis (Excel, Google Sheets, R, SPSS).
                Each row is a recording session.
              </p>
              <p>
                • <strong>JSON:</strong> Best for programmatic access and database import.
                Preserves data types and nested structures.
              </p>
              <p>
                • <strong>Markdown:</strong> Best for reports and documentation.
                Human-readable format with tables.
              </p>
              <p>
                • <strong>Raw Time Series:</strong> Including raw RR intervals increases file size
                significantly. Only enable if needed for custom analysis.
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
