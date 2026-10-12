// import { create } from "zustand";
// import { persist, createJSONStorage } from "zustand/middleware";

// export type UserRole = "owner" | "counselor" | "tutor" | "parent" | "student";

// export interface AuthUser {
//   id:          string;
//   email:       string;
//   first_name?: string;
//   last_name?:  string;
//   role:        UserRole;
//   tenant_id:   string;
// }

// interface AuthState {
//   accessToken:  string | null;
//   refreshToken: string | null;
//   // Display-only state — safe to persist in localStorage
//   user:     AuthUser | null;
//   tenantId: string | null;
//   role:     UserRole | null;

//   // Actions
//   setUser:  (user: AuthUser) => void;
//   setAuth:  (access: string, refresh: string, user: AuthUser) => void;
//   clear:    () => void;
// }

// export const useAuthStore = create<AuthState>()(
//   persist(
//     (set) => ({
//       accessToken:  null,
//       refreshToken: null,
//       user:     null,
//       tenantId: null,
//       role:     null,

//       setAuth: (access, refresh, user) => set({ accessToken: access, refreshToken: refresh, user, tenantId: user.tenant_id, role: user.role }),

//       setUser: (user) =>
//         set({
//           user,
//           tenantId: user.tenant_id,
//           role:     user.role,
//         }),

//       clear: () =>
//         set({
//           accessToken:  null,
//           refreshToken: null,
//           user:     null,
//           tenantId: null,
//           role:     null,
//         }),
//     }),
//     {
//       name: "coachgenie-ui",   // renamed key — forces clean slate on deploy
//       storage: createJSONStorage(() =>
//         typeof window !== "undefined" ? localStorage : ({} as Storage)
//       ),
//       // Only persist display fields — never tokens
//       partialize: (state) => ({
//         user:     state.user,
//         tenantId: state.tenantId,
//         role:     state.role,
//       }),
//     }
//   )
// );





import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type UserRole =
  | "super_admin"
  | "owner"
  | "admin"
  | "counselor"
  | "tutor"
  | "coach"
  | "parent"
  | "student";

export interface AuthUser {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: UserRole;
  tenant_id: string;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;

  user: AuthUser | null;
  tenantId: string | null;
  role: UserRole | null;

  /** True once Zustand Persist has restored localStorage */
  hydrated: boolean;

  setHydrated: () => void;

  setUser: (user: AuthUser) => void;
  setAuth: (
    access: string,
    refresh: string,
    user: AuthUser
  ) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,

      user: null,
      tenantId: null,
      role: null,

      hydrated: false,

      setHydrated: () =>
        set({
          hydrated: true,
        }),

      setAuth: (access, refresh, user) =>
        set({
          accessToken: access,
          refreshToken: refresh,
          user,
          tenantId: user.tenant_id,
          role: user.role,
        }),

      setUser: (user) =>
        set({
          user,
          tenantId: user.tenant_id,
          role: user.role,
        }),

      clear: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          tenantId: null,
          role: null,
        }),
    }),
    {
      name: "coachgenie-ui",

      storage: createJSONStorage(() =>
        typeof window !== "undefined"
          ? localStorage
          : ({} as Storage)
      ),

      partialize: (state) => ({
        user: state.user,
        tenantId: state.tenantId,
        role: state.role,
      }),

      onRehydrateStorage: () => (state) => {
        state?.setHydrated();
      },
    }
  )
);