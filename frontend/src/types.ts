export type Screen =
  | "landing"
  | "login"
  | "register"
  | "dashboard"
  | "create-interview"
  | "text-interview"
  | "voice-interview"
  | "results"
  | "analytics"
  | "coach";

export const AUTHENTICATED_SCREENS: Screen[] = [
  "dashboard",
  "create-interview",
  "text-interview",
  "voice-interview",
  "results",
  "analytics",
  "coach",
];
