"use client";

import { useChat } from "@/hooks/useChat";
import { scrollToBottom } from "@/utils/dom-utils";
import { useEffect, useRef } from "react";
import ChatBanner from "../chat/ChatBanner";
import ChatInputForm from "../chat/ChatInputForm";
import ChatList from "../chat/ChatList";
import ChatLobby from "../chat/ChatLobby";

const ChattingPanel = () => {
  const { data, error } = useChat();
  const { messages } = data;

  const chatPanelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollToBottom(chatPanelRef);
  }, [messages]);

  if (error) {
    alert(`${error.code}: ${error.reason}`);
  }

  return (
    <section>
      <div className="p-4 h-screen flex flex-row justify-center">
        <div className="flex flex-col gap-4 justify-center items-center h-full rounded-s-lg border-2 max-w-4xl p-4 w-[1024px]">
          <div
            ref={chatPanelRef}
            className="flex-1 w-full overflow-scroll flex flex-col gap-4 px-4"
          >
            <ChatBanner />
            <ChatList />
          </div>
          <div className="w-full">
            <ChatInputForm />
          </div>
        </div>
        <div className="flex flex-col gap-4 items-center h-full rounded-e-lg border-2 max-w-4xl border-l-0">
          <ChatLobby />
        </div>
      </div>
    </section>
  );
};

export default ChattingPanel;
