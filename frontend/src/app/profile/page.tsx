// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  User,
  Plus,
  Trash2,
  Heart,
  Activity,
  Scale,
  Ruler,
  Calendar,
  Globe,
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
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { listUsers, createUser, deleteUser } from "@/lib/api";
import type { UserProfile } from "@/types";
import { formatDate, formatWithUnit } from "@/lib/utils";
import { useAppStore } from "@/lib/store";

function UserCard({
  user,
  isSelected,
  onSelect,
  onDelete,
}: {
  user: UserProfile;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      layout
    >
      <Card
        className={`cursor-pointer transition-all ${
          isSelected ? "ring-2 ring-primary" : "hover:bg-accent/50"
        }`}
        onClick={onSelect}
      >
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <span className="text-lg font-bold text-primary">
                  {(user.full_name || user.username).charAt(0).toUpperCase()}
                </span>
              </div>
              <div>
                <h4 className="font-medium">{user.full_name || user.username}</h4>
                <p className="text-sm text-muted-foreground">@{user.username}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="text-muted-foreground hover:text-danger"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="outline" className="capitalize">
              {user.sex}
            </Badge>
            <Badge variant="outline">
              <Globe className="h-3 w-3 mr-1" />
              {user.language.toUpperCase()}
            </Badge>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function ProfileDetails({ user }: { user: UserProfile | null }) {
  if (!user) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full min-h-[400px]">
          <div className="text-center">
            <User className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              Select a profile to view details
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-4">
          <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
            <span className="text-2xl font-bold text-primary">
              {(user.full_name || user.username).charAt(0).toUpperCase()}
            </span>
          </div>
          <div>
            <CardTitle>{user.full_name || user.username}</CardTitle>
            <CardDescription>@{user.username}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Basic Info */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">
              Sex
            </p>
            <p className="font-medium capitalize">{user.sex}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">
              Language
            </p>
            <p className="font-medium">{user.language.toUpperCase()}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">
              Date of Birth
            </p>
            <p className="font-medium">{formatDate(user.date_of_birth)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">
              Email
            </p>
            <p className="font-medium">{user.email || "Not set"}</p>
          </div>
        </div>

        <Separator />

        {/* Biometrics */}
        <div>
          <h4 className="font-medium mb-3 flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Biometrics
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Ruler className="h-4 w-4" />
                <span className="text-xs">Height</span>
              </div>
              <p className="font-semibold">
                {formatWithUnit(user.height_cm, "cm", 0)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Scale className="h-4 w-4" />
                <span className="text-xs">Weight</span>
              </div>
              <p className="font-semibold">
                {formatWithUnit(user.weight_kg, "kg", 1)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Heart className="h-4 w-4" />
                <span className="text-xs">Resting HR</span>
              </div>
              <p className="font-semibold">
                {formatWithUnit(user.resting_hr_bpm, "bpm", 0)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Activity className="h-4 w-4" />
                <span className="text-xs">VO2max</span>
              </div>
              <p className="font-semibold">
                {formatWithUnit(user.vo2max_ml_kg_min, "ml/kg/min", 1)}
              </p>
            </div>
          </div>
        </div>

        <Separator />

        {/* Metadata */}
        <div className="text-xs text-muted-foreground">
          <p>Created: {formatDate(user.created_at)}</p>
          <p>Updated: {formatDate(user.updated_at)}</p>
          <p>ID: {user.user_id}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function NewUserForm({
  onSubmit,
}: {
  onSubmit: (data: { username: string; fullName: string; sex: string }) => void;
}) {
  const [username, setUsername] = React.useState("");
  const [fullName, setFullName] = React.useState("");
  const [sex, setSex] = React.useState("other");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;
    onSubmit({ username, fullName, sex });
    setUsername("");
    setFullName("");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plus className="h-5 w-5" />
          New Profile
        </CardTitle>
        <CardDescription>Add a new crew member profile</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Username *</label>
            <Input
              placeholder="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Full Name</label>
            <Input
              placeholder="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Sex</label>
            <Select value={sex} onValueChange={setSex}>
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
          <Button type="submit" className="w-full">
            <Plus className="h-4 w-4 mr-2" />
            Create Profile
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function ProfilePage() {
  const [users, setUsers] = React.useState<UserProfile[]>([]);
  const { selectedUserId, setSelectedUserId } = useAppStore();
  const [loading, setLoading] = React.useState(true);

  const selectedUser = users.find((u) => u.user_id === selectedUserId) || null;

  const fetchUsers = async () => {
    try {
      const data = await listUsers();
      setUsers(data.users);
    } catch (error) {
      console.error("Failed to fetch users:", error);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreate = async (data: {
    username: string;
    fullName: string;
    sex: string;
  }) => {
    try {
      await createUser({
        username: data.username,
        full_name: data.fullName || undefined,
        sex: data.sex as any,
      });
      await fetchUsers();
    } catch (error) {
      console.error("Failed to create user:", error);
    }
  };

  const handleDelete = async (userId: string) => {
    try {
      await deleteUser(userId);
      if (selectedUserId === userId) {
        setSelectedUserId(null);
      }
      await fetchUsers();
    } catch (error) {
      console.error("Failed to delete user:", error);
    }
  };

  return (
    <PageWrapper title="User Profiles" description="Manage crew member profiles">
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Users List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Profiles ({users.length})</h3>
          </div>
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
            {users.map((user) => (
              <UserCard
                key={user.user_id}
                user={user}
                isSelected={selectedUserId === user.user_id}
                onSelect={() => setSelectedUserId(user.user_id)}
                onDelete={() => handleDelete(user.user_id)}
              />
            ))}
          </div>
          <NewUserForm onSubmit={handleCreate} />
        </motion.div>

        {/* Profile Details */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2"
        >
          <ProfileDetails user={selectedUser} />
        </motion.div>
      </div>
    </PageWrapper>
  );
}
