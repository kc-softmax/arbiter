import {
  ChatMessage,
  ChatSendMessage,
  ChatSocketMessageBase,
} from "@/@types/chat";
import { ChatActions } from "@/const/actions";
import { useEffect, useRef, useState } from "react";

const wsHost = process.env.NEXT_PUBLIC_CHAT_WEBSOCKET_URL;

export const useChat = (username: string, token: string) => {
  const [roomId, setRoomId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [users, setUsers] = useState([username]);
  const [eventMessage, setEventMessage] = useState<ChatSocketMessageBase>();

  const chatPanelRef = useRef<HTMLDivElement>(null);

  if (!wsHost) {
    throw new Error("NEXT_PUBLIC_CHAT_WEBSOCKET_URL is not defined");
  }

  const wsRef = useRef<WebSocket>(new WebSocket(`${wsHost}?token=${token}`));
  console.log("wsRef.current :>> ", wsRef.current);

  const join = () => {
    const ws = wsRef.current;

    ws.onopen = () => {
      console.log("Chat connected");
    };

    ws.onclose = (event) => {
      console.log("Chat disconnected");
      if (event.code === 3000) {
        alert("Invalid Token");
        location.reload();
      }
    };

    ws.onmessage = (event) => {
      console.log("event :>> ", event);

      const chatSoketMessage: ChatSocketMessageBase = JSON.parse(event.data);
      const { action, data } = chatSoketMessage;

      if (action === ChatActions.ROOM_JOIN) {
        const { room_id, messages, users } = data;

        setRoomId(room_id);
        setMessages(messages);
        setUsers(users);
      }

      if (action === ChatActions.USER_JOIN) {
        setUsers((prev) => [...prev, data.user]);
      }

      if (action === ChatActions.USER_LEAVE) {
        setUsers((prev) => prev.filter((user) => user !== data.user));
      }

      if (action === ChatActions.MESSAGE || action === ChatActions.CONTROL) {
        setMessages((prev) => [...prev, data]);
      }

      setEventMessage(chatSoketMessage);

      chatPanelRef.current?.scrollTo({
        top: chatPanelRef.current.scrollHeight,
        behavior: "smooth",
      });
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

    ws.send(JSON.stringify(chatData));
  };

  useEffect(() => {
    join();

    chatPanelRef.current?.scrollTo({
      top: chatPanelRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, []);

  return {
    roomId,
    messages,
    users,
    chatPanelRef,
    sendMessage,
    eventMessage,
  };
};
