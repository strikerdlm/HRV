// Author: Dr Diego Malpica MD
/**
 * Global application state store using Zustand
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface AppState {
  // Mission state
  activeMission: string;
  setActiveMission: (mission: string) => void;

  // Debug mode
  debugMode: boolean;
  setDebugMode: (enabled: boolean) => void;

  // Active user
  activeUserId: string | null;
  setActiveUserId: (userId: string | null) => void;

  // Sidebar state
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

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
      // Mission state
      activeMission: "Mission 1",
      setActiveMission: (mission) => set({ activeMission: mission }),

      // Debug mode
      debugMode: false,
      setDebugMode: (enabled) => set({ debugMode: enabled }),

      // Active user
      activeUserId: null,
      setActiveUserId: (userId) => set({ activeUserId: userId }),

      // Sidebar state
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

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
        activeMission: state.activeMission,
        debugMode: state.debugMode,
        activeUserId: state.activeUserId,
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
      }),
    }
  )
);
