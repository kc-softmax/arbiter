import { ChatInfo } from "@/@types/Chat";
import React from "react";

interface ChattingPanelProps {
  chatInfo: ChatInfo;
}

const ChattingPanel = ({ chatInfo }: ChattingPanelProps) => {
  const { name } = chatInfo;

  return <div>ChattingPanel: {name}</div>;
};

export default ChattingPanel;
