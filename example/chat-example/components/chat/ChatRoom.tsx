"use client";

import { ChatMessage, ChatSocketMessageBase } from "@/@types/chat";
import React from "react";
import ChatBanner from "./ChatBanner";
import ChatList from "./ChatList";

interface ChatRoomProps {
  bannerInfo: {
    roomId: string;
    users: string[];
  };
  chatData: ChatMessage[];
  chatListRef?: React.RefObject<HTMLDivElement>;
  eventMessage?: ChatSocketMessageBase;
}

const ChatRoom = ({ bannerInfo, chatData, eventMessage }: ChatRoomProps) => {
  const { roomId, users } = bannerInfo;

  return (
    <div className="flex flex-col gap-4">
      <ChatBanner roomId={roomId} users={users} />
      <ChatList messages={chatData} eventMessage={eventMessage} />
    </div>
  );
};

export default ChatRoom;
