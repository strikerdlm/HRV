// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Calendar,
  Clock,
  Users,
  Plus,
  Filter,
  Download,
  RefreshCw,
  Edit,
  Trash2,
  Save,
  X,
  AlertTriangle,
  CheckCircle,
  Activity,
  Heart,
  Moon,
  Zap,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  Settings,
  User,
  FileText,
  Play,
  Pause,
  Target,
  TrendingUp,
  TrendingDown,
  Minus,
  Globe,
  Shield,
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
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { listUsers, createUser, updateUser, deleteUser } from "@/lib/api";
import type { UserProfile, ActivityCategory, RiskLevel } from "@/types";
import { useAppStore } from "@/lib/store";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CrewMember {
  id: string;
  user: UserProfile;
  role: string;
  status: "on_duty" | "off_duty" | "rest" | "eva" | "medical";
  ihpiScore: number;
  fatigueLevel: number;
  sleepDebt: number;
  lastSleep: string;
  readinessScore: number;
}

interface ScheduleActivity {
  id: string;
  title: string;
  description?: string;
  startTime: string;
  endTime: string;
  assignedCrew: string[];
  category: ActivityCategory;
  status: "scheduled" | "in_progress" | "completed" | "cancelled" | "pending";
  priority: "critical" | "high" | "medium" | "low";
  location?: string;
}

interface Alert {
  id: string;
  type: "warning" | "danger" | "info" | "success";
  title: string;
  message: string;
  crewMember?: string;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ROLES = ["CDR", "PLT", "MS1", "MS2", "MS3", "MS4"];

const STATUS_COLORS: Record<string, string> = {
  on_duty: "bg-success text-success-foreground",
  off_duty: "bg-muted text-muted-foreground",
  rest: "bg-info text-info-foreground",
  eva: "bg-warning text-warning-foreground",
  medical: "bg-danger text-danger-foreground",
};

const CATEGORY_COLORS: Record<string, string> = {
  medical: "bg-blue-500/20 text-blue-700 border-blue-500",
  exercise: "bg-green-500/20 text-green-700 border-green-500",
  meal: "bg-yellow-500/20 text-yellow-700 border-yellow-500",
  experiment: "bg-purple-500/20 text-purple-700 border-purple-500",
  work: "bg-slate-500/20 text-slate-700 border-slate-500",
  sleep: "bg-indigo-500/20 text-indigo-700 border-indigo-500",
  maintenance: "bg-orange-500/20 text-orange-700 border-orange-500",
  communication: "bg-cyan-500/20 text-cyan-700 border-cyan-500",
  personal: "bg-pink-500/20 text-pink-700 border-pink-500",
  emergency: "bg-red-500/20 text-red-700 border-red-500",
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-500 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-500 text-black",
  low: "bg-green-500 text-white",
};

// Sample schedule data
const generateSampleSchedule = (date: Date): ScheduleActivity[] => [
  {
    id: "1",
    title: "Post-Sleep Assessment",
    description: "Morning HRV measurement and wellness check",
    startTime: "06:00",
    endTime: "07:00",
    assignedCrew: ["CDR", "PLT", "MS1", "MS2"],
    category: "medical",
    status: "completed",
    priority: "high",
    location: "Medical Bay",
  },
  {
    id: "2",
    title: "Morning Exercise",
    description: "Cardiovascular and resistance training",
    startTime: "07:00",
    endTime: "08:30",
    assignedCrew: ["CDR", "PLT"],
    category: "exercise",
    status: "completed",
    priority: "high",
    location: "Exercise Module",
  },
  {
    id: "3",
    title: "Breakfast",
    startTime: "08:30",
    endTime: "09:00",
    assignedCrew: ["CDR", "PLT", "MS1", "MS2"],
    category: "meal",
    status: "completed",
    priority: "medium",
    location: "Galley",
  },
  {
    id: "4",
    title: "Science Operations - Protein Crystallization",
    description: "Continue protein crystal growth experiment",
    startTime: "09:00",
    endTime: "12:00",
    assignedCrew: ["MS1", "MS2"],
    category: "experiment",
    status: "in_progress",
    priority: "high",
    location: "Science Module",
  },
  {
    id: "5",
    title: "Systems Maintenance",
    description: "Environmental control system check",
    startTime: "09:00",
    endTime: "11:00",
    assignedCrew: ["PLT"],
    category: "maintenance",
    status: "in_progress",
    priority: "medium",
    location: "Node 2",
  },
  {
    id: "6",
    title: "Flight Planning Review",
    startTime: "09:30",
    endTime: "11:00",
    assignedCrew: ["CDR"],
    category: "work",
    status: "in_progress",
    priority: "medium",
    location: "Cupola",
  },
  {
    id: "7",
    title: "Lunch",
    startTime: "12:00",
    endTime: "13:00",
    assignedCrew: ["CDR", "PLT", "MS1", "MS2"],
    category: "meal",
    status: "scheduled",
    priority: "medium",
    location: "Galley",
  },
  {
    id: "8",
    title: "EVA Preparation",
    description: "Suit checkout and EVA briefing",
    startTime: "14:00",
    endTime: "17:00",
    assignedCrew: ["CDR", "MS1"],
    category: "work",
    status: "scheduled",
    priority: "critical",
    location: "Airlock",
  },
  {
    id: "9",
    title: "Ground Communication",
    description: "Daily planning conference with Mission Control",
    startTime: "17:30",
    endTime: "18:30",
    assignedCrew: ["CDR", "PLT"],
    category: "communication",
    status: "scheduled",
    priority: "high",
    location: "Comm Station",
  },
  {
    id: "10",
    title: "Dinner",
    startTime: "18:30",
    endTime: "19:30",
    assignedCrew: ["CDR", "PLT", "MS1", "MS2"],
    category: "meal",
    status: "scheduled",
    priority: "medium",
    location: "Galley",
  },
  {
    id: "11",
    title: "Pre-Sleep Routine",
    startTime: "21:00",
    endTime: "21:30",
    assignedCrew: ["CDR", "PLT", "MS1", "MS2"],
    category: "personal",
    status: "scheduled",
    priority: "medium",
  },
  {
    id: "12",
    title: "Sleep Period",
    startTime: "21:30",
    endTime: "06:00",
    assignedCrew: ["CDR", "PLT", "MS1", "MS2"],
    category: "sleep",
    status: "scheduled",
    priority: "high",
  },
];

// Sample alerts
const sampleAlerts: Alert[] = [
  {
    id: "1",
    type: "warning",
    title: "Elevated Fatigue",
    message: "CDR shows elevated fatigue indicators. Consider schedule adjustment.",
    crewMember: "CDR",
    timestamp: new Date().toISOString(),
  },
  {
    id: "2",
    type: "info",
    title: "EVA Tomorrow",
    message: "EVA scheduled for tomorrow. Ensure pre-breathe protocol compliance.",
    timestamp: new Date().toISOString(),
  },
];

// ---------------------------------------------------------------------------
// Utility Functions
// ---------------------------------------------------------------------------

function getIHPIColor(score: number): string {
  if (score >= 80) return "text-success";
  if (score >= 60) return "text-warning";
  return "text-danger";
}

function getIHPIBgColor(score: number): string {
  if (score >= 80) return "bg-success";
  if (score >= 60) return "bg-warning";
  return "bg-danger";
}

function formatTime(time: string): string {
  const [hours, minutes] = time.split(":");
  const h = parseInt(hours);
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 || 12;
  return `${h12}:${minutes} ${ampm}`;
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

// Mission Workspace Selector
function MissionWorkspaceSelector() {
  const { activeMission, setActiveMission } = useAppStore();

  return (
    <Card className="bg-gradient-to-r from-slate-900 to-slate-800 text-white border-slate-700">
      <CardContent className="py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center">
              <Shield className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Crew Workspace</h2>
              <p className="text-sm text-slate-400">
                Mission-scoped database and configurations
              </p>
            </div>
          </div>
          <Select value={activeMission} onValueChange={setActiveMission}>
            <SelectTrigger className="w-40 bg-slate-800 border-slate-600">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Mission 1">Mission 1</SelectItem>
              <SelectItem value="Mission 2">Mission 2</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}

// Crew Member Card with Edit/Delete
function CrewMemberCard({
  member,
  onEdit,
  onDelete,
  onSelect,
  isSelected,
}: {
  member: CrewMember;
  onEdit: () => void;
  onDelete: () => void;
  onSelect: () => void;
  isSelected: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      layout
    >
      <Card
        className={`cursor-pointer transition-all ${
          isSelected ? "ring-2 ring-primary" : "hover:bg-accent/50"
        }`}
        onClick={onSelect}
      >
        <CardContent className="p-4">
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-lg font-bold text-primary">
                    {member.role}
                  </span>
                </div>
                <div
                  className={`absolute -bottom-1 -right-1 h-4 w-4 rounded-full border-2 border-background ${
                    STATUS_COLORS[member.status]?.split(" ")[0] || "bg-muted"
                  }`}
                />
              </div>
              <div>
                <h4 className="font-medium">
                  {member.user.full_name || member.user.username}
                </h4>
                <p className="text-sm text-muted-foreground capitalize">
                  {member.status.replace("_", " ")}
                </p>
              </div>
            </div>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit();
                }}
              >
                <Edit className="h-4 w-4" />
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-danger"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Remove Crew Member?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will remove {member.user.full_name || member.user.username} from
                      the crew. This action cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="bg-danger hover:bg-danger/90"
                      onClick={onDelete}
                    >
                      Remove
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>

          {/* IHPI Score */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">IHPI Score</span>
              <span className={`font-bold ${getIHPIColor(member.ihpiScore)}`}>
                {member.ihpiScore}%
              </span>
            </div>
            <Progress value={member.ihpiScore} className="h-2" />
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-2 mt-3">
            <div className="text-center p-2 rounded bg-muted/50">
              <Moon className="h-4 w-4 mx-auto text-muted-foreground mb-1" />
              <p className="text-xs font-medium">{member.sleepDebt}h debt</p>
            </div>
            <div className="text-center p-2 rounded bg-muted/50">
              <Activity className="h-4 w-4 mx-auto text-muted-foreground mb-1" />
              <p className="text-xs font-medium">{member.fatigueLevel}%</p>
            </div>
            <div className="text-center p-2 rounded bg-muted/50">
              <Target className="h-4 w-4 mx-auto text-muted-foreground mb-1" />
              <p className="text-xs font-medium">{member.readinessScore}%</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// Edit Crew Member Dialog - Comprehensive Admin Editor
function EditCrewMemberDialog({
  member,
  open,
  onOpenChange,
  onSave,
}: {
  member: CrewMember | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: Partial<UserProfile> & { role: string; status: string }) => void;
}) {
  const [activeSection, setActiveSection] = React.useState("identity");
  const [formData, setFormData] = React.useState({
    // Identity
    full_name: "",
    email: "",
    sex: "other" as "male" | "female" | "other",
    date_of_birth: "",
    language: "en",
    // Operational
    role: "MS1",
    status: "on_duty",
    occupation: "",
    // Biometrics
    height_cm: "",
    weight_kg: "",
    resting_hr_bpm: "",
    max_hr_bpm: "",
    vo2max_ml_kg_min: "",
    activity_level: "",
    // Lifestyle
    smoking_status: "",
    alcohol_use: "",
    caffeine_intake_mg: "",
    // Medical
    medical_conditions: "",
    medications: "",
  });

  React.useEffect(() => {
    if (member) {
      setFormData({
        full_name: member.user.full_name || "",
        email: member.user.email || "",
        sex: member.user.sex || "other",
        date_of_birth: member.user.date_of_birth || "",
        language: member.user.language || "en",
        role: member.role,
        status: member.status,
        occupation: member.user.occupation || "",
        height_cm: member.user.height_cm?.toString() || "",
        weight_kg: member.user.weight_kg?.toString() || "",
        resting_hr_bpm: member.user.resting_hr_bpm?.toString() || "",
        max_hr_bpm: member.user.max_hr_bpm?.toString() || "",
        vo2max_ml_kg_min: member.user.vo2max_ml_kg_min?.toString() || "",
        activity_level: member.user.activity_level || "",
        smoking_status: member.user.smoking_status || "",
        alcohol_use: member.user.alcohol_use || "",
        caffeine_intake_mg: member.user.caffeine_intake_mg?.toString() || "",
        medical_conditions: member.user.medical_conditions?.join(", ") || "",
        medications: member.user.medications?.join(", ") || "",
      });
    }
  }, [member]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      full_name: formData.full_name || null,
      email: formData.email || null,
      sex: formData.sex,
      date_of_birth: formData.date_of_birth || null,
      language: formData.language || "en",
      occupation: formData.occupation || null,
      height_cm: formData.height_cm ? parseFloat(formData.height_cm) : null,
      weight_kg: formData.weight_kg ? parseFloat(formData.weight_kg) : null,
      resting_hr_bpm: formData.resting_hr_bpm ? parseFloat(formData.resting_hr_bpm) : null,
      max_hr_bpm: formData.max_hr_bpm ? parseFloat(formData.max_hr_bpm) : null,
      vo2max_ml_kg_min: formData.vo2max_ml_kg_min ? parseFloat(formData.vo2max_ml_kg_min) : null,
      activity_level: formData.activity_level || null,
      smoking_status: formData.smoking_status || null,
      alcohol_use: formData.alcohol_use || null,
      caffeine_intake_mg: formData.caffeine_intake_mg ? parseFloat(formData.caffeine_intake_mg) : null,
      medical_conditions: formData.medical_conditions
        ? formData.medical_conditions.split(",").map((s) => s.trim()).filter(Boolean)
        : [],
      medications: formData.medications
        ? formData.medications.split(",").map((s) => s.trim()).filter(Boolean)
        : [],
      role: formData.role,
      status: formData.status,
    });
    onOpenChange(false);
  };

  const sections = [
    { id: "identity", label: "Identity", icon: User },
    { id: "operational", label: "Operational", icon: Shield },
    { id: "biometrics", label: "Biometrics", icon: Activity },
    { id: "lifestyle", label: "Lifestyle", icon: Heart },
    { id: "medical", label: "Medical", icon: FileText },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            {member ? `Edit Profile: ${member.user.full_name || member.user.username}` : "Add Crew Member"}
          </DialogTitle>
          <DialogDescription>
            Full admin access to modify all profile fields
          </DialogDescription>
        </DialogHeader>

        {/* Section Navigation */}
        <div className="flex gap-1 border-b pb-2">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <Button
                key={section.id}
                type="button"
                variant={activeSection === section.id ? "secondary" : "ghost"}
                size="sm"
                className="gap-2"
                onClick={() => setActiveSection(section.id)}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{section.label}</span>
              </Button>
            );
          })}
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="space-y-6 py-4">
            {/* Identity Section */}
            {activeSection === "identity" && (
              <motion.div
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                <h4 className="font-medium flex items-center gap-2 text-primary">
                  <User className="h-4 w-4" />
                  Identity Information
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Full Name</Label>
                    <Input
                      value={formData.full_name}
                      onChange={(e) =>
                        setFormData({ ...formData, full_name: e.target.value })
                      }
                      placeholder="Full Name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) =>
                        setFormData({ ...formData, email: e.target.value })
                      }
                      placeholder="email@example.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Sex</Label>
                    <Select
                      value={formData.sex}
                      onValueChange={(v) =>
                        setFormData({ ...formData, sex: v as "male" | "female" | "other" })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="male">Male</SelectItem>
                        <SelectItem value="female">Female</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Date of Birth</Label>
                    <Input
                      type="date"
                      value={formData.date_of_birth}
                      onChange={(e) =>
                        setFormData({ ...formData, date_of_birth: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label>Language</Label>
                    <Select
                      value={formData.language}
                      onValueChange={(v) =>
                        setFormData({ ...formData, language: v })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="en">English</SelectItem>
                        <SelectItem value="es">Spanish</SelectItem>
                        <SelectItem value="fr">French</SelectItem>
                        <SelectItem value="de">German</SelectItem>
                        <SelectItem value="ru">Russian</SelectItem>
                        <SelectItem value="zh">Chinese</SelectItem>
                        <SelectItem value="ja">Japanese</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                {member && (
                  <div className="p-3 bg-muted/50 rounded-lg text-sm">
                    <p className="text-muted-foreground">
                      <strong>User ID:</strong> {member.user.user_id}
                    </p>
                    <p className="text-muted-foreground">
                      <strong>Username:</strong> {member.user.username} (cannot be changed)
                    </p>
                    {member.user.created_at && (
                      <p className="text-muted-foreground">
                        <strong>Created:</strong>{" "}
                        {new Date(member.user.created_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                )}
              </motion.div>
            )}

            {/* Operational Section */}
            {activeSection === "operational" && (
              <motion.div
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                <h4 className="font-medium flex items-center gap-2 text-primary">
                  <Shield className="h-4 w-4" />
                  Operational Status
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Crew Role</Label>
                    <Select
                      value={formData.role}
                      onValueChange={(v) => setFormData({ ...formData, role: v })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map((role) => (
                          <SelectItem key={role} value={role}>
                            {role} - {role === "CDR" ? "Commander" :
                              role === "PLT" ? "Pilot" :
                              role === "MS1" ? "Mission Specialist 1" :
                              role === "MS2" ? "Mission Specialist 2" :
                              role === "MS3" ? "Mission Specialist 3" :
                              "Mission Specialist 4"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Current Status</Label>
                    <Select
                      value={formData.status}
                      onValueChange={(v) => setFormData({ ...formData, status: v })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="on_duty">On Duty</SelectItem>
                        <SelectItem value="off_duty">Off Duty</SelectItem>
                        <SelectItem value="rest">Rest Period</SelectItem>
                        <SelectItem value="eva">EVA Operations</SelectItem>
                        <SelectItem value="medical">Medical Hold</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label>Occupation / Specialty</Label>
                    <Input
                      value={formData.occupation}
                      onChange={(e) =>
                        setFormData({ ...formData, occupation: e.target.value })
                      }
                      placeholder="e.g., Flight Engineer, Materials Scientist"
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {/* Biometrics Section */}
            {activeSection === "biometrics" && (
              <motion.div
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                <h4 className="font-medium flex items-center gap-2 text-primary">
                  <Activity className="h-4 w-4" />
                  Physiological Parameters
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Height (cm)</Label>
                    <Input
                      type="number"
                      min="100"
                      max="250"
                      value={formData.height_cm}
                      onChange={(e) =>
                        setFormData({ ...formData, height_cm: e.target.value })
                      }
                      placeholder="175"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Weight (kg)</Label>
                    <Input
                      type="number"
                      min="30"
                      max="200"
                      step="0.1"
                      value={formData.weight_kg}
                      onChange={(e) =>
                        setFormData({ ...formData, weight_kg: e.target.value })
                      }
                      placeholder="70.0"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Resting Heart Rate (bpm)</Label>
                    <Input
                      type="number"
                      min="30"
                      max="120"
                      value={formData.resting_hr_bpm}
                      onChange={(e) =>
                        setFormData({ ...formData, resting_hr_bpm: e.target.value })
                      }
                      placeholder="60"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Maximum Heart Rate (bpm)</Label>
                    <Input
                      type="number"
                      min="120"
                      max="220"
                      value={formData.max_hr_bpm}
                      onChange={(e) =>
                        setFormData({ ...formData, max_hr_bpm: e.target.value })
                      }
                      placeholder="180"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>VO2max (ml/kg/min)</Label>
                    <Input
                      type="number"
                      min="15"
                      max="90"
                      step="0.1"
                      value={formData.vo2max_ml_kg_min}
                      onChange={(e) =>
                        setFormData({ ...formData, vo2max_ml_kg_min: e.target.value })
                      }
                      placeholder="45.0"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Activity Level</Label>
                    <Select
                      value={formData.activity_level}
                      onValueChange={(v) =>
                        setFormData({ ...formData, activity_level: v })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select level" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="sedentary">Sedentary</SelectItem>
                        <SelectItem value="light">Light Activity</SelectItem>
                        <SelectItem value="moderate">Moderate Activity</SelectItem>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="very_active">Very Active / Athlete</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="p-3 bg-info/10 rounded-lg text-sm border border-info/30">
                  <p className="text-info font-medium">BMI Calculator</p>
                  {formData.height_cm && formData.weight_kg && (
                    <p className="text-muted-foreground">
                      BMI: {(
                        parseFloat(formData.weight_kg) /
                        Math.pow(parseFloat(formData.height_cm) / 100, 2)
                      ).toFixed(1)} kg/m²
                    </p>
                  )}
                </div>
              </motion.div>
            )}

            {/* Lifestyle Section */}
            {activeSection === "lifestyle" && (
              <motion.div
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                <h4 className="font-medium flex items-center gap-2 text-primary">
                  <Heart className="h-4 w-4" />
                  Lifestyle Factors
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Smoking Status</Label>
                    <Select
                      value={formData.smoking_status}
                      onValueChange={(v) =>
                        setFormData({ ...formData, smoking_status: v })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="never">Never Smoked</SelectItem>
                        <SelectItem value="former">Former Smoker</SelectItem>
                        <SelectItem value="current_light">Current - Light</SelectItem>
                        <SelectItem value="current_moderate">Current - Moderate</SelectItem>
                        <SelectItem value="current_heavy">Current - Heavy</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Alcohol Use</Label>
                    <Select
                      value={formData.alcohol_use}
                      onValueChange={(v) =>
                        setFormData({ ...formData, alcohol_use: v })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select frequency" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        <SelectItem value="occasional">Occasional (1-2/month)</SelectItem>
                        <SelectItem value="light">Light (1-2/week)</SelectItem>
                        <SelectItem value="moderate">Moderate (3-7/week)</SelectItem>
                        <SelectItem value="heavy">Heavy (daily)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label>Daily Caffeine Intake (mg)</Label>
                    <Input
                      type="number"
                      min="0"
                      max="1000"
                      value={formData.caffeine_intake_mg}
                      onChange={(e) =>
                        setFormData({ ...formData, caffeine_intake_mg: e.target.value })
                      }
                      placeholder="200 (approx. 2 cups of coffee)"
                    />
                    <p className="text-xs text-muted-foreground">
                      Reference: 1 cup coffee ≈ 95mg, 1 espresso ≈ 63mg, 1 energy drink ≈ 80mg
                    </p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Medical Section */}
            {activeSection === "medical" && (
              <motion.div
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                <h4 className="font-medium flex items-center gap-2 text-primary">
                  <FileText className="h-4 w-4" />
                  Medical Information
                </h4>
                <div className="p-3 bg-warning/10 rounded-lg text-sm border border-warning/30 mb-4">
                  <p className="text-warning font-medium flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    Confidential Medical Data
                  </p>
                  <p className="text-muted-foreground mt-1">
                    This information is stored securely and used for health monitoring purposes only.
                  </p>
                </div>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Medical Conditions</Label>
                    <Textarea
                      value={formData.medical_conditions}
                      onChange={(e) =>
                        setFormData({ ...formData, medical_conditions: e.target.value })
                      }
                      placeholder="Enter conditions separated by commas (e.g., Hypertension, Asthma, Diabetes Type 2)"
                      rows={3}
                    />
                    <p className="text-xs text-muted-foreground">
                      Separate multiple conditions with commas
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label>Current Medications</Label>
                    <Textarea
                      value={formData.medications}
                      onChange={(e) =>
                        setFormData({ ...formData, medications: e.target.value })
                      }
                      placeholder="Enter medications separated by commas (e.g., Lisinopril 10mg, Metformin 500mg)"
                      rows={3}
                    />
                    <p className="text-xs text-muted-foreground">
                      Include dosage where applicable. Separate with commas.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </div>

          <DialogFooter className="border-t pt-4">
            <div className="flex items-center justify-between w-full">
              <p className="text-xs text-muted-foreground">
                All fields are optional except username
              </p>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                  Cancel
                </Button>
                <Button type="submit">
                  <Save className="h-4 w-4 mr-2" />
                  Save All Changes
                </Button>
              </div>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// Add Crew Member Dialog
function AddCrewMemberDialog({
  open,
  onOpenChange,
  onAdd,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (data: { username: string; fullName: string; sex: string; role: string }) => void;
}) {
  const [formData, setFormData] = React.useState({
    username: "",
    fullName: "",
    sex: "other",
    role: "MS1",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.username.trim()) return;
    onAdd(formData);
    setFormData({ username: "", fullName: "", sex: "other", role: "MS1" });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Crew Member</DialogTitle>
          <DialogDescription>
            Create a new crew member profile
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>Username *</Label>
            <Input
              value={formData.username}
              onChange={(e) =>
                setFormData({ ...formData, username: e.target.value })
              }
              placeholder="username"
              required
            />
          </div>
          <div className="space-y-2">
            <Label>Full Name</Label>
            <Input
              value={formData.fullName}
              onChange={(e) =>
                setFormData({ ...formData, fullName: e.target.value })
              }
              placeholder="Full Name"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Sex</Label>
              <Select
                value={formData.sex}
                onValueChange={(v) => setFormData({ ...formData, sex: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="male">Male</SelectItem>
                  <SelectItem value="female">Female</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Select
                value={formData.role}
                onValueChange={(v) => setFormData({ ...formData, role: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {role}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">
              <Plus className="h-4 w-4 mr-2" />
              Add Crew Member
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// Schedule Activity Card
function ScheduleActivityCard({
  activity,
  onStatusChange,
}: {
  activity: ScheduleActivity;
  onStatusChange: (id: string, status: ScheduleActivity["status"]) => void;
}) {
  const categoryColor = CATEGORY_COLORS[activity.category] || CATEGORY_COLORS.work;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      layout
    >
      <div className="flex items-stretch gap-4 p-4 rounded-lg border bg-card hover:bg-accent/30 transition-colors">
        {/* Time Column */}
        <div className="flex-shrink-0 w-24 flex flex-col justify-center">
          <p className="text-sm font-medium">{formatTime(activity.startTime)}</p>
          <p className="text-xs text-muted-foreground">
            to {formatTime(activity.endTime)}
          </p>
        </div>

        <Separator orientation="vertical" className="h-auto" />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h4 className="font-medium truncate">{activity.title}</h4>
              {activity.description && (
                <p className="text-sm text-muted-foreground line-clamp-1">
                  {activity.description}
                </p>
              )}
            </div>
            <Badge className={`${PRIORITY_COLORS[activity.priority]} shrink-0`}>
              {activity.priority}
            </Badge>
          </div>

          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <Badge variant="outline" className={categoryColor}>
              {activity.category}
            </Badge>
            {activity.location && (
              <Badge variant="outline" className="text-xs">
                📍 {activity.location}
              </Badge>
            )}
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Users className="h-3 w-3" />
              {activity.assignedCrew.join(", ")}
            </div>
          </div>
        </div>

        {/* Status Controls */}
        <div className="flex-shrink-0 flex flex-col justify-center gap-1">
          {activity.status === "scheduled" && (
            <Button
              size="sm"
              variant="outline"
              className="h-8"
              onClick={() => onStatusChange(activity.id, "in_progress")}
            >
              <Play className="h-3 w-3 mr-1" />
              Start
            </Button>
          )}
          {activity.status === "in_progress" && (
            <Button
              size="sm"
              variant="default"
              className="h-8"
              onClick={() => onStatusChange(activity.id, "completed")}
            >
              <CheckCircle className="h-3 w-3 mr-1" />
              Complete
            </Button>
          )}
          {activity.status === "completed" && (
            <Badge variant="success" className="justify-center">
              <CheckCircle className="h-3 w-3 mr-1" />
              Done
            </Badge>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// Alert Card
function AlertCard({ alert }: { alert: Alert }) {
  const icons = {
    warning: <AlertTriangle className="h-5 w-5 text-warning" />,
    danger: <AlertTriangle className="h-5 w-5 text-danger" />,
    info: <Activity className="h-5 w-5 text-info" />,
    success: <CheckCircle className="h-5 w-5 text-success" />,
  };

  const bgColors = {
    warning: "bg-warning/10 border-warning/30",
    danger: "bg-danger/10 border-danger/30",
    info: "bg-info/10 border-info/30",
    success: "bg-success/10 border-success/30",
  };

  return (
    <div className={`p-3 rounded-lg border ${bgColors[alert.type]}`}>
      <div className="flex items-start gap-3">
        {icons[alert.type]}
        <div className="flex-1">
          <h4 className="font-medium text-sm">{alert.title}</h4>
          <p className="text-xs text-muted-foreground mt-1">{alert.message}</p>
          {alert.crewMember && (
            <Badge variant="outline" className="mt-2 text-xs">
              {alert.crewMember}
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}

// Day Summary Card
function DaySummaryCard({ activities }: { activities: ScheduleActivity[] }) {
  const stats = React.useMemo(() => {
    const completed = activities.filter((a) => a.status === "completed").length;
    const total = activities.length;

    const workHours = activities
      .filter((a) => ["work", "experiment", "maintenance"].includes(a.category))
      .reduce((sum, a) => {
        const start = a.startTime.split(":").map(Number);
        const end = a.endTime.split(":").map(Number);
        const startMins = start[0] * 60 + start[1];
        let endMins = end[0] * 60 + end[1];
        if (endMins < startMins) endMins += 24 * 60; // Handle overnight
        return sum + (endMins - startMins) / 60;
      }, 0);

    const exerciseHours = activities
      .filter((a) => a.category === "exercise")
      .reduce((sum, a) => {
        const start = a.startTime.split(":").map(Number);
        const end = a.endTime.split(":").map(Number);
        return sum + (end[0] * 60 + end[1] - (start[0] * 60 + start[1])) / 60;
      }, 0);

    const sleepHours = activities
      .filter((a) => a.category === "sleep")
      .reduce((sum, a) => {
        const start = a.startTime.split(":").map(Number);
        const end = a.endTime.split(":").map(Number);
        const startMins = start[0] * 60 + start[1];
        let endMins = end[0] * 60 + end[1];
        if (endMins < startMins) endMins += 24 * 60;
        return sum + (endMins - startMins) / 60;
      }, 0);

    return {
      completed,
      total,
      compliance: total > 0 ? Math.round((completed / total) * 100) : 0,
      workHours: workHours.toFixed(1),
      exerciseHours: exerciseHours.toFixed(1),
      sleepHours: sleepHours.toFixed(1),
    };
  }, [activities]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Day Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Tasks Completed</span>
          <span className="font-medium">
            {stats.completed} / {stats.total}
          </span>
        </div>
        <Progress value={stats.compliance} className="h-2" />

        <Separator />

        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-sm text-muted-foreground">Work Hours</span>
            <span className="font-medium">{stats.workHours}h</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-muted-foreground">Exercise</span>
            <span className="font-medium">{stats.exerciseHours}h</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-muted-foreground">Sleep Scheduled</span>
            <span className="font-medium">{stats.sleepHours}h</span>
          </div>
        </div>

        <Separator />

        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Compliance</span>
          <Badge variant={stats.compliance >= 80 ? "success" : "warning"}>
            {stats.compliance}%
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

// IHPI Gauge Component
function IHPIGauge({ member }: { member: CrewMember }) {
  const score = member.ihpiScore;
  const color = getIHPIBgColor(score);

  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-center gap-3 mb-3">
        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
          <span className="font-bold text-primary">{member.role}</span>
        </div>
        <div>
          <h4 className="font-medium text-sm">
            {member.user.full_name || member.user.username}
          </h4>
          <p className="text-xs text-muted-foreground capitalize">
            {member.status.replace("_", " ")}
          </p>
        </div>
      </div>

      {/* Circular Gauge */}
      <div className="relative w-24 h-24 mx-auto">
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-muted/30"
          />
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeDasharray={`${(score / 100) * 251.2} 251.2`}
            className={color}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-2xl font-bold ${getIHPIColor(score)}`}>
            {score}
          </span>
        </div>
      </div>

      <div className="text-center mt-2">
        <p className="text-xs text-muted-foreground">IHPI Score</p>
      </div>

      {/* Sub-metrics */}
      <div className="grid grid-cols-3 gap-1 mt-3 text-center">
        <div>
          <p className="text-xs text-muted-foreground">Fatigue</p>
          <p className="text-sm font-medium">{member.fatigueLevel}%</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Sleep</p>
          <p className="text-sm font-medium">{member.sleepDebt}h</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Ready</p>
          <p className="text-sm font-medium">{member.readinessScore}%</p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function SchedulingPage() {
  const { activeMission, activeUserId, setActiveUserId } = useAppStore();

  // State
  const [users, setUsers] = React.useState<UserProfile[]>([]);
  const [crewMembers, setCrewMembers] = React.useState<CrewMember[]>([]);
  const [activities, setActivities] = React.useState<ScheduleActivity[]>([]);
  const [alerts, setAlerts] = React.useState<Alert[]>(sampleAlerts);
  const [loading, setLoading] = React.useState(true);
  const [selectedDate, setSelectedDate] = React.useState(new Date());
  const [editingMember, setEditingMember] = React.useState<CrewMember | null>(null);
  const [editDialogOpen, setEditDialogOpen] = React.useState(false);
  const [addDialogOpen, setAddDialogOpen] = React.useState(false);
  const [categoryFilter, setCategoryFilter] = React.useState<string>("all");

  // Fetch users and build crew members
  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await listUsers();
      setUsers(data.users);

      // Build crew members with simulated performance data
      const members: CrewMember[] = data.users.slice(0, 6).map((user, idx) => ({
        id: user.user_id,
        user,
        role: ROLES[idx % ROLES.length],
        status: idx === 0 ? "on_duty" : idx === 2 ? "rest" : "on_duty",
        ihpiScore: Math.round(70 + Math.random() * 25),
        fatigueLevel: Math.round(20 + Math.random() * 30),
        sleepDebt: Math.round(Math.random() * 3 * 10) / 10,
        lastSleep: "22:00",
        readinessScore: Math.round(60 + Math.random() * 35),
      }));
      setCrewMembers(members);

      // Generate schedule
      setActivities(generateSampleSchedule(selectedDate));
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handlers
  const handleAddCrewMember = async (data: {
    username: string;
    fullName: string;
    sex: string;
    role: string;
  }) => {
    try {
      const newUser = await createUser({
        username: data.username,
        full_name: data.fullName || undefined,
        sex: data.sex as "male" | "female" | "other",
      });

      const newMember: CrewMember = {
        id: newUser.user_id,
        user: newUser,
        role: data.role,
        status: "on_duty",
        ihpiScore: 85,
        fatigueLevel: 20,
        sleepDebt: 0,
        lastSleep: "22:00",
        readinessScore: 90,
      };

      setCrewMembers((prev) => [...prev, newMember]);
      setUsers((prev) => [...prev, newUser]);
    } catch (error) {
      console.error("Failed to add crew member:", error);
    }
  };

  const handleEditCrewMember = (member: CrewMember) => {
    setEditingMember(member);
    setEditDialogOpen(true);
  };

  const handleSaveCrewMember = async (
    data: Partial<UserProfile> & { role: string; status: string }
  ) => {
    if (!editingMember) return;

    try {
      const updatedUser = await updateUser(editingMember.user.user_id, {
        ...editingMember.user,
        ...data,
      });

      setCrewMembers((prev) =>
        prev.map((m) =>
          m.id === editingMember.id
            ? {
                ...m,
                user: updatedUser,
                role: data.role,
                status: data.status as CrewMember["status"],
              }
            : m
        )
      );

      setUsers((prev) =>
        prev.map((u) =>
          u.user_id === editingMember.user.user_id ? updatedUser : u
        )
      );
    } catch (error) {
      console.error("Failed to update crew member:", error);
    }

    setEditingMember(null);
  };

  const handleDeleteCrewMember = async (memberId: string) => {
    const member = crewMembers.find((m) => m.id === memberId);
    if (!member) return;

    try {
      await deleteUser(member.user.user_id);
      setCrewMembers((prev) => prev.filter((m) => m.id !== memberId));
      setUsers((prev) => prev.filter((u) => u.user_id !== member.user.user_id));

      if (activeUserId === member.user.user_id) {
        setActiveUserId(null);
      }
    } catch (error) {
      console.error("Failed to delete crew member:", error);
    }
  };

  const handleActivityStatusChange = (
    activityId: string,
    status: ScheduleActivity["status"]
  ) => {
    setActivities((prev) =>
      prev.map((a) => (a.id === activityId ? { ...a, status } : a))
    );
  };

  // Filtered activities
  const filteredActivities = React.useMemo(() => {
    if (categoryFilter === "all") return activities;
    return activities.filter((a) => a.category === categoryFilter);
  }, [activities, categoryFilter]);

  // Date navigation
  const navigateDate = (direction: number) => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() + direction);
    setSelectedDate(newDate);
  };

  return (
    <PageWrapper
      title="Crew Scheduling & Human Performance"
      description="Evidence-based scheduling with IHPI composite scoring"
    >
      <div className="space-y-6">
        {/* Mission Workspace Selector */}
        <MissionWorkspaceSelector />

        {/* Main Tabs */}
        <Tabs defaultValue="dashboard" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-flex">
            <TabsTrigger value="dashboard" className="gap-2">
              <Users className="h-4 w-4" />
              <span className="hidden sm:inline">Status Dashboard</span>
            </TabsTrigger>
            <TabsTrigger value="schedule" className="gap-2">
              <Calendar className="h-4 w-4" />
              <span className="hidden sm:inline">Schedule</span>
            </TabsTrigger>
            <TabsTrigger value="crew" className="gap-2">
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">Crew Management</span>
            </TabsTrigger>
            <TabsTrigger value="performance" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Performance</span>
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-3">
              {/* Crew Status Grid */}
              <div className="lg:col-span-2">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        Crew Status Overview
                      </CardTitle>
                      <Badge variant="outline">{activeMission}</Badge>
                    </div>
                    <CardDescription>
                      Real-time IHPI scores and operational status
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {crewMembers.map((member) => (
                        <IHPIGauge key={member.id} member={member} />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Alerts Panel */}
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5" />
                      Active Alerts
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {alerts.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <CheckCircle className="h-8 w-8 mx-auto mb-2 text-success" />
                        <p>No active alerts</p>
                      </div>
                    ) : (
                      alerts.map((alert) => (
                        <AlertCard key={alert.id} alert={alert} />
                      ))
                    )}
                  </CardContent>
                </Card>

                <DaySummaryCard activities={activities} />
              </div>
            </div>
          </TabsContent>

          {/* Schedule Tab */}
          <TabsContent value="schedule" className="space-y-6">
            {/* Date Navigation & Filters */}
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => navigateDate(-1)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <div className="px-4 py-2 border rounded-md min-w-[200px] text-center">
                  <p className="font-medium">
                    {selectedDate.toLocaleDateString("en-US", {
                      weekday: "long",
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => navigateDate(1)}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedDate(new Date())}
                >
                  Today
                </Button>
              </div>

              <div className="flex items-center gap-2">
                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                  <SelectTrigger className="w-40">
                    <Filter className="h-4 w-4 mr-2" />
                    <SelectValue placeholder="Filter" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Activities</SelectItem>
                    <SelectItem value="medical">Medical</SelectItem>
                    <SelectItem value="exercise">Exercise</SelectItem>
                    <SelectItem value="experiment">Experiments</SelectItem>
                    <SelectItem value="work">Work</SelectItem>
                    <SelectItem value="meal">Meals</SelectItem>
                    <SelectItem value="sleep">Sleep</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" size="icon" onClick={fetchData}>
                  <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </Button>
                <Button variant="outline" size="icon">
                  <Download className="h-4 w-4" />
                </Button>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Activity
                </Button>
              </div>
            </div>

            {/* Schedule List */}
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Calendar className="h-5 w-5" />
                      Daily Schedule
                    </CardTitle>
                    <CardDescription>
                      {filteredActivities.length} activities scheduled
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <AnimatePresence mode="popLayout">
                      {filteredActivities.map((activity) => (
                        <ScheduleActivityCard
                          key={activity.id}
                          activity={activity}
                          onStatusChange={handleActivityStatusChange}
                        />
                      ))}
                    </AnimatePresence>
                    {filteredActivities.length === 0 && (
                      <div className="text-center py-8 text-muted-foreground">
                        <Calendar className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p>No activities matching filter</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <div>
                <DaySummaryCard activities={activities} />
              </div>
            </div>
          </TabsContent>

          {/* Crew Management Tab */}
          <TabsContent value="crew" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-medium">Crew Members</h3>
                <p className="text-sm text-muted-foreground">
                  {crewMembers.length} members in {activeMission}
                </p>
              </div>
              <Button onClick={() => setAddDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Crew Member
              </Button>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <AnimatePresence mode="popLayout">
                {crewMembers.map((member) => (
                  <CrewMemberCard
                    key={member.id}
                    member={member}
                    isSelected={activeUserId === member.user.user_id}
                    onSelect={() => setActiveUserId(member.user.user_id)}
                    onEdit={() => handleEditCrewMember(member)}
                    onDelete={() => handleDeleteCrewMember(member.id)}
                  />
                ))}
              </AnimatePresence>
            </div>

            {crewMembers.length === 0 && (
              <Card>
                <CardContent className="py-12 text-center">
                  <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="text-lg font-medium mb-2">No Crew Members</h3>
                  <p className="text-muted-foreground mb-4">
                    Add crew members to start managing the schedule
                  </p>
                  <Button onClick={() => setAddDialogOpen(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add First Crew Member
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Performance Tab */}
          <TabsContent value="performance" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Integrated Human Performance Indicators (IHPI)
                </CardTitle>
                <CardDescription>
                  Composite scores based on fatigue, sleep debt, circadian alignment,
                  and physiological readiness
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {crewMembers.map((member) => (
                    <IHPIGauge key={member.id} member={member} />
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Performance Metrics Table */}
            <Card>
              <CardHeader>
                <CardTitle>Detailed Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-3 px-2 font-medium">Crew</th>
                        <th className="text-center py-3 px-2 font-medium">Status</th>
                        <th className="text-center py-3 px-2 font-medium">IHPI</th>
                        <th className="text-center py-3 px-2 font-medium">Fatigue</th>
                        <th className="text-center py-3 px-2 font-medium">Sleep Debt</th>
                        <th className="text-center py-3 px-2 font-medium">Readiness</th>
                        <th className="text-center py-3 px-2 font-medium">Go/No-Go</th>
                      </tr>
                    </thead>
                    <tbody>
                      {crewMembers.map((member) => (
                        <tr key={member.id} className="border-b">
                          <td className="py-3 px-2">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{member.role}</span>
                              <span className="text-muted-foreground">
                                {member.user.full_name || member.user.username}
                              </span>
                            </div>
                          </td>
                          <td className="text-center py-3 px-2">
                            <Badge
                              className={
                                STATUS_COLORS[member.status] || "bg-muted"
                              }
                            >
                              {member.status.replace("_", " ")}
                            </Badge>
                          </td>
                          <td className="text-center py-3 px-2">
                            <span
                              className={`font-bold ${getIHPIColor(
                                member.ihpiScore
                              )}`}
                            >
                              {member.ihpiScore}%
                            </span>
                          </td>
                          <td className="text-center py-3 px-2">
                            {member.fatigueLevel}%
                          </td>
                          <td className="text-center py-3 px-2">
                            {member.sleepDebt}h
                          </td>
                          <td className="text-center py-3 px-2">
                            {member.readinessScore}%
                          </td>
                          <td className="text-center py-3 px-2">
                            {member.ihpiScore >= 70 ? (
                              <Badge variant="success">GO</Badge>
                            ) : member.ihpiScore >= 50 ? (
                              <Badge variant="warning">MARGINAL</Badge>
                            ) : (
                              <Badge variant="danger">NO-GO</Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            {/* Scientific References */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Scientific Foundation
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground space-y-2">
                <p>
                  <strong>IHPI Composite Score:</strong> Based on SAFTE-FAST biomathematical
                  model (Hursh et al., 2004) and NASA Crew Scheduling guidelines
                  (NASA-STD-3001).
                </p>
                <p>
                  <strong>Fatigue Assessment:</strong> Samn-Perelli 7-point scale with
                  circadian modulation (Samel et al., 1997).
                </p>
                <p>
                  <strong>Sleep Debt:</strong> Cumulative deficit calculated against
                  8-hour baseline with decay factor (Van Dongen et al., 2003).
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Dialogs */}
      <EditCrewMemberDialog
        member={editingMember}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        onSave={handleSaveCrewMember}
      />

      <AddCrewMemberDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        onAdd={handleAddCrewMember}
      />
    </PageWrapper>
  );
}
