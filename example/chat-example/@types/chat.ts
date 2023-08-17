import { ChatActions } from "@/const/actions";

export interface ChatInfo {
  id: string;
  token: string;
}

export interface ChatMessage {
  user: string;
  message: string;
  time: string;
}

export interface RoomJoinData {
  room_id: string;
  messages: ChatMessage[];
  users: string[];
}

export interface UserJoinData {
  user: string;
}

export interface UserLeaveData {
  user: string;
}

export interface ChatSocketMessageRoomJoin {
  action: typeof ChatActions.ROOM_JOIN;
  data: RoomJoinData;
}

export interface ChatSocketMessageUserJoin {
  action: typeof ChatActions.USER_JOIN;
  data: UserJoinData;
}

export interface ChatSocketMessageUserLeave {
  action: typeof ChatActions.USER_LEAVE;
  data: UserLeaveData;
}

export interface ChatSocketMessage {
  action: typeof ChatActions.MESSAGE | typeof ChatActions.CONTROL;
  data: ChatMessage;
}

export type ChatSocketMessageBase =
  | ChatSocketMessageRoomJoin
  | ChatSocketMessageUserJoin
  | ChatSocketMessageUserLeave
  | ChatSocketMessage;

export interface ChatSendMessage {
  action: typeof ChatActions.MESSAGE;
  data: Pick<ChatMessage, "message">;
}
