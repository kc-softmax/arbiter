"use client";

import {
  ChatError,
  ChatMessageListData,
  ChatSendMessage,
  ChatSocketMessageBase,
  UserInfo,
} from "@/@types/chat";
import { ChatActionType, ChatActions } from "@/const/actions";
import { useEffect, useRef, useState } from "react";

const HostAddress = process.env.NEXT_PUBLIC_HOST;

export const useChat = (token: string) => {
  const [roomId, setRoomId] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageListData[]>([]);
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [error, setError] = useState<ChatError | null>(null);
  // 가장 최근의 이벤트 메시지
  const [eventMessage, setEventMessage] = useState<ChatSocketMessageBase>();

  const wsRef = useRef<WebSocket>();

  const join = () => {
    const ws = wsRef.current;

    if (!ws) {
      return alert("WebSocket is not connected");
    }

    ws.onopen = () => {
      console.log("Chat connected");
    };

    ws.onclose = (event) => {
      console.log("Chat disconnected", event);
      if (event.code === 3000) {
        alert("Invalid Token");
        location.reload();
      }
    };

    ws.onmessage = (event) => {
      const chatSocketMessage: ChatSocketMessageBase = JSON.parse(event.data);
      const { action, data } = chatSocketMessage;
      console.log(
        "🚀 ~ file: useChat.tsx:46 ~ join ~ chatSocketMessage:",
        chatSocketMessage
      );

      setEventMessage(chatSocketMessage);

      switch (action) {
        case ChatActions.ROOM_JOIN: {
          const { room_id, messages, users, notice } = data;

          setRoomId(room_id);
          setUsers(users);
          setNotice(notice);
          setMessages(
            messages.map((message) => ({
              type: "message",
              data: message,
            }))
          );
          break;
        }
        case ChatActions.USER_JOIN: {
          setUsers((prev) =>
            prev.some((prevUser) => prevUser.user_id === data.user.user_id)
              ? prev
              : [...prev, data.user]
          );

          setMessages((prev) => [
            ...prev,
            {
              type: "notification",
              data: {
                enter: true,
                user: data.user,
              },
            },
          ]);
          break;
        }
        case ChatActions.USER_LEAVE: {
          setUsers((prev) =>
            prev.filter((prevUser) => prevUser.user_id !== data.user.user_id)
          );

          setMessages((prev) => [
            ...prev,
            {
              type: "notification",
              data: {
                enter: false,
                user: data.user,
              },
            },
          ]);
          break;
        }
        case ChatActions.MESSAGE:
        case ChatActions.CONTROL: {
          setMessages((prev) => [
            ...prev,
            {
              type: "message",
              data,
            },
          ]);
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
        default: {
          setError({
            code: 0,
            reason: `Unhandled action: ${action}`,
          });
          break;
        }
      }
    };
  };

  const sendSocketBase = <T extends object>(
    action: ChatActionType,
    data: T
  ) => {
    const ws = wsRef.current;

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

  const changeRoom = (nextRoomId: string) => {
    if (roomId === nextRoomId) return;

    sendSocketBase(ChatActions.ROOM_CHANGE, {
      room_id: nextRoomId,
    });
  };

  const sendNotice = ({ message, user_id }: ChatSendMessage["data"]) => {
    sendSocketBase(ChatActions.NOTICE, {
      message,
      user_id,
    });
  };

  useEffect(() => {
    if (!HostAddress) {
      throw new Error("Host Address is not defined");
    }

    if (!wsRef.current) {
      const websocketAddress = HostAddress.replace(/^https?/, "ws");
      wsRef.current = new WebSocket(
        `${websocketAddress}/chat/ws?token=${token}`
      );
    }

    join();

    return () => {
      wsRef.current?.close();
    };
  }, [token]);

  return {
    data: {
      roomId,
      notice,
      messages,
      users,
    },
    error,
    eventMessage,
    sendMessage,
    changeRoom,
    sendNotice,
  };
};
