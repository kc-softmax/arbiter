"use client";

import { ChatInfo } from "@/@types/chat";
import { useChat } from "@/app/hooks/useChat";
import { ChatTabList, ChatTabType } from "@/const/actions";
import { scrollToBottom } from "@/lib/dom-utils";
import { useEffect, useRef } from "react";
import ChatInputForm from "../chat/ChatInputForm";
import ChatRoom from "../chat/ChatRoom";
import ChatTabs from "../chat/ChatTabs";

interface ChattingPanelProps {
  chatInfo: ChatInfo;
}

const ChattingPanel = ({ chatInfo }: ChattingPanelProps) => {
  const { id, token } = chatInfo;
  const { data, sendMessage, eventMessage, changeRoom } = useChat(token);
  const { roomId, messages, users } = data;

  const chatPanelRef = useRef<HTMLDivElement>(null);

  const onChangeTabs = (tab: ChatTabType) => {
    let nextRoomId = "";

    switch (tab) {
      case ChatTabList.CUSTOM:
        const answer = prompt("Type Room ID");

        if (!answer) {
          return;
        }

        nextRoomId = answer;
        break;
      case ChatTabList.PARTY:
        nextRoomId = "party";
        break;
      case ChatTabList.ALL:
        nextRoomId = crypto.randomUUID();
        break;
      default:
        break;
    }

    if (nextRoomId === roomId) return;

    changeRoom(nextRoomId);
  };

  const sendChat = (message: string) => {
    console.log(id, message);
    sendMessage(message);
  };

  useEffect(() => {
    scrollToBottom(chatPanelRef);
  }, [messages]);

  return (
    <section>
      <div className="p-4 h-screen">
        <div className="flex flex-col gap-4 justify-center items-center h-full rounded-lg border-2 max-w-4xl mx-auto p-4">
          <ChatTabs onChange={onChangeTabs} />
          <div ref={chatPanelRef} className="flex-1 w-full overflow-scroll">
            <ChatRoom
              chatInfo={chatInfo}
              bannerInfo={{
                roomId,
                users,
              }}
              chatData={messages}
              eventMessage={eventMessage}
            />
          </div>
          <div className="w-full">
            <ChatInputForm sendChat={sendChat} />
          </div>
        </div>
      </div>
    </section>
  );
};

export default ChattingPanel;
