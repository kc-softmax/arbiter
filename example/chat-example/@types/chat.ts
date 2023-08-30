import { ChatActions } from "@/const/actions";

// SECTION: Common Types

export interface AuthInfo {
  id: string;
  token: string;
}

export interface UserInfo {
  user_id: number;
  user_name: string;
}

// SECTION: Data from Socket

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
  number_of_users: number;
  notice: string;
}

export interface UserJoinData {
  user: UserInfo;
}

export interface UserLeaveData {
  user: UserInfo;
}

export interface LobbyRefreshData {
  room_id: string;
  current_users: number;
  max_users: number;
}

export interface InviteUserData {
  room_id: string;
  user_name_from: string;
}

export interface ChatError {
  code: number;
  reason: string;
}

// SECTION: Socket Message

export interface ChatSocketMessageRoomCreate {
  action: typeof ChatActions.ROOM_CREATE;
  data: {
    message: string;
  };
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

export interface ChatSocketMessageNotice {
  action: typeof ChatActions.NOTICE;
  data: {
    message: string;
  };
}

export interface ChatSocketMessageLobbyRefresh {
  action: typeof ChatActions.LOBBY_REFRESH;
  data: LobbyRefreshData[];
}

export interface ChatSocketMessageInviteUser {
  action: typeof ChatActions.USER_INVITE;
  data: InviteUserData;
}

export interface ChatSocketMessageError {
  action: typeof ChatActions.ERROR;
  data: ChatError;
}

export type ChatSocketMessageBase =
  | ChatSocketMessageRoomCreate
  | ChatSocketMessageRoomJoin
  | ChatSocketMessageUserJoin
  | ChatSocketMessageUserLeave
  | ChatSocketMessageError
  | ChatSocketMessage
  | ChatSocketMessageNotice
  | ChatSocketMessageLobbyRefresh
  | ChatSocketMessageInviteUser;

// SECTION: Client used Data types

export interface ChatMessageData {
  type: "message";
  data: ChatMessage;
}

export interface ChatNotificationData {
  type: "notification";
  data: {
    enter: boolean;
    user: UserInfo;
  };
}

export type ChatMessageList = ChatMessageData | ChatNotificationData;

export interface ChatSendMessage {
  action: typeof ChatActions.MESSAGE;
  data: {
    message: string;
    user_id: string;
  };
}
