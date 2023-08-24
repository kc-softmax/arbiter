"use client";

import { usePanel } from "@/hooks/usePanel";
import ChattingPanel from "./ChattingPanel";
import StartChatPanel from "./StartChatPanel";
import LoadingIndicator from "@/app/loading";

const PanelController = () => {
  const { PanelStep, setActiveStep } = usePanel([
    "startChat",
    "loading",
    "chatting",
  ] as const);

  const startChat = () => {
    setActiveStep("loading");

    setTimeout(() => {
      setActiveStep("chatting");
    }, 1000);
  };

  return (
    <div>
      <PanelStep name="startChat">
        <StartChatPanel next={startChat} />
      </PanelStep>
      <PanelStep name="loading">
        <LoadingIndicator />
      </PanelStep>
      <PanelStep name="chatting">
        <ChattingPanel />
      </PanelStep>
    </div>
  );
};

export default PanelController;
