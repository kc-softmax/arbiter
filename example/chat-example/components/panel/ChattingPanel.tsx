import { ChatInfo } from "@/@types/chat";
import React from "react";
import ChatInputForm from "../chat/ChatInputForm";

interface ChattingPanelProps {
  chatInfo: ChatInfo;
}

const ChattingPanel = ({ chatInfo }: ChattingPanelProps) => {
  const { name } = chatInfo;
  const sendChat = (message: string) => {
    console.log(message);
  };

  return (
    <section>
      <div className="flex flex-col justify-center items-center h-screen border-2 max-w-4xl mx-auto p-4">
        <div className="flex-1">ChattingPanel: {name}</div>
        <div className="w-full">
          <ChatInputForm sendChat={sendChat} />
        </div>
      </div>
    </section>
  );
};

export default ChattingPanel;
