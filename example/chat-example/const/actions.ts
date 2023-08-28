export const ChatActions = {
  ROOM_JOIN: "room_join",
  USER_JOIN: "user_join",
  USER_LEAVE: "user_leave",
  ERROR: "error",
  MESSAGE: "message",
  CONTROL: "control",
  ROOM_CHANGE: "room_change",
  NOTICE: "notice",
} as const;

export type ChatActionType = (typeof ChatActions)[keyof typeof ChatActions];
