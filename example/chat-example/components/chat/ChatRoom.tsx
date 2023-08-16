"use client";

import { ChatInfo, ChatMessage, ChatSocketMessageBase } from "@/@types/chat";
import React from "react";
import ChatBanner, { ChatBannerProps } from "./ChatBanner";
import ChatList from "./ChatList";

interface ChatRoomProps {
  chatInfo: ChatInfo;
  bannerInfo: ChatBannerProps;
  chatData: ChatMessage[];
  chatListRef?: React.RefObject<HTMLDivElement>;
  eventMessage?: ChatSocketMessageBase;
}

const ChatRoom = ({
  chatInfo,
  bannerInfo,
  chatData,
  chatListRef,
  eventMessage,
}: ChatRoomProps) => {
  const { roomId, users } = bannerInfo;

  return (
    <div className="flex flex-col gap-4">
      <ChatBanner roomId={roomId} users={users} />
      <ChatList
        ref={chatListRef}
        chatInfo={chatInfo}
        messages={chatData}
        eventMessage={eventMessage}
      />
    </div>
  );
};

export default ChatRoom;
