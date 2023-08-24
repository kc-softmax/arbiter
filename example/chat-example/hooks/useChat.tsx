"use client";

import {
  ChatMessage,
  ChatSendMessage,
  ChatSocketMessageBase,
  UserInfo,
} from "@/@types/chat";
import { ChatActionType, ChatActions } from "@/const/actions";
import { useEffect, useRef, useState } from "react";

const wsHost = process.env.NEXT_PUBLIC_CHAT_WEBSOCKET_URL;

export const useChat = (token: string) => {
  const [roomId, setRoomId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [users, setUsers] = useState<UserInfo[]>([]);
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

      if (action === ChatActions.ROOM_JOIN) {
        const { room_id, messages, users } = data;

        setRoomId(room_id);
        setMessages(messages);
        setUsers(users);
      }

      if (action === ChatActions.USER_JOIN) {
        setUsers((prev) =>
          prev.some((prevUser) => prevUser.user_id === data.user.user_id)
            ? prev
            : [...prev, data.user]
        );
      }

      if (action === ChatActions.USER_LEAVE) {
        setUsers((prev) =>
          prev.filter((prevUser) => prevUser.user_id !== data.user.user_id)
        );
      }

      if (action === ChatActions.MESSAGE || action === ChatActions.CONTROL) {
        setMessages((prev) => [...prev, data]);
      }

      setEventMessage(chatSocketMessage);
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

  const changeRoom = (roomId: string) => {
    sendSocketBase(ChatActions.ROOM_CHANGE, {
      room_id: roomId,
    });
  };

  useEffect(() => {
    if (!wsHost) {
      throw new Error("NEXT_PUBLIC_CHAT_WEBSOCKET_URL is not defined");
    }

    if (!wsRef.current) {
      wsRef.current = new WebSocket(`${wsHost}?token=${token}`);
    }

    join();

    return () => {
      wsRef.current?.close();
    };
  }, [token]);

  return {
    data: {
      roomId,
      messages,
      users,
    },
    sendMessage,
    changeRoom,
    eventMessage,
  };
};
