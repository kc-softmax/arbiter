export const ChatActions = {
  ROOM_JOIN: "room_join",
  USER_JOIN: "user_join",
  USER_LEAVE: "user_leave",
  ERROR: "error",
  MESSAGE: "message",
  CONTROL: "control",
} as const;

export type ChatActionType = (typeof ChatActions)[keyof typeof ChatActions];
