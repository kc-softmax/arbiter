import { ChatActions } from "@/const/actions";

export interface AuthInfo {
  id: string;
  username: string;
  token: string;
}

export interface UserInfo {
  user_id: number;
  user_name: string;
}

export interface ChatMessage {
  user: UserInfo;
  message_id: number;
  message: string;
  time: string;
}

export interface RoomJoinData {
  room_id: string;
  messages: ChatMessage[];
  users: UserInfo[];
}

export interface UserJoinData {
  user: UserInfo;
}

export interface UserLeaveData {
  user: UserInfo;
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
  data: {
    message: string;
    user_id: string;
  };
}

export interface ChatSendChangeRoom {
  action: typeof ChatActions.ROOM_CHANGE;
  data: {
    room_id: string;
  };
}
