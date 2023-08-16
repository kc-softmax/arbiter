import React from "react";
import ChatBanner, { ChatBannerProps } from "./ChatBanner";
import { ChatInfo, ChatMessage } from "@/@types/chat";
import ChatList from "./ChatList";

interface ChatRoomProps {
  chatInfo: ChatInfo;
  bannerInfo: ChatBannerProps;
  chatData: ChatMessage[];
  chatListRef?: React.RefObject<HTMLDivElement>;
}

const ChatRoom = ({ bannerInfo, chatData, chatListRef }: ChatRoomProps) => {
  const { roomId, users } = bannerInfo;

  return (
    <div>
      <div className="flex flex-col gap-4">
        <ChatBanner roomId={roomId} users={users} />
        <ChatList ref={chatListRef} messages={chatData} />
      </div>
    </div>
  );
};

export default ChatRoom;
