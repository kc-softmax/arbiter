export const ChatActions = {
  ROOM_JOIN: "room_join",
  USER_JOIN: "user_join",
  USER_LEAVE: "user_leave",
  ERROR: "error",
  MESSAGE: "message",
  CONTROL: "control",
  ROOM_CHANGE: "room_change",
} as const;

export type ChatActionType = (typeof ChatActions)[keyof typeof ChatActions];

export const ChatTabList = {
  ALL: "all",
  PARTY: "party",
} as const;

export type ChatTabType = (typeof ChatTabList)[keyof typeof ChatTabList];
