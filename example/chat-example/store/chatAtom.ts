import {
  ChatError,
  ChatMessageItem,
  ChatItem,
  ChatSocketMessageBase,
  InviteUserData,
  LobbyRefreshData,
  MessageLikeData,
  UserInfo,
  MessageData,
  ChatNotificationItem,
  RoomJoinData,
} from "@/@types/chat";
import { atom } from "jotai";

interface ChatAtom {
  ws: WebSocket | null;
  roomId: string;
  notice: string | null;
  messages: ChatItem[];
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

const chatbotMessage: ChatItem = {
  type: "message",
  data: {
    user: {
      user_id: 6,
      user_name: "Chatbot",
    },
    message_id: 999,
    message: "Welcome to Chat!",
    time: new Date().toISOString(),
    like: 7,
  },
};
const chatbotMessage2: ChatItem = {
  type: "message",
  data: {
    user: {
      user_id: 999,
      user_name: "Chatbot",
    },
    message_id: 9999,
    message: "Welcome to Chat! It's me mario!",
    time: new Date().toISOString(),
    like: 7,
  },
};

export const chatSetEventMessageAtom = atom<
  null,
  [ChatSocketMessageBase],
  void
>(null, (get, set, eventMessage) => {
  set(chatAtom, {
    ...get(chatAtom),
    eventMessage,
    error: null,
    inviteMessage: null,
  });
});

export const chatRoomJoinAtom = atom<null, [RoomJoinData], void>(
  null,
  (get, set, data) => {
    const { room_id, messages, ...props } = data;

    const userMessages = messages.map((message) => ({
      type: "message",
      data: message,
    })) satisfies ChatMessageItem[];

    userMessages.unshift(chatbotMessage, chatbotMessage2),
      set(chatAtom, {
        ...get(chatAtom),
        roomId: room_id,
        messages: userMessages,
        ...props,
      });
  }
);

export const chatUserJoinAtom = atom<null, [UserInfo], void>(
  null,
  (get, set, data) => {
    const users = get(chatAtom).users.slice();
    const messages = get(chatAtom).messages.slice();

    if (users.some((user) => user.user_id === data.user_id)) return;

    const notificationMessage = {
      type: "notification",
      data: {
        enter: true,
        user: data,
      },
    } satisfies ChatNotificationItem;

    users.push(data);
    messages.push(notificationMessage);

    set(chatAtom, {
      ...get(chatAtom),
      users,
      messages,
    });
  }
);

export const chatUsesrLeaveAtom = atom<null, [UserInfo], void>(
  null,
  (get, set, data) => {
    const users = get(chatAtom).users.slice();
    const messages = get(chatAtom).messages.slice();

    const notificationMessage = {
      type: "notification",
      data: {
        enter: false,
        user: data,
      },
    } satisfies ChatNotificationItem;

    const targetUserIndex = users.findIndex(
      (user) => user.user_id === data.user_id
    );

    users.splice(targetUserIndex, 1);
    messages.push(notificationMessage);

    set(chatAtom, {
      ...get(chatAtom),
      users,
      messages,
    });
  }
);

export const chatAddMessageAtom = atom<null, [MessageData], void>(
  null,
  (get, set, data) => {
    const messages = get(chatAtom).messages.slice();

    messages.push({
      type: "message",
      data,
    });

    set(chatAtom, {
      ...get(chatAtom),
      messages,
    });
  }
);

export const chatSetNoticeAtom = atom<null, [string], void>(
  null,
  (get, set, notice) => {
    set(chatAtom, {
      ...get(chatAtom),
      notice,
    });
  }
);

export const chatSetErrorAtom = atom<null, [ChatError], void>(
  null,
  (get, set, error) => {
    set(chatAtom, {
      ...get(chatAtom),
      error,
    });
  }
);

export const chatSetLobbyAtom = atom<null, [LobbyRefreshData[]], void>(
  null,
  (get, set, lobbyRoomListData) => {
    const roomId = get(chatAtom).roomId;
    const lobbyRoomList = lobbyRoomListData.sort((a, b) => {
      if (a.room_id === roomId) return -1;
      if (b.room_id === roomId) return 1;
      return a.current_users - b.current_users;
    });

    set(chatAtom, {
      ...get(chatAtom),
      lobbyRoomList,
    });
  }
);

export const chatSetInviteUserAtom = atom<null, [InviteUserData], void>(
  null,
  (get, set, inviteMessage) => {
    set(chatAtom, {
      ...get(chatAtom),
      inviteMessage,
    });
  }
);

export const chatUpdateLikesAtom = atom<null, [MessageLikeData], void>(
  null,
  (get, set, { like, message_id }) => {
    const messages = get(chatAtom).messages.slice();

    const targetMessageIndex = messages.findIndex(
      (message) =>
        message.type === "message" && message.data.message_id === message_id
    );

    const messageWithLikes = {
      ...messages[targetMessageIndex],
      data: {
        ...messages[targetMessageIndex].data,
        like,
      },
    } as ChatMessageItem;

    messages.splice(targetMessageIndex, 1, messageWithLikes);

    set(chatAtom, {
      ...get(chatAtom),
      messages,
    });
  }
);
