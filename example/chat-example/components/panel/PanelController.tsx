"use client";

import { usePanel } from "@/app/hooks/usePanel";
import ChattingPanel from "./ChattingPanel";
import StartChatPanel from "./StartChatPanel";

const PanelController = () => {
  const { PanelStep, setActiveStep } = usePanel([
    "startChat",
    "chatting",
  ] as const);

  const startChat = () => {
    setActiveStep("chatting");
  };

  return (
    <div>
      <PanelStep name="startChat">
        <StartChatPanel next={startChat} />
      </PanelStep>
      <PanelStep name="chatting">
        <ChattingPanel />
      </PanelStep>
    </div>
  );
};

export default PanelController;
