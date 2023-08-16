import React from "react";
import ChatBanner from "./ChatBanner";
import { ChatInfo } from "@/@types/chat";
import ChatList from "./ChatList";

interface ChatRoomProps {
  chatInfo: ChatInfo;
}

const ChatRoom = ({ chatInfo }: ChatRoomProps) => {
  const { name } = chatInfo;

  return (
    <div>
      <div className="flex flex-col gap-4">
        <ChatBanner roomId="test" users={[name]} />
        <ChatList />
      </div>
    </div>
  );
};

export default ChatRoom;
