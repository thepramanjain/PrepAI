export type Screen =
  | "landing"
  | "login"
  | "register"
  | "dashboard"
  | "create-interview"
  | "text-interview"
  | "voice-interview"
  | "results"
  | "analytics";

export const AUTHENTICATED_SCREENS: Screen[] = [
  "dashboard",
  "create-interview",
  "text-interview",
  "voice-interview",
  "results",
  "analytics",
];
