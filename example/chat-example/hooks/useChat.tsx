"use client";

import { ChatSendMessage, ChatSocketMessageBase } from "@/@types/chat";
import { ChatActionType, ChatActions } from "@/const/actions";
import { authAtom } from "@/store/authAtom";
import { chatAtom } from "@/store/chatAtom";
import { useAtom, useAtomValue } from "jotai";
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
    console.log("inviteUser", { roomId, userFrom, userTo });

    // TODO: user_id_from 타입 변경 필요
    sendSocketBase(ChatActions.USER_INVITE, {
      room_id: roomId,
      user_id_from: parseInt(userFrom, 10),
      user_name_to: userTo,
    });
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
  };
};

export const ChatProvider = ({ children }: PropsWithChildren) => {
  const [{ ws }, setChatState] = useAtom(chatAtom);
  const { token } = useAtomValue(authAtom);

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
            const { room_id, messages, users, notice } = data;

            setChatState((prev) => ({
              ...prev,
              roomId: room_id,
              users,
              notice,
              messages: messages.map((message) => ({
                type: "message",
                data: message,
              })),
            }));

            break;
          }
          case ChatActions.USER_JOIN: {
            setChatState((prev) => ({
              ...prev,
              users: prev.users.some(
                (prevUser) => prevUser.user_id === data.user.user_id
              )
                ? prev.users
                : [...prev.users, data.user],
              messages: [
                ...prev.messages,
                {
                  type: "notification",
                  data: {
                    enter: true,
                    user: data.user,
                  },
                },
              ],
            }));

            break;
          }
          case ChatActions.USER_LEAVE: {
            setChatState((prev) => ({
              ...prev,
              users: prev.users.filter(
                (prevUser) => prevUser.user_id !== data.user.user_id
              ),
              messages: [
                ...prev.messages,
                {
                  type: "notification",
                  data: {
                    enter: false,
                    user: data.user,
                  },
                },
              ],
            }));

            break;
          }
          case ChatActions.MESSAGE:
          case ChatActions.CONTROL: {
            setChatState((prev) => ({
              ...prev,
              messages: [
                ...prev.messages,
                {
                  type: "message",
                  data,
                },
              ],
            }));

            break;
          }
          case ChatActions.NOTICE: {
            setChatState((prev) => ({
              ...prev,
              notice: data.message,
            }));

            break;
          }
          case ChatActions.ERROR: {
            setChatState((prev) => ({
              ...prev,
              error: data,
            }));

            break;
          }
          case ChatActions.ROOM_CREATE: {
            alert(data.message);

            break;
          }
          case ChatActions.LOBBY_REFRESH: {
            const lobbyRoomList = data.sort(
              (a, b) => b.current_users - a.current_users
            );

            setChatState((prev) => ({
              ...prev,
              lobbyRoomList,
            }));

            break;
          }
          case ChatActions.USER_INVITE: {
            setChatState((prev) => ({
              ...prev,
              inviteMessage: data,
            }));

            break;
          }
          default: {
            setChatState((prev) => ({
              ...prev,
              error: {
                code: 0,
                reason: `Unhandled action: ${action}`,
              },
            }));

            break;
          }
        }
      };
    },
    [setChatState]
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
