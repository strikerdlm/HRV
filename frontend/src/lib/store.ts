// Author: Dr Diego Malpica MD
/**
 * Global application state store using Zustand
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

/** Application mode - mirrors Python backend separation */
export type AppMode = "operational" | "research";

export interface RRTracingSelection {
  user_id: string;
  measurement_id: string;
  file_hash: string | null;
  source_file: string | null;
  selected_at: string;
}

interface AppState {
  // App mode - separates operational and research functionality
  appMode: AppMode;
  setAppMode: (mode: AppMode) => void;

  // Mission state
  activeMission: string;
  setActiveMission: (mission: string) => void;

  // Debug mode
  debugMode: boolean;
  setDebugMode: (enabled: boolean) => void;

  // Active user
  activeUserId: string | null;
  setActiveUserId: (userId: string | null) => void;

  // Globally selected RR tracing (applies across research pages)
  rrTracingSelection: RRTracingSelection | null;
  setRRTracingSelection: (selection: RRTracingSelection | null) => void;
  clearRRTracingSelection: () => void;

  // Sidebar state (sidebarOpen = !sidebarCollapsed for clarity)
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Notifications
  unreadNotifications: number;
  setUnreadNotifications: (count: number) => void;

  // Theme preference (for future use)
  theme: "light" | "dark" | "system";
  setTheme: (theme: "light" | "dark" | "system") => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // App mode - defaults to operational (mission control dashboard)
      appMode: "operational",
      setAppMode: (mode) => set({ appMode: mode }),

      // Mission state
      activeMission: "Mission 1",
      setActiveMission: (mission) => set({ activeMission: mission }),

      // Debug mode
      debugMode: false,
      setDebugMode: (enabled) => set({ debugMode: enabled }),

      // Active user
      activeUserId: null,
      setActiveUserId: (userId) => set({ activeUserId: userId }),

      // RR tracing selection
      rrTracingSelection: null,
      setRRTracingSelection: (selection) => set({ rrTracingSelection: selection }),
      clearRRTracingSelection: () => set({ rrTracingSelection: null }),

      // Sidebar state
      sidebarOpen: true,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      // Notifications
      unreadNotifications: 0,
      setUnreadNotifications: (count) => set({ unreadNotifications: count }),

      // Theme
      theme: "system",
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "mission-control-storage", // localStorage key
      storage: createJSONStorage(() => localStorage),
      // Only persist certain fields
      partialize: (state) => ({
        appMode: state.appMode,
        activeMission: state.activeMission,
        debugMode: state.debugMode,
        activeUserId: state.activeUserId,
        rrTracingSelection: state.rrTracingSelection,
        sidebarOpen: state.sidebarOpen,
        theme: state.theme,
      }),
    }
  )
);
