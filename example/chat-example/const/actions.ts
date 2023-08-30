export const ChatActions = {
  ROOM_JOIN: "room_join",
  USER_JOIN: "user_join",
  USER_LEAVE: "user_leave",
  ERROR: "error",
  MESSAGE: "message",
  CONTROL: "control",
  ROOM_CHANGE: "room_change",
  NOTICE: "notice",
  ROOM_CREATE: "room_create",
  LOBBY_REFRESH: "lobby_refresh",
  USER_INVITE: "user_invite",
} as const;

export type ChatActionType = (typeof ChatActions)[keyof typeof ChatActions];
