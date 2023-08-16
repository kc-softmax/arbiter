import { ChatInfo } from "@/@types/chat";
import React from "react";
import ChatInputForm from "../chat/ChatInputForm";
import ChatRoom from "../chat/ChatRoom";

interface ChattingPanelProps {
  chatInfo: ChatInfo;
}

const ChattingPanel = ({ chatInfo }: ChattingPanelProps) => {
  const { name } = chatInfo;

  const sendChat = (message: string) => {
    console.log(name, message);
  };

  return (
    <section>
      <div className="p-4 h-screen">
        <div className="flex flex-col gap-4 justify-center items-center h-full rounded-lg border-2 max-w-4xl mx-auto p-4">
          <div className="flex-1 w-full">
            <ChatRoom chatInfo={chatInfo} />
          </div>
          <div className="w-full">
            <ChatInputForm sendChat={sendChat} />
          </div>
        </div>
      </div>
    </section>
  );
};

export default ChattingPanel;
