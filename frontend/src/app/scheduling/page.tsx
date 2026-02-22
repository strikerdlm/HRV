// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { currentSAFTEEffectiveness } from "@/lib/safte-model";
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
  CheckCircle2,
  Activity,
  Heart,
  Moon,
  Zap,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
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
  Check,
  Loader2,
  PlayCircle,
  StopCircle,
  MapPin,
  GripVertical,
  Copy,
  MoreVertical,
  UserPlus,
  UserMinus,
  Sparkles,
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
import { CrewPerformanceModal } from "@/components/crew-performance-modal";
import type { CrewMemberForModal } from "@/components/crew-performance-modal";

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
// Activity Templates (PROGSS-aligned)
// ---------------------------------------------------------------------------

interface ActivityTemplate {
  id: string;
  title: string;
  description: string;
  category: ActivityCategory;
  defaultDuration: number; // minutes
  priority: "critical" | "high" | "medium" | "low";
  location?: string;
}

const ACTIVITY_TEMPLATES: Record<string, ActivityTemplate[]> = {
  medical: [
    { id: "med-1", title: "Post-Sleep Assessment", description: "Morning HRV measurement and wellness check", category: "medical", defaultDuration: 60, priority: "high", location: "Medical Bay" },
    { id: "med-2", title: "Pre-EVA Medical Check", description: "Complete medical evaluation before EVA", category: "medical", defaultDuration: 45, priority: "critical", location: "Medical Bay" },
    { id: "med-3", title: "Weekly Health Screening", description: "Comprehensive weekly health assessment", category: "medical", defaultDuration: 90, priority: "high", location: "Medical Bay" },
    { id: "med-4", title: "Blood Draw / Lab Work", description: "Biomarker sample collection", category: "medical", defaultDuration: 30, priority: "medium", location: "Medical Bay" },
    { id: "med-5", title: "Psychological Assessment", description: "Mood and cognitive assessment", category: "medical", defaultDuration: 45, priority: "high", location: "Private Quarters" },
  ],
  exercise: [
    { id: "ex-1", title: "Morning Exercise", description: "Cardiovascular and resistance training", category: "exercise", defaultDuration: 90, priority: "high", location: "Exercise Module" },
    { id: "ex-2", title: "Afternoon Exercise", description: "Low-intensity recovery exercise", category: "exercise", defaultDuration: 60, priority: "medium", location: "Exercise Module" },
    { id: "ex-3", title: "CEVIS Cycling Session", description: "Cycle ergometer with vibration isolation", category: "exercise", defaultDuration: 45, priority: "high", location: "Exercise Module" },
    { id: "ex-4", title: "ARED Resistance Training", description: "Advanced resistive exercise device", category: "exercise", defaultDuration: 60, priority: "high", location: "Exercise Module" },
  ],
  meal: [
    { id: "meal-1", title: "Breakfast", description: "Morning meal", category: "meal", defaultDuration: 30, priority: "medium", location: "Galley" },
    { id: "meal-2", title: "Lunch", description: "Midday meal", category: "meal", defaultDuration: 60, priority: "medium", location: "Galley" },
    { id: "meal-3", title: "Dinner", description: "Evening meal", category: "meal", defaultDuration: 60, priority: "medium", location: "Galley" },
    { id: "meal-4", title: "Snack / Hydration Break", description: "Scheduled nutrition break", category: "meal", defaultDuration: 15, priority: "low", location: "Galley" },
  ],
  experiment: [
    { id: "exp-1", title: "Science Operations", description: "Scheduled experiment execution", category: "experiment", defaultDuration: 180, priority: "high", location: "Science Module" },
    { id: "exp-2", title: "Payload Operations", description: "Payload setup and data collection", category: "experiment", defaultDuration: 120, priority: "medium", location: "Science Module" },
    { id: "exp-3", title: "Earth Observation", description: "Photography and data collection", category: "experiment", defaultDuration: 60, priority: "medium", location: "Cupola" },
  ],
  work: [
    { id: "work-1", title: "Flight Planning Review", description: "Review and update mission timeline", category: "work", defaultDuration: 90, priority: "high", location: "Cupola" },
    { id: "work-2", title: "EVA Preparation", description: "Suit checkout and EVA briefing", category: "work", defaultDuration: 180, priority: "critical", location: "Airlock" },
    { id: "work-3", title: "Daily Planning Conference", description: "Mission Control coordination", category: "work", defaultDuration: 30, priority: "high", location: "Comm Station" },
    { id: "work-4", title: "Handover Briefing", description: "Crew shift handover", category: "work", defaultDuration: 30, priority: "high", location: "Cupola" },
  ],
  maintenance: [
    { id: "maint-1", title: "Systems Maintenance", description: "Environmental control system check", category: "maintenance", defaultDuration: 120, priority: "medium", location: "Node 2" },
    { id: "maint-2", title: "Inventory Management", description: "Cargo tracking and organization", category: "maintenance", defaultDuration: 60, priority: "low", location: "Storage Module" },
    { id: "maint-3", title: "Emergency Systems Check", description: "Fire and safety equipment inspection", category: "maintenance", defaultDuration: 45, priority: "high", location: "All Modules" },
  ],
  communication: [
    { id: "comm-1", title: "Ground Communication", description: "Daily planning conference with Mission Control", category: "communication", defaultDuration: 60, priority: "high", location: "Comm Station" },
    { id: "comm-2", title: "Family Private Communication", description: "Private communication with family", category: "communication", defaultDuration: 30, priority: "medium", location: "Private Quarters" },
    { id: "comm-3", title: "Public Affairs Event", description: "Media or educational outreach", category: "communication", defaultDuration: 45, priority: "medium", location: "Cupola" },
  ],
  sleep: [
    { id: "sleep-1", title: "Sleep Period", description: "Scheduled sleep", category: "sleep", defaultDuration: 510, priority: "high", location: "Crew Quarters" },
    { id: "sleep-2", title: "Pre-Sleep Routine", description: "Preparation for sleep", category: "sleep", defaultDuration: 30, priority: "medium", location: "Crew Quarters" },
    { id: "sleep-3", title: "Post-Sleep Routine", description: "Morning routine and hygiene", category: "sleep", defaultDuration: 30, priority: "medium", location: "Crew Quarters" },
  ],
  personal: [
    { id: "pers-1", title: "Personal Time", description: "Free time for recreation", category: "personal", defaultDuration: 60, priority: "low", location: "Any" },
    { id: "pers-2", title: "Personal Hygiene", description: "Daily hygiene routine", category: "personal", defaultDuration: 30, priority: "medium", location: "Hygiene Module" },
  ],
  emergency: [
    { id: "emerg-1", title: "Emergency Drill", description: "Scheduled emergency response drill", category: "emergency", defaultDuration: 60, priority: "critical", location: "All Modules" },
    { id: "emerg-2", title: "Medical Emergency Response", description: "Emergency medical situation", category: "emergency", defaultDuration: 120, priority: "critical", location: "Medical Bay" },
  ],
};

// ---------------------------------------------------------------------------
// PROGSS Checklist Items (aligned with the PROGSS methodology)
// ---------------------------------------------------------------------------

interface PROGSSCheckItem {
  id: string;
  phase: "A" | "PRE" | "B" | "POST";
  step: string;
  label: string;
  description: string;
  frequency: "daily" | "weekly" | "per_event" | "mission_start" | "mission_end";
}

const PROGSS_CHECKLIST: PROGSSCheckItem[] = [
  // Phase A - Characterization Stage
  { id: "a-1.1", phase: "A", step: "1.1", label: "Mission Definition", description: "Representatives, institutions, budget confirmed", frequency: "mission_start" },
  { id: "a-1.2", phase: "A", step: "1.2", label: "Destination Defined", description: "Location, agenda, itinerary confirmed", frequency: "mission_start" },
  { id: "a-1.3", phase: "A", step: "1.3", label: "Resources & Protocols", description: "Essential resources for human presence verified", frequency: "mission_start" },
  { id: "a-1.4", phase: "A", step: "1.4", label: "Risk Matrix", description: "Risk matrix for accidents and emergencies reviewed", frequency: "mission_start" },
  { id: "a-1.5", phase: "A", step: "1.5", label: "Personnel Criteria", description: "Criteria for registration of professionals", frequency: "mission_start" },
  { id: "a-1.6", phase: "A", step: "1.6", label: "Participant Criteria", description: "Criteria for participant suitability", frequency: "mission_start" },
  // Pre-Stage
  { id: "pre-2.1", phase: "PRE", step: "2.1", label: "Screening Complete", description: "Sociodemographic and health history collected", frequency: "mission_start" },
  { id: "pre-2.2", phase: "PRE", step: "2.2", label: "Assessment Done", description: "Assessment per established criteria completed", frequency: "mission_start" },
  { id: "pre-2.3", phase: "PRE", step: "2.3", label: "Preparation", description: "Baggage, identification, supplies prepared", frequency: "mission_start" },
  { id: "pre-2.4", phase: "PRE", step: "2.4", label: "Training Complete", description: "Participants and professionals trained", frequency: "mission_start" },
  { id: "pre-2.5", phase: "PRE", step: "2.5", label: "Reporting Training", description: "Incident reporting and update flow established", frequency: "mission_start" },
  // Phase B - During Stage (daily items)
  { id: "b-3.1", phase: "B", step: "3.1", label: "Remote Monitoring", description: "Self-management checklist completed", frequency: "daily" },
  { id: "b-3.2", phase: "B", step: "3.2", label: "Emergency Protocols", description: "Emergency protocols reviewed if needed", frequency: "per_event" },
  { id: "b-3.3", phase: "B", step: "3.3", label: "Communication", description: "Scheduled communication completed", frequency: "daily" },
  { id: "b-3.4", phase: "B", step: "3.4", label: "Evaluation Checklist", description: "Post-exposure evaluation items reviewed", frequency: "daily" },
  // Post-Stage
  { id: "post-4.1", phase: "POST", step: "4.1", label: "Post-Assessment", description: "Post-exposure assessment checklist comparative", frequency: "mission_end" },
  { id: "post-4.2", phase: "POST", step: "4.2", label: "Service/Support", description: "Impacts and effects recognized and addressed", frequency: "mission_end" },
  { id: "post-4.3", phase: "POST", step: "4.3", label: "Exit Interview", description: "Exit/reintegration interview completed", frequency: "mission_end" },
  { id: "post-4.4", phase: "POST", step: "4.4", label: "Recommendations", description: "Mission assessment and future recommendations", frequency: "mission_end" },
];

type SemaphoreStatus = "not_started" | "in_progress" | "completed" | "issue";

interface PROGSSCheckStatus {
  itemId: string;
  status: SemaphoreStatus;
  notes?: string;
  completedAt?: string;
  completedBy?: string;
}

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
      resting_hr_bpm: formData.resting_hr_bpm ? parseInt(formData.resting_hr_bpm, 10) : null,
      max_hr_bpm: formData.max_hr_bpm ? parseInt(formData.max_hr_bpm, 10) : null,
      vo2max_ml_kg_min: formData.vo2max_ml_kg_min ? parseFloat(formData.vo2max_ml_kg_min) : null,
      activity_level: formData.activity_level || null,
      smoking_status: formData.smoking_status || null,
      alcohol_use: formData.alcohol_use || null,
      caffeine_intake_mg: formData.caffeine_intake_mg ? parseInt(formData.caffeine_intake_mg, 10) : null,
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

// Add Activity Dialog with Templates Menu
function AddActivityDialog({
  open,
  onOpenChange,
  onAdd,
  crewMembers,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (activity: Omit<ScheduleActivity, "id">) => void;
  crewMembers: CrewMember[];
}) {
  const [selectedCategory, setSelectedCategory] = React.useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = React.useState<ActivityTemplate | null>(null);
  const [customMode, setCustomMode] = React.useState(false);
  const [formData, setFormData] = React.useState({
    title: "",
    description: "",
    startTime: "09:00",
    endTime: "10:00",
    category: "work" as ActivityCategory,
    priority: "medium" as "critical" | "high" | "medium" | "low",
    location: "",
    assignedCrew: [] as string[],
  });

  // Reset state when dialog opens/closes
  React.useEffect(() => {
    if (!open) {
      setSelectedCategory(null);
      setSelectedTemplate(null);
      setCustomMode(false);
      setFormData({
        title: "",
        description: "",
        startTime: "09:00",
        endTime: "10:00",
        category: "work",
        priority: "medium",
        location: "",
        assignedCrew: [],
      });
    }
  }, [open]);

  // Apply template to form
  const applyTemplate = (template: ActivityTemplate) => {
    setSelectedTemplate(template);
    const startHour = 9;
    const durationHours = Math.floor(template.defaultDuration / 60);
    const durationMins = template.defaultDuration % 60;
    const endHour = startHour + durationHours;
    const endMin = durationMins;

    setFormData({
      title: template.title,
      description: template.description,
      startTime: `${String(startHour).padStart(2, "0")}:00`,
      endTime: `${String(endHour).padStart(2, "0")}:${String(endMin).padStart(2, "0")}`,
      category: template.category,
      priority: template.priority,
      location: template.location || "",
      assignedCrew: [],
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) return;

    onAdd({
      title: formData.title,
      description: formData.description || undefined,
      startTime: formData.startTime,
      endTime: formData.endTime,
      category: formData.category,
      priority: formData.priority,
      location: formData.location || undefined,
      assignedCrew: formData.assignedCrew,
      status: "scheduled",
    });
    onOpenChange(false);
  };

  const toggleCrewMember = (role: string) => {
    setFormData((prev) => ({
      ...prev,
      assignedCrew: prev.assignedCrew.includes(role)
        ? prev.assignedCrew.filter((r) => r !== role)
        : [...prev.assignedCrew, role],
    }));
  };

  const categoryIcons: Record<string, React.ReactNode> = {
    medical: <Heart className="h-4 w-4" />,
    exercise: <Activity className="h-4 w-4" />,
    meal: <Clock className="h-4 w-4" />,
    experiment: <Target className="h-4 w-4" />,
    work: <FileText className="h-4 w-4" />,
    maintenance: <Settings className="h-4 w-4" />,
    communication: <Globe className="h-4 w-4" />,
    sleep: <Moon className="h-4 w-4" />,
    personal: <User className="h-4 w-4" />,
    emergency: <AlertTriangle className="h-4 w-4" />,
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            Add Activity
          </DialogTitle>
          <DialogDescription>
            Select from templates or create a custom activity
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {/* Step 1: Category Selection */}
          {!selectedCategory && !customMode && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              <div className="flex items-center justify-between">
                <h4 className="font-medium">Select Activity Category</h4>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCustomMode(true)}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Custom Activity
                </Button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                {Object.keys(ACTIVITY_TEMPLATES).map((category) => (
                  <motion.button
                    key={category}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={`p-4 rounded-lg border-2 transition-all text-left ${
                      CATEGORY_COLORS[category]?.split(" ")[0] || "bg-muted"
                    } hover:shadow-md`}
                    onClick={() => setSelectedCategory(category)}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      {categoryIcons[category]}
                      <span className="font-medium capitalize text-sm">{category}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {ACTIVITY_TEMPLATES[category]?.length || 0} templates
                    </p>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 2: Template Selection */}
          {selectedCategory && !selectedTemplate && !customMode && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-4"
            >
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedCategory(null)}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Back
                </Button>
                <h4 className="font-medium capitalize">{selectedCategory} Activities</h4>
              </div>

              <div className="grid gap-2">
                {ACTIVITY_TEMPLATES[selectedCategory]?.map((template) => (
                  <motion.button
                    key={template.id}
                    whileHover={{ scale: 1.01 }}
                    className="p-4 rounded-lg border bg-card hover:bg-accent/50 transition-all text-left"
                    onClick={() => applyTemplate(template)}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h5 className="font-medium">{template.title}</h5>
                        <p className="text-sm text-muted-foreground mt-1">
                          {template.description}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant="outline" className="text-xs">
                            <Clock className="h-3 w-3 mr-1" />
                            {template.defaultDuration} min
                          </Badge>
                          {template.location && (
                            <Badge variant="outline" className="text-xs">
                              📍 {template.location}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <Badge className={PRIORITY_COLORS[template.priority]}>
                        {template.priority}
                      </Badge>
                    </div>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 3: Activity Configuration (after template or custom) */}
          {(selectedTemplate || customMode) && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedTemplate(null);
                      setCustomMode(false);
                      setSelectedCategory(null);
                    }}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Back
                  </Button>
                  <h4 className="font-medium">
                    {selectedTemplate ? `Configure: ${selectedTemplate.title}` : "Custom Activity"}
                  </h4>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2 col-span-2">
                    <Label>Title *</Label>
                    <Input
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      placeholder="Activity title"
                      required
                    />
                  </div>

                  <div className="space-y-2 col-span-2">
                    <Label>Description</Label>
                    <Textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Activity description"
                      rows={2}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Start Time</Label>
                    <Input
                      type="time"
                      value={formData.startTime}
                      onChange={(e) => setFormData({ ...formData, startTime: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>End Time</Label>
                    <Input
                      type="time"
                      value={formData.endTime}
                      onChange={(e) => setFormData({ ...formData, endTime: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Category</Label>
                    <Select
                      value={formData.category}
                      onValueChange={(v) => setFormData({ ...formData, category: v as ActivityCategory })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.keys(ACTIVITY_TEMPLATES).map((cat) => (
                          <SelectItem key={cat} value={cat}>
                            <span className="capitalize">{cat}</span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Priority</Label>
                    <Select
                      value={formData.priority}
                      onValueChange={(v) =>
                        setFormData({ ...formData, priority: v as typeof formData.priority })
                      }
                    >
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

                  <div className="space-y-2 col-span-2">
                    <Label>Location</Label>
                    <Input
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                      placeholder="Activity location"
                    />
                  </div>

                  {/* Crew Assignment */}
                  <div className="space-y-2 col-span-2">
                    <Label>Assign Crew Members</Label>
                    <div className="flex flex-wrap gap-2">
                      {crewMembers.map((member) => (
                        <motion.button
                          key={member.id}
                          type="button"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          className={`px-3 py-2 rounded-lg border transition-all ${
                            formData.assignedCrew.includes(member.role)
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-card hover:bg-accent/50"
                          }`}
                          onClick={() => toggleCrewMember(member.role)}
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{member.role}</span>
                            <span className="text-xs opacity-75">
                              {member.user.full_name?.split(" ")[0] || member.user.username}
                            </span>
                          </div>
                        </motion.button>
                      ))}
                    </div>
                    {formData.assignedCrew.length === 0 && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Click crew members to assign them to this activity
                      </p>
                    )}
                  </div>
                </div>

                <DialogFooter className="pt-4">
                  <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={!formData.title.trim()}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Activity
                  </Button>
                </DialogFooter>
              </form>
            </motion.div>
          )}
        </div>
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
// ---------------------------------------------------------------------------
// Enhanced Schedule Activity Card with Edit Mode
// ---------------------------------------------------------------------------
function ScheduleActivityCard({
  activity,
  onStatusChange,
  onUpdate,
  onDelete,
  onDuplicate,
  crewMembers,
}: {
  activity: ScheduleActivity;
  onStatusChange: (id: string, status: ScheduleActivity["status"]) => void;
  onUpdate: (activity: ScheduleActivity) => void;
  onDelete: (id: string) => void;
  onDuplicate: (activity: ScheduleActivity) => void;
  crewMembers: CrewMember[];
}) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editData, setEditData] = React.useState(activity);
  const [showMenu, setShowMenu] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [showSuccess, setShowSuccess] = React.useState(false);

  const categoryColor = CATEGORY_COLORS[activity.category] || CATEGORY_COLORS.work;

  // Reset edit data when activity changes
  React.useEffect(() => {
    setEditData(activity);
  }, [activity]);

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate save delay for animation
    await new Promise((resolve) => setTimeout(resolve, 500));
    onUpdate(editData);
    setIsSaving(false);
    setShowSuccess(true);
    setTimeout(() => {
      setShowSuccess(false);
      setIsEditing(false);
    }, 800);
  };

  const handleCancel = () => {
    setEditData(activity);
    setIsEditing(false);
  };

  const toggleCrewMember = (crewName: string) => {
    setEditData((prev) => ({
      ...prev,
      assignedCrew: prev.assignedCrew.includes(crewName)
        ? prev.assignedCrew.filter((c) => c !== crewName)
        : [...prev.assignedCrew, crewName],
    }));
  };

  const getStatusGradient = () => {
    switch (activity.status) {
      case "completed":
        return "from-emerald-500/10 via-green-500/5 to-transparent border-emerald-500/30";
      case "in_progress":
        return "from-amber-500/10 via-yellow-500/5 to-transparent border-amber-500/30";
      case "cancelled":
        return "from-red-500/10 via-rose-500/5 to-transparent border-red-500/30";
      default:
        return "from-slate-500/5 via-transparent to-transparent border-border";
    }
  };

  const getPriorityGlow = () => {
    switch (activity.priority) {
      case "critical":
        return "shadow-red-500/20";
      case "high":
        return "shadow-orange-500/20";
      default:
        return "";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      layout
      className="group"
    >
      <motion.div
        className={`
          relative overflow-hidden rounded-xl border
          bg-gradient-to-r ${getStatusGradient()}
          transition-all duration-300
          ${isEditing ? "ring-2 ring-primary shadow-lg shadow-primary/20" : "hover:shadow-lg"}
          ${activity.priority === "critical" || activity.priority === "high" ? `shadow-md ${getPriorityGlow()}` : ""}
        `}
        animate={showSuccess ? { scale: [1, 1.02, 1] } : {}}
      >
        {/* Success overlay */}
        <AnimatePresence>
          {showSuccess && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-green-500/20 backdrop-blur-sm z-10 flex items-center justify-center"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="bg-green-500 rounded-full p-3"
              >
                <Check className="h-6 w-6 text-white" />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Edit Mode */}
        <AnimatePresence mode="wait">
          {isEditing ? (
            <motion.div
              key="edit"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="p-4 space-y-4"
            >
              {/* Edit Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <motion.div
                    animate={{ rotate: [0, 360] }}
                    transition={{ duration: 0.5 }}
                    className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center"
                  >
                    <Edit className="h-4 w-4 text-primary" />
                  </motion.div>
                  <span className="font-semibold text-sm">Edit Activity</span>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost" onClick={handleCancel} disabled={isSaving}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Title & Description */}
              <div className="space-y-3">
                <div>
                  <Label className="text-xs text-muted-foreground">Title</Label>
                  <Input
                    value={editData.title}
                    onChange={(e) => setEditData({ ...editData, title: e.target.value })}
                    className="mt-1"
                    placeholder="Activity title"
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Description</Label>
                  <Input
                    value={editData.description || ""}
                    onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                    className="mt-1"
                    placeholder="Activity description"
                  />
                </div>
              </div>

              {/* Time Selection */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" /> Start Time
                  </Label>
                  <Input
                    type="time"
                    value={editData.startTime}
                    onChange={(e) => setEditData({ ...editData, startTime: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" /> End Time
                  </Label>
                  <Input
                    type="time"
                    value={editData.endTime}
                    onChange={(e) => setEditData({ ...editData, endTime: e.target.value })}
                    className="mt-1"
                  />
                </div>
              </div>

              {/* Location */}
              <div>
                <Label className="text-xs text-muted-foreground flex items-center gap-1">
                  <MapPin className="h-3 w-3" /> Location
                </Label>
                <Input
                  value={editData.location || ""}
                  onChange={(e) => setEditData({ ...editData, location: e.target.value })}
                  className="mt-1"
                  placeholder="e.g., Medical Bay, Science Module"
                />
              </div>

              {/* Category & Priority */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs text-muted-foreground">Category</Label>
                  <Select
                    value={editData.category}
                    onValueChange={(value) => setEditData({ ...editData, category: value as ActivityCategory })}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.keys(CATEGORY_COLORS).map((cat) => (
                        <SelectItem key={cat} value={cat}>
                          <span className="capitalize">{cat}</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Priority</Label>
                  <Select
                    value={editData.priority}
                    onValueChange={(value) => setEditData({ ...editData, priority: value as ScheduleActivity["priority"] })}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="critical">🔴 Critical</SelectItem>
                      <SelectItem value="high">🟠 High</SelectItem>
                      <SelectItem value="medium">🟡 Medium</SelectItem>
                      <SelectItem value="low">🟢 Low</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Crew Assignment */}
              <div>
                <Label className="text-xs text-muted-foreground flex items-center gap-1 mb-2">
                  <Users className="h-3 w-3" /> Assigned Crew
                </Label>
                <div className="flex flex-wrap gap-2">
                  {crewMembers.map((member) => {
                    const isAssigned = editData.assignedCrew.includes(member.role);
                    return (
                      <motion.button
                        key={member.id}
                        type="button"
                        onClick={() => toggleCrewMember(member.role)}
                        className={`
                          px-3 py-1.5 rounded-full text-xs font-medium
                          flex items-center gap-1.5 transition-all
                          ${isAssigned
                            ? "bg-primary text-primary-foreground shadow-md shadow-primary/30"
                            : "bg-muted hover:bg-muted/80 text-muted-foreground"
                          }
                        `}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        {isAssigned ? (
                          <UserMinus className="h-3 w-3" />
                        ) : (
                          <UserPlus className="h-3 w-3" />
                        )}
                        {member.role}
                        <span className="text-[10px] opacity-70">
                          ({member.user.full_name?.split(" ")[0] || member.user.username})
                        </span>
                      </motion.button>
                    );
                  })}
                </div>
              </div>

              {/* Save/Cancel Actions */}
              <div className="flex items-center justify-end gap-2 pt-2 border-t">
                <Button variant="outline" onClick={handleCancel} disabled={isSaving}>
                  Cancel
                </Button>
                <Button onClick={handleSave} disabled={isSaving} className="min-w-[100px]">
                  {isSaving ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    >
                      <Loader2 className="h-4 w-4" />
                    </motion.div>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Save
                    </>
                  )}
                </Button>
              </div>
            </motion.div>
          ) : (
            /* View Mode */
            <motion.div
              key="view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-stretch"
            >
              {/* Drag Handle & Status Indicator */}
              <div className="flex items-center px-2 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab">
                <GripVertical className="h-4 w-4 text-muted-foreground" />
              </div>

              {/* Time Column */}
              <div className="flex-shrink-0 w-20 flex flex-col justify-center py-4">
                <motion.p
                  className="text-sm font-bold"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  {formatTime(activity.startTime)}
                </motion.p>
                <p className="text-xs text-muted-foreground">
                  to {formatTime(activity.endTime)}
                </p>
                <div className="mt-1">
                  <Badge
                    variant="outline"
                    className={`text-[10px] ${
                      activity.status === "completed"
                        ? "bg-green-500/10 text-green-600 border-green-500/30"
                        : activity.status === "in_progress"
                        ? "bg-yellow-500/10 text-yellow-600 border-yellow-500/30"
                        : ""
                    }`}
                  >
                    {activity.status.replace("_", " ")}
                  </Badge>
                </div>
              </div>

              {/* Colored Bar */}
              <div
                className="w-1 my-3 rounded-full"
                style={{
                  background: categoryColor.includes("text-")
                    ? undefined
                    : `linear-gradient(180deg, ${categoryColor.split(" ")[0].replace("bg-", "var(--")}), transparent)`,
                  backgroundColor: categoryColor.includes("text-") ? undefined : undefined,
                }}
              />

              {/* Content */}
              <div className="flex-1 min-w-0 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold truncate">{activity.title}</h4>
                    {activity.description && (
                      <p className="text-sm text-muted-foreground line-clamp-1 mt-0.5">
                        {activity.description}
                      </p>
                    )}
                  </div>
                  <Badge className={`${PRIORITY_COLORS[activity.priority]} shrink-0 text-xs`}>
                    {activity.priority}
                  </Badge>
                </div>

                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  <Badge variant="outline" className={`${categoryColor} text-xs`}>
                    {activity.category}
                  </Badge>
                  {activity.location && (
                    <Badge variant="outline" className="text-xs gap-1">
                      <MapPin className="h-2.5 w-2.5" />
                      {activity.location}
                    </Badge>
                  )}
                  <div className="flex items-center gap-1">
                    {activity.assignedCrew.map((crew) => (
                      <motion.div
                        key={crew}
                        className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center text-[10px] font-bold text-primary"
                        whileHover={{ scale: 1.1, y: -2 }}
                        title={crew}
                      >
                        {crew}
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex-shrink-0 flex items-center gap-2 pr-4">
                {/* Status Change Button */}
                {activity.status === "scheduled" && (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="h-9 px-3 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary text-sm font-medium flex items-center gap-1.5 transition-colors"
                    onClick={() => onStatusChange(activity.id, "in_progress")}
                  >
                    <Play className="h-3.5 w-3.5" />
                    Start
                  </motion.button>
                )}
                {activity.status === "in_progress" && (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="h-9 px-3 rounded-lg bg-green-500 hover:bg-green-600 text-white text-sm font-medium flex items-center gap-1.5 transition-colors shadow-md shadow-green-500/30"
                    onClick={() => onStatusChange(activity.id, "completed")}
                  >
                    <Check className="h-3.5 w-3.5" />
                    Done
                  </motion.button>
                )}
                {activity.status === "completed" && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="h-9 px-3 rounded-lg bg-green-500/10 text-green-600 text-sm font-medium flex items-center gap-1.5"
                  >
                    <CheckCircle className="h-3.5 w-3.5" />
                    Complete
                  </motion.div>
                )}

                {/* Edit Button */}
                <motion.button
                  whileHover={{ scale: 1.1, rotate: 10 }}
                  whileTap={{ scale: 0.9 }}
                  className="h-9 w-9 rounded-lg bg-muted/50 hover:bg-muted flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
                  onClick={() => setIsEditing(true)}
                >
                  <Edit className="h-4 w-4" />
                </motion.button>

                {/* More Actions */}
                <div className="relative">
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    className="h-9 w-9 rounded-lg bg-muted/50 hover:bg-muted flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
                    onClick={() => setShowMenu(!showMenu)}
                  >
                    <MoreVertical className="h-4 w-4" />
                  </motion.button>
                  
                  <AnimatePresence>
                    {showMenu && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: -10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: -10 }}
                        className="absolute right-0 top-full mt-2 z-50 w-40 rounded-lg border bg-popover shadow-xl overflow-hidden"
                      >
                        <button
                          className="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2 transition-colors"
                          onClick={() => {
                            onDuplicate(activity);
                            setShowMenu(false);
                          }}
                        >
                          <Copy className="h-4 w-4" />
                          Duplicate
                        </button>
                        <button
                          className="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2 transition-colors"
                          onClick={() => {
                            setIsEditing(true);
                            setShowMenu(false);
                          }}
                        >
                          <Edit className="h-4 w-4" />
                          Edit
                        </button>
                        <Separator />
                        <button
                          className="w-full px-3 py-2 text-sm text-left hover:bg-red-500/10 text-red-600 flex items-center gap-2 transition-colors"
                          onClick={() => {
                            onDelete(activity.id);
                            setShowMenu(false);
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                          Delete
                        </button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Progress indicator for in_progress status */}
        {activity.status === "in_progress" && (
          <motion.div
            className="absolute bottom-0 left-0 h-1 bg-gradient-to-r from-amber-500 via-yellow-500 to-amber-500"
            initial={{ width: "0%" }}
            animate={{ width: "100%" }}
            transition={{ duration: 60, repeat: Infinity }}
          />
        )}
      </motion.div>
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

// ---------------------------------------------------------------------------
// Animated Check Button Component
// ---------------------------------------------------------------------------
function AnimatedCheckButton({
  status,
  onClick,
  size = "md",
}: {
  status: SemaphoreStatus;
  onClick: () => void;
  size?: "sm" | "md" | "lg";
}) {
  const [isAnimating, setIsAnimating] = React.useState(false);
  const [showConfetti, setShowConfetti] = React.useState(false);

  const sizeClasses = {
    sm: "h-6 w-6",
    md: "h-8 w-8",
    lg: "h-10 w-10",
  };

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-4 w-4",
    lg: "h-5 w-5",
  };

  const handleClick = () => {
    setIsAnimating(true);
    if (status === "in_progress") {
      // About to complete - show confetti
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 1000);
    }
    onClick();
    setTimeout(() => setIsAnimating(false), 300);
  };

  const getGradient = () => {
    switch (status) {
      case "completed":
        return "bg-gradient-to-br from-emerald-400 via-green-500 to-emerald-600 shadow-lg shadow-green-500/30";
      case "in_progress":
        return "bg-gradient-to-br from-amber-400 via-yellow-500 to-orange-500 shadow-lg shadow-yellow-500/30";
      case "issue":
        return "bg-gradient-to-br from-red-400 via-red-500 to-rose-600 shadow-lg shadow-red-500/30";
      default:
        return "bg-gradient-to-br from-slate-200 via-slate-300 to-slate-400 dark:from-slate-600 dark:via-slate-700 dark:to-slate-800";
    }
  };

  const getRingColor = () => {
    switch (status) {
      case "completed":
        return "ring-green-500/50";
      case "in_progress":
        return "ring-yellow-500/50";
      case "issue":
        return "ring-red-500/50";
      default:
        return "ring-slate-400/30";
    }
  };

  return (
    <div className="relative">
      {/* Confetti particles */}
      <AnimatePresence>
        {showConfetti && (
          <>
            {[...Array(8)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-2 h-2 rounded-full"
                style={{
                  background: ["#22c55e", "#eab308", "#3b82f6", "#ec4899", "#8b5cf6"][i % 5],
                  left: "50%",
                  top: "50%",
                }}
                initial={{ x: 0, y: 0, scale: 0, opacity: 1 }}
                animate={{
                  x: Math.cos((i * Math.PI) / 4) * 40,
                  y: Math.sin((i * Math.PI) / 4) * 40,
                  scale: 1,
                  opacity: 0,
                }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.6, ease: "easeOut" }}
              />
            ))}
          </>
        )}
      </AnimatePresence>

      {/* Pulse ring animation */}
      <AnimatePresence>
        {status === "completed" && (
          <motion.div
            className={`absolute inset-0 rounded-full ring-2 ${getRingColor()}`}
            initial={{ scale: 1, opacity: 0.8 }}
            animate={{ scale: 1.5, opacity: 0 }}
            transition={{ duration: 1, repeat: Infinity }}
          />
        )}
      </AnimatePresence>

      {/* Main button */}
      <motion.button
        className={`
          ${sizeClasses[size]} rounded-full ${getGradient()}
          flex items-center justify-center cursor-pointer
          transition-all duration-200 hover:scale-110
          ring-2 ring-offset-2 ring-offset-background ${getRingColor()}
        `}
        whileHover={{ scale: 1.15, rotate: status === "not_started" ? 10 : 0 }}
        whileTap={{ scale: 0.85 }}
        animate={isAnimating ? { rotate: [0, -10, 10, 0], scale: [1, 1.2, 1] } : {}}
        onClick={handleClick}
        type="button"
      >
        <AnimatePresence mode="wait">
          {status === "completed" && (
            <motion.div
              key="check"
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              exit={{ scale: 0, rotate: 180 }}
              transition={{ type: "spring", stiffness: 500, damping: 25 }}
            >
              <Check className={`${iconSizes[size]} text-white drop-shadow-md`} strokeWidth={3} />
            </motion.div>
          )}
          {status === "in_progress" && (
            <motion.div
              key="progress"
              initial={{ scale: 0 }}
              animate={{ scale: 1, rotate: 360 }}
              exit={{ scale: 0 }}
              transition={{ type: "spring", stiffness: 400, damping: 20, rotate: { duration: 2, repeat: Infinity, ease: "linear" } }}
            >
              <Loader2 className={`${iconSizes[size]} text-white drop-shadow-md`} />
            </motion.div>
          )}
          {status === "issue" && (
            <motion.div
              key="alert"
              initial={{ scale: 0 }}
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ scale: { duration: 0.5, repeat: Infinity } }}
            >
              <AlertTriangle className={`${iconSizes[size]} text-white drop-shadow-md`} strokeWidth={2.5} />
            </motion.div>
          )}
          {status === "not_started" && (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              className={`${iconSizes[size]} rounded-full border-2 border-dashed border-white/50`}
            />
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Progress Ring Component
// ---------------------------------------------------------------------------
function ProgressRing({
  progress,
  size = 80,
  strokeWidth = 6,
  color = "#22c55e",
}: {
  progress: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        {/* Background circle */}
        <circle
          className="text-muted/30"
          strokeWidth={strokeWidth}
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        {/* Progress circle */}
        <motion.circle
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          style={{
            strokeDasharray: circumference,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <motion.span
          className="text-lg font-bold"
          key={progress}
          initial={{ scale: 1.2, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
        >
          {progress}%
        </motion.span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PROGSS Phase Card Component
// ---------------------------------------------------------------------------
function PROGSSPhaseCard({
  phase,
  label,
  icon: Icon,
  items,
  checkStatuses,
  onStatusChange,
  isExpanded,
  onToggle,
}: {
  phase: string;
  label: string;
  icon: React.ElementType;
  items: PROGSSCheckItem[];
  checkStatuses: Record<string, PROGSSCheckStatus>;
  onStatusChange: (itemId: string, status: SemaphoreStatus, notes?: string) => void;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const completedCount = items.filter((item) => checkStatuses[item.id]?.status === "completed").length;
  const progress = items.length > 0 ? Math.round((completedCount / items.length) * 100) : 0;

  const getNextStatus = (current: SemaphoreStatus): SemaphoreStatus => {
    const cycle: SemaphoreStatus[] = ["not_started", "in_progress", "completed", "issue"];
    const idx = cycle.indexOf(current);
    return cycle[(idx + 1) % cycle.length];
  };

  const getPhaseGradient = () => {
    switch (phase) {
      case "A":
        return "from-blue-500/10 via-indigo-500/10 to-violet-500/10";
      case "PRE":
        return "from-cyan-500/10 via-teal-500/10 to-emerald-500/10";
      case "B":
        return "from-amber-500/10 via-orange-500/10 to-red-500/10";
      case "POST":
        return "from-purple-500/10 via-pink-500/10 to-rose-500/10";
      default:
        return "from-slate-500/10 to-slate-600/10";
    }
  };

  const getPhaseColor = () => {
    switch (phase) {
      case "A":
        return "#6366f1";
      case "PRE":
        return "#14b8a6";
      case "B":
        return "#f97316";
      case "POST":
        return "#a855f7";
      default:
        return "#64748b";
    }
  };

  const getFrequencyBadge = (frequency: string) => {
    const config = {
      daily: { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", icon: RefreshCw },
      weekly: { bg: "bg-purple-500/10", text: "text-purple-600 dark:text-purple-400", icon: Calendar },
      per_event: { bg: "bg-orange-500/10", text: "text-orange-600 dark:text-orange-400", icon: Zap },
      mission_start: { bg: "bg-green-500/10", text: "text-green-600 dark:text-green-400", icon: PlayCircle },
      mission_end: { bg: "bg-red-500/10", text: "text-red-600 dark:text-red-400", icon: StopCircle },
    };
    const { bg, text, icon: BadgeIcon } = config[frequency as keyof typeof config] || config.daily;
    return (
      <Badge variant="outline" className={`${bg} ${text} text-[10px] gap-1`}>
        <BadgeIcon className="h-2.5 w-2.5" />
        {frequency.replace("_", " ")}
      </Badge>
    );
  };

  return (
    <motion.div
      layout
      className={`
        rounded-xl overflow-hidden
        bg-gradient-to-br ${getPhaseGradient()}
        border border-border/50
        backdrop-blur-sm
      `}
    >
      {/* Phase Header */}
      <motion.button
        className="w-full p-4 flex items-center gap-4 hover:bg-white/5 dark:hover:bg-black/5 transition-colors"
        onClick={onToggle}
        type="button"
      >
        <div
          className="h-12 w-12 rounded-xl flex items-center justify-center"
          style={{ background: `linear-gradient(135deg, ${getPhaseColor()}33, ${getPhaseColor()}66)` }}
        >
          <Icon className="h-6 w-6" style={{ color: getPhaseColor() }} />
        </div>
        <div className="flex-1 text-left">
          <h4 className="font-semibold text-sm">{label}</h4>
          <p className="text-xs text-muted-foreground">
            {completedCount}/{items.length} tasks completed
          </p>
        </div>
        <ProgressRing progress={progress} size={50} strokeWidth={4} color={getPhaseColor()} />
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="h-5 w-5 text-muted-foreground" />
        </motion.div>
      </motion.button>

      {/* Checklist Items */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-2">
              {items.map((item, index) => {
                const status = checkStatuses[item.id]?.status || "not_started";
                return (
                  <motion.div
                    key={item.id}
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: index * 0.05 }}
                    className={`
                      flex items-center gap-3 p-3 rounded-lg
                      ${status === "completed" 
                        ? "bg-green-500/10 border border-green-500/20" 
                        : status === "in_progress"
                        ? "bg-yellow-500/10 border border-yellow-500/20"
                        : status === "issue"
                        ? "bg-red-500/10 border border-red-500/20"
                        : "bg-white/50 dark:bg-slate-900/50 border border-transparent"
                      }
                      hover:shadow-md transition-all duration-200
                    `}
                  >
                    <AnimatedCheckButton
                      status={status}
                      onClick={() => onStatusChange(item.id, getNextStatus(status))}
                      size="md"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className="text-xs font-bold px-1.5 py-0.5 rounded"
                          style={{ 
                            background: `${getPhaseColor()}20`,
                            color: getPhaseColor(),
                          }}
                        >
                          {item.step}
                        </span>
                        <p className={`text-sm font-medium ${status === "completed" ? "line-through text-muted-foreground" : ""}`}>
                          {item.label}
                        </p>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {item.description}
                      </p>
                    </div>
                    {getFrequencyBadge(item.frequency)}
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// PROGSS Checklist Component - ENHANCED with Animations
// ---------------------------------------------------------------------------
function PROGSSChecklist({
  checkStatuses,
  onStatusChange,
  missionDay,
}: {
  checkStatuses: Record<string, PROGSSCheckStatus>;
  onStatusChange: (itemId: string, status: SemaphoreStatus, notes?: string) => void;
  missionDay: number;
}) {
  const [expandedPhases, setExpandedPhases] = React.useState<string[]>(["B"]); // Default expand Phase B
  const [showCelebration, setShowCelebration] = React.useState(false);

  const phases = [
    { id: "A", label: "Phase A - Characterization", icon: Shield, color: "#6366f1" },
    { id: "PRE", label: "Pre-Stage - Preparation", icon: FileText, color: "#14b8a6" },
    { id: "B", label: "Phase B - During Mission", icon: Activity, color: "#f97316" },
    { id: "POST", label: "Post-Stage - Assessment", icon: CheckCircle2, color: "#a855f7" },
  ];

  // Filter items based on frequency and mission day
  const getVisibleItems = (phase: string) => {
    return PROGSS_CHECKLIST.filter((item) => {
      if (item.phase !== phase) return false;
      if (item.frequency === "daily") return true;
      if (item.frequency === "per_event") return true;
      if (item.frequency === "mission_start" && missionDay <= 3) return true;
      if (item.frequency === "mission_end" && missionDay >= 7) return true;
      if (item.frequency === "weekly" && missionDay % 7 === 0) return true;
      return false;
    });
  };

  // Calculate total progress
  const allVisibleItems = phases.flatMap((p) => getVisibleItems(p.id));
  const completedCount = allVisibleItems.filter((item) => checkStatuses[item.id]?.status === "completed").length;
  const inProgressCount = allVisibleItems.filter((item) => checkStatuses[item.id]?.status === "in_progress").length;
  const issueCount = allVisibleItems.filter((item) => checkStatuses[item.id]?.status === "issue").length;
  const totalProgress = allVisibleItems.length > 0 ? Math.round((completedCount / allVisibleItems.length) * 100) : 0;

  // Check for 100% completion celebration
  React.useEffect(() => {
    if (totalProgress === 100 && allVisibleItems.length > 0) {
      setShowCelebration(true);
      setTimeout(() => setShowCelebration(false), 3000);
    }
  }, [totalProgress, allVisibleItems.length]);

  const togglePhase = (phaseId: string) => {
    setExpandedPhases((prev) =>
      prev.includes(phaseId) ? prev.filter((p) => p !== phaseId) : [...prev, phaseId]
    );
  };

  const confettiParticles = React.useMemo(() => {
    const colors = ["#22c55e", "#eab308", "#3b82f6", "#ec4899", "#8b5cf6", "#f97316"];
    return Array.from({ length: 20 }, (_, i) => {
      const angle = (i / 20) * Math.PI * 2;
      const radius = 120 + ((missionDay * 17 + i * 29) % 160);
      return {
        id: i,
        color: colors[i % colors.length],
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        rotate: (i * 47 + missionDay * 13) % 360,
        delay: (i % 6) * 0.08,
      };
    });
  }, [missionDay]);

  return (
    <Card className="overflow-hidden relative">
      {/* Celebration overlay */}
      <AnimatePresence>
        {showCelebration && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              exit={{ scale: 0, rotate: 180 }}
              className="text-center"
            >
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 0.5, repeat: Infinity }}
                className="text-6xl mb-4"
              >
                🎉
              </motion.div>
              <h3 className="text-2xl font-bold text-white">All Tasks Complete!</h3>
              <p className="text-white/80">Mission Day {missionDay} checklist finished</p>
            </motion.div>
            {/* Confetti */}
            {confettiParticles.map((particle) => (
              <motion.div
                key={particle.id}
                className="absolute w-3 h-3 rounded-full"
                style={{
                  background: particle.color,
                  left: "50%",
                  top: "50%",
                }}
                initial={{ x: 0, y: 0, scale: 0 }}
                animate={{
                  x: particle.x,
                  y: particle.y,
                  scale: [0, 1, 0],
                  rotate: particle.rotate,
                }}
                transition={{ duration: 2, delay: particle.delay }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <CardHeader className="bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 border-b">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-lg shadow-primary/30">
              <Target className="h-6 w-6 text-white" />
            </div>
            <div>
              <CardTitle className="text-lg">PROGSS Daily Checklist</CardTitle>
              <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                <Badge variant="outline" className="bg-background">
                  <Calendar className="h-3 w-3 mr-1" />
                  Day {missionDay}
                </Badge>
                <span className="text-xs">Click circles to update status</span>
              </div>
            </div>
          </div>
          <ProgressRing progress={totalProgress} size={70} strokeWidth={5} color="#22c55e" />
        </div>

        {/* Status Summary */}
        <div className="flex items-center gap-3 mt-4">
          <motion.div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20"
            whileHover={{ scale: 1.05 }}
          >
            <div className="h-2.5 w-2.5 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs font-medium text-green-600 dark:text-green-400">{completedCount} Done</span>
          </motion.div>
          <motion.div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20"
            whileHover={{ scale: 1.05 }}
          >
            <div className="h-2.5 w-2.5 rounded-full bg-yellow-500" />
            <span className="text-xs font-medium text-yellow-600 dark:text-yellow-400">{inProgressCount} Active</span>
          </motion.div>
          {issueCount > 0 && (
            <motion.div
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20"
              whileHover={{ scale: 1.05 }}
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
            >
              <div className="h-2.5 w-2.5 rounded-full bg-red-500" />
              <span className="text-xs font-medium text-red-600 dark:text-red-400">{issueCount} Issues</span>
            </motion.div>
          )}
          <div className="flex-1" />
          <Badge variant="outline" className="text-xs">
            {allVisibleItems.length - completedCount - inProgressCount - issueCount} Pending
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-4 space-y-3">
        {phases.map(({ id, label, icon }) => {
          const items = getVisibleItems(id);
          if (items.length === 0) return null;

          return (
            <PROGSSPhaseCard
              key={id}
              phase={id}
              label={label}
              icon={icon}
              items={items}
              checkStatuses={checkStatuses}
              onStatusChange={onStatusChange}
              isExpanded={expandedPhases.includes(id)}
              onToggle={() => togglePhase(id)}
            />
          );
        })}
      </CardContent>
    </Card>
  );
}

// Crew Detail Modal - Shows full profile when crew member is clicked
function CrewDetailModal({
  member,
  open,
  onOpenChange,
  onEdit,
}: {
  member: CrewMember | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEdit: () => void;
}) {
  if (!member) return null;

  const calculateBMI = () => {
    if (!member.user.height_cm || !member.user.weight_kg) return null;
    const heightM = member.user.height_cm / 100;
    return (member.user.weight_kg / (heightM * heightM)).toFixed(1);
  };

  const calculateAge = () => {
    if (!member.user.date_of_birth) return null;
    const birth = new Date(member.user.date_of_birth);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  const bmi = calculateBMI();
  const age = calculateAge();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-xl font-bold text-primary">{member.role}</span>
            </div>
            <div>
              <span>{member.user.full_name || member.user.username}</span>
              <p className="text-sm text-muted-foreground font-normal capitalize">
                {member.status.replace("_", " ")} • {member.role}
              </p>
            </div>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Performance Metrics */}
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 rounded-lg border bg-card text-center">
              <div className={`text-2xl font-bold ${getIHPIColor(member.ihpiScore)}`}>
                {member.ihpiScore}%
              </div>
              <p className="text-xs text-muted-foreground mt-1">IHPI Score</p>
            </div>
            <div className="p-4 rounded-lg border bg-card text-center">
              <div className="text-2xl font-bold">{member.fatigueLevel}%</div>
              <p className="text-xs text-muted-foreground mt-1">Fatigue</p>
            </div>
            <div className="p-4 rounded-lg border bg-card text-center">
              <div className="text-2xl font-bold">{member.sleepDebt}h</div>
              <p className="text-xs text-muted-foreground mt-1">Sleep Debt</p>
            </div>
            <div className="p-4 rounded-lg border bg-card text-center">
              <div className="text-2xl font-bold">{member.readinessScore}%</div>
              <p className="text-xs text-muted-foreground mt-1">Readiness</p>
            </div>
          </div>

          <Separator />

          {/* Identity Information */}
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <User className="h-4 w-4" />
              Identity
            </h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Full Name</span>
                <p className="font-medium">{member.user.full_name || "Not set"}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Email</span>
                <p className="font-medium">{member.user.email || "Not set"}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Sex</span>
                <p className="font-medium capitalize">{member.user.sex}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Age</span>
                <p className="font-medium">{age ? `${age} years` : "Not set"}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Occupation</span>
                <p className="font-medium">{member.user.occupation || "Not set"}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Language</span>
                <p className="font-medium uppercase">{member.user.language || "EN"}</p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Biometric Data */}
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Biometrics
            </h4>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Height</span>
                <p className="font-medium">
                  {member.user.height_cm ? `${member.user.height_cm} cm` : "Not set"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Weight</span>
                <p className="font-medium">
                  {member.user.weight_kg ? `${member.user.weight_kg} kg` : "Not set"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">BMI</span>
                <p className="font-medium">{bmi ? `${bmi} kg/m²` : "N/A"}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Resting HR</span>
                <p className="font-medium">
                  {member.user.resting_hr_bpm ? `${member.user.resting_hr_bpm} bpm` : "Not set"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Max HR</span>
                <p className="font-medium">
                  {member.user.max_hr_bpm ? `${member.user.max_hr_bpm} bpm` : "Not set"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">VO2max</span>
                <p className="font-medium">
                  {member.user.vo2max_ml_kg_min
                    ? `${member.user.vo2max_ml_kg_min} ml/kg/min`
                    : "Not set"}
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Lifestyle Factors */}
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <Heart className="h-4 w-4" />
              Lifestyle
            </h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Activity Level</span>
                <p className="font-medium capitalize">
                  {member.user.activity_level?.replace("_", " ") || "Not set"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Smoking Status</span>
                <p className="font-medium capitalize">
                  {member.user.smoking_status?.replace("_", " ") || "Not set"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Alcohol Use</span>
                <p className="font-medium capitalize">
                  {member.user.alcohol_use?.replace("_", " ") || "Not set"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Caffeine Intake</span>
                <p className="font-medium">
                  {member.user.caffeine_intake_mg
                    ? `${member.user.caffeine_intake_mg} mg/day`
                    : "Not set"}
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Medical Information */}
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2 text-warning">
              <FileText className="h-4 w-4" />
              Medical Information
            </h4>
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-muted-foreground">Medical Conditions</span>
                <div className="mt-1">
                  {member.user.medical_conditions?.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {member.user.medical_conditions.map((condition, idx) => (
                        <Badge key={idx} variant="outline" className="text-xs">
                          {condition}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">None reported</p>
                  )}
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">Current Medications</span>
                <div className="mt-1">
                  {member.user.medications?.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {member.user.medications.map((med, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {med}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">None reported</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={onEdit}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Profile
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// IHPI Gauge Component
function IHPIGauge({ member, onClick }: { member: CrewMember; onClick?: () => void }) {
  const score = member.ihpiScore;
  const color = getIHPIBgColor(score);

  return (
    <motion.div
      className={`p-4 rounded-lg border bg-card transition-all ${
        onClick ? "cursor-pointer hover:bg-accent/50 hover:shadow-md" : ""
      }`}
      onClick={onClick}
      whileHover={onClick ? { scale: 1.02 } : undefined}
      whileTap={onClick ? { scale: 0.98 } : undefined}
    >
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
        {onClick && (
          <ChevronRight className="h-4 w-4 ml-auto text-muted-foreground" />
        )}
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
        {onClick && (
          <p className="text-xs text-primary mt-1">Click for details</p>
        )}
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
    </motion.div>
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
  const [addActivityDialogOpen, setAddActivityDialogOpen] = React.useState(false);
  const [categoryFilter, setCategoryFilter] = React.useState<string>("all");
  
  // Crew Detail Modal state
  const [selectedCrewMember, setSelectedCrewMember] = React.useState<CrewMember | null>(null);
  const [crewDetailOpen, setCrewDetailOpen] = React.useState(false);
  
  // Performance Modal state (SMS matrices)
  const [perfModalMember, setPerfModalMember] = React.useState<CrewMemberForModal | null>(null);
  const [perfModalOpen, setPerfModalOpen] = React.useState(false);
  
  // PROGSS Checklist state
  const [progssStatuses, setProgssStatuses] = React.useState<Record<string, PROGSSCheckStatus>>({});
  const [missionDay, setMissionDay] = React.useState(1);

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
        fatigueLevel: Math.round(100 - currentSAFTEEffectiveness(Math.round(Math.random() * 3 * 10) / 10)),
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
      // Include role and status in the API payload for backend persistence
      const { role, status, ...profileData } = data;
      
      const updatedUser = await updateUser(editingMember.user.user_id, {
        ...editingMember.user,
        ...profileData,
        crew_role: role,
        crew_status: status,
      });

      setCrewMembers((prev) =>
        prev.map((m) =>
          m.id === editingMember.id
            ? {
                ...m,
                user: updatedUser,
                role: role,
                status: status as CrewMember["status"],
              }
            : m
        )
      );

      setUsers((prev) =>
        prev.map((u) =>
          u.user_id === editingMember.user.user_id ? updatedUser : u
        )
      );
      
      setEditingMember(null);
    } catch (error) {
      console.error("Failed to update crew member:", error);
      // Show error to user
      alert(`Failed to update profile: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
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

  // Add new activity
  const handleAddActivity = (activity: Omit<ScheduleActivity, "id">) => {
    const newActivity: ScheduleActivity = {
      ...activity,
      id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    };
    setActivities((prev) => {
      // Insert in sorted order by start time
      const updated = [...prev, newActivity];
      updated.sort((a, b) => a.startTime.localeCompare(b.startTime));
      return updated;
    });
  };

  // Update existing activity
  const handleUpdateActivity = (updatedActivity: ScheduleActivity) => {
    setActivities((prev) => {
      const updated = prev.map((a) =>
        a.id === updatedActivity.id ? updatedActivity : a
      );
      // Re-sort in case time changed
      updated.sort((a, b) => a.startTime.localeCompare(b.startTime));
      return updated;
    });
  };

  // Delete activity
  const handleDeleteActivity = (activityId: string) => {
    setActivities((prev) => prev.filter((a) => a.id !== activityId));
  };

  // Duplicate activity
  const handleDuplicateActivity = (activity: ScheduleActivity) => {
    const duplicated: ScheduleActivity = {
      ...activity,
      id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      title: `${activity.title} (Copy)`,
      status: "scheduled",
    };
    setActivities((prev) => {
      const updated = [...prev, duplicated];
      updated.sort((a, b) => a.startTime.localeCompare(b.startTime));
      return updated;
    });
  };

  // Open crew performance modal (SMS matrices)
  const handleCrewClick = (member: CrewMember) => {
    setPerfModalMember({
      id: member.user.user_id,
      name: member.user.full_name || member.user.username,
      role: member.role,
      status: member.status,
      ihpiScore: member.ihpiScore,
      fatigueLevel: member.fatigueLevel,
      sleepDebt: member.sleepDebt,
      readinessScore: member.readinessScore,
      sbp: member.user.resting_hr_bpm ? undefined : undefined, // Uses default in modal
      dbp: undefined,
      tempC: undefined,
      currentActivity: activities.find((a) =>
        a.status === "in_progress" && a.assignedCrew.includes(member.role),
      )?.title,
      activityCategory: activities.find((a) =>
        a.status === "in_progress" && a.assignedCrew.includes(member.role),
      )?.category,
    });
    setPerfModalOpen(true);
  };

  // Handle edit from crew detail modal
  const handleEditFromDetail = () => {
    if (selectedCrewMember) {
      setCrewDetailOpen(false);
      handleEditCrewMember(selectedCrewMember);
    }
  };

  // Update PROGSS checklist status
  const handleProgssStatusChange = (itemId: string, status: SemaphoreStatus, notes?: string) => {
    setProgssStatuses((prev) => ({
      ...prev,
      [itemId]: {
        itemId,
        status,
        notes,
        completedAt: status === "completed" ? new Date().toISOString() : prev[itemId]?.completedAt,
        completedBy: status === "completed" ? "Current User" : prev[itemId]?.completedBy,
      },
    }));
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
                      Real-time IHPI scores and operational status - Click any crew member for details
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {crewMembers.map((member) => (
                        <IHPIGauge
                          key={member.id}
                          member={member}
                          onClick={() => handleCrewClick(member)}
                        />
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

            {/* PROGSS Daily Checklist */}
            <div className="grid gap-6 lg:grid-cols-2">
              <PROGSSChecklist
                checkStatuses={progssStatuses}
                onStatusChange={handleProgssStatusChange}
                missionDay={missionDay}
              />
              
              {/* Mission Day Control */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calendar className="h-5 w-5" />
                    Mission Progress
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Current Mission Day</span>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => setMissionDay(Math.max(1, missionDay - 1))}
                        disabled={missionDay <= 1}
                      >
                        <Minus className="h-4 w-4" />
                      </Button>
                      <span className="text-2xl font-bold w-12 text-center">{missionDay}</span>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => setMissionDay(missionDay + 1)}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  
                  <Separator />
                  
                  {/* PROGSS Completion Summary */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-medium">Checklist Completion</h4>
                    {(() => {
                      const total = Object.keys(progssStatuses).length || 1;
                      const completed = Object.values(progssStatuses).filter(
                        (s) => s.status === "completed"
                      ).length;
                      const issues = Object.values(progssStatuses).filter(
                        (s) => s.status === "issue"
                      ).length;
                      const inProgress = Object.values(progssStatuses).filter(
                        (s) => s.status === "in_progress"
                      ).length;
                      const completionPct = total > 0 ? Math.round((completed / total) * 100) : 0;

                      return (
                        <>
                          <Progress value={completionPct} className="h-3" />
                          <div className="grid grid-cols-3 gap-2 text-center text-sm">
                            <div className="p-2 rounded bg-green-500/10">
                              <p className="font-bold text-green-600">{completed}</p>
                              <p className="text-xs text-muted-foreground">Completed</p>
                            </div>
                            <div className="p-2 rounded bg-yellow-500/10">
                              <p className="font-bold text-yellow-600">{inProgress}</p>
                              <p className="text-xs text-muted-foreground">In Progress</p>
                            </div>
                            <div className="p-2 rounded bg-red-500/10">
                              <p className="font-bold text-red-600">{issues}</p>
                              <p className="text-xs text-muted-foreground">Issues</p>
                            </div>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </CardContent>
              </Card>
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
                <Button onClick={() => setAddActivityDialogOpen(true)}>
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
                          onUpdate={handleUpdateActivity}
                          onDelete={handleDeleteActivity}
                          onDuplicate={handleDuplicateActivity}
                          crewMembers={crewMembers}
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
                  and physiological readiness - Click any crew member for full profile
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {crewMembers.map((member) => (
                    <IHPIGauge
                      key={member.id}
                      member={member}
                      onClick={() => handleCrewClick(member)}
                    />
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

      <AddActivityDialog
        open={addActivityDialogOpen}
        onOpenChange={setAddActivityDialogOpen}
        onAdd={handleAddActivity}
        crewMembers={crewMembers}
      />

      <CrewDetailModal
        member={selectedCrewMember}
        open={crewDetailOpen}
        onOpenChange={setCrewDetailOpen}
        onEdit={handleEditFromDetail}
      />

      <CrewPerformanceModal
        member={perfModalMember}
        open={perfModalOpen}
        onOpenChange={setPerfModalOpen}
      />
    </PageWrapper>
  );
}
