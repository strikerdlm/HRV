// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  FlaskConical,
  Plus,
  Clock,
  Users,
  AlertCircle,
  CheckCircle2,
  Pause,
  Play,
  Trash2,
} from "lucide-react";
import { PageWrapper } from "@/components/layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { listExperiments, createExperiment, deleteExperiment } from "@/lib/api";
import type { Experiment } from "@/types";
import { getStatusColor, capitalize } from "@/lib/utils";

const priorityColors: Record<string, string> = {
  critical: "bg-danger text-danger-foreground",
  high: "bg-orange-500 text-white",
  medium: "bg-warning text-warning-foreground",
  low: "bg-muted text-muted-foreground",
};

function ExperimentCard({
  experiment,
  onDelete,
}: {
  experiment: Experiment;
  onDelete: (id: string) => void;
}) {
  const statusIcon = {
    draft: AlertCircle,
    approved: CheckCircle2,
    in_progress: Play,
    paused: Pause,
    completed: CheckCircle2,
    cancelled: AlertCircle,
  };
  const Icon = statusIcon[experiment.status] || AlertCircle;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      layout
    >
      <Card className="h-full flex flex-col">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="text-lg">{experiment.title}</CardTitle>
              <CardDescription>
                {experiment.description || "No description provided"}
              </CardDescription>
            </div>
            <Badge className={priorityColors[experiment.priority]}>
              {capitalize(experiment.priority)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="flex-1 space-y-4">
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock className="h-4 w-4" />
              {experiment.duration_minutes} min
            </div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <Users className="h-4 w-4" />
              {experiment.required_crew} crew
            </div>
          </div>
          {experiment.equipment.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {experiment.equipment.map((eq) => (
                <Badge key={eq} variant="outline" className="text-xs">
                  {eq}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
        <CardFooter className="flex items-center justify-between pt-4 border-t">
          <Badge variant="outline" className={getStatusColor(experiment.status)}>
            <Icon className="h-3 w-3 mr-1" />
            {capitalize(experiment.status.replace("_", " "))}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-danger"
            onClick={() => onDelete(experiment.experiment_id)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </CardFooter>
      </Card>
    </motion.div>
  );
}

function NewExperimentForm({
  onSubmit,
}: {
  onSubmit: (data: { title: string; priority: string; duration: number }) => void;
}) {
  const [title, setTitle] = React.useState("");
  const [priority, setPriority] = React.useState("medium");
  const [duration, setDuration] = React.useState(60);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit({ title, priority, duration });
    setTitle("");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plus className="h-5 w-5" />
          New Experiment
        </CardTitle>
        <CardDescription>Define a new science protocol</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Title</label>
            <Input
              placeholder="Experiment title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Priority</label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Duration (min)</label>
              <Input
                type="number"
                min={15}
                max={480}
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value) || 60)}
              />
            </div>
          </div>
          <Button type="submit" className="w-full">
            <Plus className="h-4 w-4 mr-2" />
            Create Experiment
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function ExperimentsPage() {
  const [experiments, setExperiments] = React.useState<Experiment[]>([]);
  const [loading, setLoading] = React.useState(true);

  const fetchExperiments = async () => {
    try {
      const data = await listExperiments();
      setExperiments(data.experiments);
    } catch (error) {
      console.error("Failed to fetch experiments:", error);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchExperiments();
  }, []);

  const handleCreate = async (data: {
    title: string;
    priority: string;
    duration: number;
  }) => {
    try {
      await createExperiment({
        title: data.title,
        priority: data.priority as any,
        duration_minutes: data.duration,
      });
      await fetchExperiments();
    } catch (error) {
      console.error("Failed to create experiment:", error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteExperiment(id);
      await fetchExperiments();
    } catch (error) {
      console.error("Failed to delete experiment:", error);
    }
  };

  return (
    <PageWrapper
      title="Experiments"
      description="Manage mission science protocols"
    >
      <div className="space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div className="flex items-center gap-4">
            <Badge variant="outline">
              {experiments.length} / 10 experiments
            </Badge>
          </div>
        </motion.div>

        {/* Main Content */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Experiments Grid */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2"
          >
            {experiments.length === 0 ? (
              <Card className="p-12">
                <div className="text-center">
                  <FlaskConical className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Experiments</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Create your first experiment to get started with science
                    operations.
                  </p>
                </div>
              </Card>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {experiments.map((exp) => (
                  <ExperimentCard
                    key={exp.experiment_id}
                    experiment={exp}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            )}
          </motion.div>

          {/* Sidebar */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <NewExperimentForm onSubmit={handleCreate} />
          </motion.div>
        </div>
      </div>
    </PageWrapper>
  );
}
