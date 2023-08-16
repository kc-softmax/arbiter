"use client";

import { usePanel } from "@/app/hooks/usePanel";
import StartChatPanel from "./StartChatPanel";
import ChattingPanel from "./ChattingPanel";
import { useState } from "react";
import { ChatInfo } from "@/@types/Chat";

const PanelController = () => {
  const { PanelStep, setActiveStep } = usePanel([
    "startChat",
    "chatting",
  ] as const);
  const [chatInfo, setChatInfo] = useState<ChatInfo>({
    name: "",
  });

  const startChat = (name: string) => {
    setChatInfo({ name });
    setActiveStep("chatting");
  };

  return (
    <div>
      <PanelStep name="startChat">
        <StartChatPanel next={startChat} />
      </PanelStep>
      <PanelStep name="chatting">
        <ChattingPanel chatInfo={chatInfo} />
      </PanelStep>
    </div>
  );
};

export default PanelController;
