import React from "react";
import ChatBanner from "./ChatBanner";
import { ChatInfo } from "@/@types/chat";

interface ChatRoomProps {
  chatInfo: ChatInfo;
}

const ChatRoom = ({ chatInfo }: ChatRoomProps) => {
  const { name } = chatInfo;

  return (
    <div>
      <div>
        <ChatBanner roomId="test" users={[name]} />
      </div>
    </div>
  );
};

export default ChatRoom;
