"use client";

import LoadingIndicator from "@/app/loading";
import { usePanel } from "@/hooks/usePanel";
import ChattingPanel from "./ChattingPanel";
import StartChatPanel from "./StartChatPanel";
import ChatProvider from "../provider/ChatProvider";

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
      <PanelStep name="startChat" next={startChat}>
        <StartChatPanel />
      </PanelStep>
      <PanelStep name="loading">
        <LoadingIndicator />
      </PanelStep>
      <PanelStep name="chatting">
        <ChatProvider>
          <ChattingPanel />
        </ChatProvider>
      </PanelStep>
    </div>
  );
};

export default PanelController;
