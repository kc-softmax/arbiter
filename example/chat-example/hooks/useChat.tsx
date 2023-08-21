"use client";

import {
  ChatMessage,
  ChatSendChangeRoom,
  ChatSendMessage,
  ChatSocketMessageBase,
} from "@/@types/chat";
import { ChatActions } from "@/const/actions";
import { useEffect, useRef, useState } from "react";

const wsHost = process.env.NEXT_PUBLIC_CHAT_WEBSOCKET_URL;

export const useChat = (token: string) => {
  const [roomId, setRoomId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [users, setUsers] = useState<string[]>([]);
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

      if (action === ChatActions.ROOM_JOIN) {
        const { room_id, messages, users } = data;

        setRoomId(room_id);
        setMessages(messages);
        setUsers(users);
      }

      if (action === ChatActions.USER_JOIN) {
        setUsers((prev) =>
          prev.includes(data.user) ? prev : [...prev, data.user]
        );
      }

      if (action === ChatActions.USER_LEAVE) {
        setUsers((prev) => prev.filter((user) => user !== data.user));
      }

      if (action === ChatActions.MESSAGE || action === ChatActions.CONTROL) {
        setMessages((prev) => [...prev, data]);
      }

      setEventMessage(chatSocketMessage);
    };
  };

  const sendMessage = (message: string) => {
    const ws = wsRef.current;

    const chatData: ChatSendMessage = {
      action: ChatActions.MESSAGE,
      data: {
        message,
      },
    };

    ws?.send(JSON.stringify(chatData));
  };

  const changeRoom = (roomId: string) => {
    const ws = wsRef.current;

    const chatData: ChatSendChangeRoom = {
      action: ChatActions.ROOM_CHANGE,
      data: {
        room_id: roomId,
      },
    };

    // TODO: 룸 입장시 바뀌게 해두었으므로 이 부분은 나중에 제거할 임시 코드
    setRoomId(roomId);

    console.log("🚀 changeRoom ~ chatData:", chatData);
    // ws?.send(JSON.stringify(chatData));
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
