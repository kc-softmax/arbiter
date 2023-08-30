import {
  ChatError,
  ChatMessageList,
  ChatSocketMessageBase,
  InviteUserData,
  LobbyRefreshData,
  UserInfo,
} from "@/@types/chat";
import { atom } from "jotai";

interface ChatAtom {
  ws: WebSocket | null;
  roomId: string;
  notice: string | null;
  messages: ChatMessageList[];
  users: UserInfo[];
  error: ChatError | null;
  eventMessage: ChatSocketMessageBase | null;
  lobbyRoomList: LobbyRefreshData[];
  inviteMessage: InviteUserData | null;
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
  inviteMessage: null,
});

export const chatResetInviteMessageAtom = atom(null, (get, set) => {
  set(chatAtom, {
    ...get(chatAtom),
    inviteMessage: null,
  });
});

export const chatResetErrorAtom = atom(null, (get, set) => {
  set(chatAtom, {
    ...get(chatAtom),
    error: null,
  });
});
