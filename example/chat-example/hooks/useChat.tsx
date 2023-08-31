"use client";

import {
  ChatSendMessage,
  ChatSocketMessageBase,
  LikeOrDislike,
} from "@/@types/chat";
import { ChatActionType, ChatActions } from "@/const/actions";
import { authAtom } from "@/store/authAtom";
import {
  chatAddMessageAtom,
  chatAtom,
  chatRoomJoinAtom,
  chatSetErrorAtom,
  chatSetInviteUserAtom,
  chatSetLobbyAtom,
  chatSetNoticeAtom,
  chatUpdateLikesAtom,
  chatUserJoinAtom,
  chatUsesrLeaveAtom,
} from "@/store/chatAtom";
import { useAtom, useAtomValue, useSetAtom } from "jotai";
import { PropsWithChildren, useCallback, useEffect } from "react";

const HostAddress = process.env.NEXT_PUBLIC_HOST;

export const useChat = () => {
  const {
    error,
    eventMessage,
    messages,
    notice,
    roomId,
    users,
    ws,
    lobbyRoomList,
    inviteMessage,
  } = useAtomValue(chatAtom);

  const sendSocketBase = <T extends object>(
    action: ChatActionType,
    data: T
  ) => {
    const chatData: {
      action: ChatActionType;
      data: T;
    } = {
      action,
      data,
    };

    ws?.send(JSON.stringify(chatData));
  };

  const sendMessage = ({ message, user_id }: ChatSendMessage["data"]) => {
    sendSocketBase(ChatActions.MESSAGE, {
      message,
      user_id,
    });
  };

  const createRoom = (nextRoomId: string, maxUsers: number = 8) => {
    if (roomId === nextRoomId) return;

    sendSocketBase(ChatActions.ROOM_CREATE, {
      room_id: nextRoomId,
      max_users: maxUsers,
    });
  };

  const changeRoom = (nextRoomId: string) => {
    if (roomId === nextRoomId) return;

    sendSocketBase(ChatActions.ROOM_CHANGE, {
      room_id: nextRoomId,
    });
  };

  const sendNotice = (message: string, userId: string) => {
    sendSocketBase(ChatActions.NOTICE, {
      message,
      user_id: userId,
    });
  };

  const refreshLobby = () => {
    sendSocketBase(ChatActions.LOBBY_REFRESH, {});
  };

  const inviteUser = ({
    userFrom,
    userTo,
  }: {
    userFrom: string;
    userTo: string;
  }) => {
    // TODO: user_id_from의 타입 변경 필요
    sendSocketBase(ChatActions.USER_INVITE, {
      room_id: roomId,
      user_id_from: parseInt(userFrom, 10),
      user_name_to: userTo,
    });
  };

  const sendLike = (messageId: number, type: LikeOrDislike) => {
    console.log("sendLike", { messageId, type });

    // TODO: 서버 연동 후 구현 필요
    // sendSocketBase(ChatActions.MESSAGE_LIKE, {
    //   message_id: messageId,
    //   type,
    // });
  };

  return {
    data: {
      roomId,
      notice,
      messages,
      users,
      lobbyRoomList,
    },
    inviteMessage,
    error,
    eventMessage,
    sendMessage,
    createRoom,
    changeRoom,
    sendNotice,
    refreshLobby,
    inviteUser,
    sendLike,
  };
};

export const ChatProvider = ({ children }: PropsWithChildren) => {
  const [{ ws }, setChatState] = useAtom(chatAtom);
  const { token } = useAtomValue(authAtom);

  const setRoomData = useSetAtom(chatRoomJoinAtom);
  const addMessage = useSetAtom(chatAddMessageAtom);
  const addUser = useSetAtom(chatUserJoinAtom);
  const removeUser = useSetAtom(chatUsesrLeaveAtom);
  const setNotice = useSetAtom(chatSetNoticeAtom);
  const setError = useSetAtom(chatSetErrorAtom);
  const setLobbyRoomList = useSetAtom(chatSetLobbyAtom);
  const setInviteUser = useSetAtom(chatSetInviteUserAtom);
  const updateLike = useSetAtom(chatUpdateLikesAtom);

  const join = useCallback(
    (ws: WebSocket) => {
      ws.onopen = () => {
        console.log("Chat connected");
      };

      ws.onclose = (event) => {
        console.log("Chat disconnected", event);
        alert(event.reason || "Chat disconnected");
      };

      ws.onmessage = (event) => {
        const chatSocketMessage: ChatSocketMessageBase = JSON.parse(event.data);
        const { action, data } = chatSocketMessage;
        console.log(
          "🚀 ~ file: useChat.tsx:46 ~ join ~ chatSocketMessage:",
          chatSocketMessage
        );

        setChatState((prev) => ({
          ...prev,
          eventMessage: chatSocketMessage,
          error: null,
          inviteMessage: null,
        }));

        switch (action) {
          case ChatActions.ROOM_JOIN: {
            setRoomData(data);
            break;
          }
          case ChatActions.USER_JOIN: {
            addUser(data.user);
            break;
          }
          case ChatActions.USER_LEAVE: {
            removeUser(data.user);
            break;
          }
          case ChatActions.MESSAGE:
          case ChatActions.CONTROL: {
            addMessage(data);
            break;
          }
          case ChatActions.NOTICE: {
            setNotice(data.message);
            break;
          }
          case ChatActions.ERROR: {
            setError(data);
            break;
          }
          case ChatActions.ROOM_CREATE: {
            alert(data.message);
            break;
          }
          case ChatActions.LOBBY_REFRESH: {
            setLobbyRoomList(data);
            break;
          }
          case ChatActions.USER_INVITE: {
            setInviteUser(data);
            break;
          }
          case ChatActions.MESSAGE_LIKE: {
            updateLike(data);
            break;
          }
          default: {
            setError({
              code: 0,
              reason: `Unhandled action: ${action}`,
            });

            break;
          }
        }
      };
    },
    [
      setRoomData,
      setChatState,
      addMessage,
      addUser,
      removeUser,
      setNotice,
      setError,
      setLobbyRoomList,
      setInviteUser,
      updateLike,
    ]
  );

  useEffect(() => {
    if (!HostAddress) {
      throw new Error("Host Address is not defined");
    }

    if (!ws) {
      const websocketAddress = HostAddress.replace(/^https?/, "ws");
      const ws = new WebSocket(`${websocketAddress}/chat/ws?token=${token}`);

      setChatState((prev) => ({
        ...prev,
        ws,
      }));

      join(ws);
    }

    return () => {
      ws?.close();
    };
  }, [token, ws, setChatState, join]);

  return <>{children}</>;
};
