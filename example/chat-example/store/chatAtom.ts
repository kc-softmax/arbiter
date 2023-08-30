import {
  ChatError,
  ChatMessageListData,
  ChatSocketMessageBase,
  LobbyRefreshData,
  UserInfo,
} from "@/@types/chat";
import { atom } from "jotai";

interface ChatAtom {
  ws: WebSocket | null;
  roomId: string;
  notice: string | null;
  messages: ChatMessageListData[];
  users: UserInfo[];
  error: ChatError | null;
  eventMessage: ChatSocketMessageBase | null;
  lobbyRoomList: LobbyRefreshData[];
}

export const chatAtom = atom<ChatAtom>({
  ws: null,
  roomId: "",
  notice: null,
  messages: [],
  users: [],
  error: null,
  eventMessage: null,
  lobbyRoomList: [],
});
