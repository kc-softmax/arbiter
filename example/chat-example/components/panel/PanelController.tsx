"use client";

import { usePanel } from "@/app/hooks/usePanel";
import StartChatPanel from "./StartChatPanel";
import ChattingPanel from "./ChattingPanel";

const PanelController = () => {
  const { PanelStep, setActiveStep } = usePanel([
    "startChat",
    "chatting",
  ] as const);

  return (
    <div>
      <PanelStep name="startChat">
        <StartChatPanel onClick={() => setActiveStep("chatting")} />
      </PanelStep>
      <PanelStep name="chatting">
        <ChattingPanel />
      </PanelStep>
    </div>
  );
};

export default PanelController;
