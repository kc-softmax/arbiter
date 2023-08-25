"use client";

import { ChatTabList, ChatTabType } from "@/const/actions";
import { useChat } from "@/hooks/useChat";
import { scrollToBottom } from "@/utils/dom-utils";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";
import { useEffect, useRef } from "react";
import ChatBanner from "../chat/ChatBanner";
import ChatInputForm from "../chat/ChatInputForm";
import ChatList from "../chat/ChatList";
import ChatTabs from "../chat/ChatTabs";

const ChattingPanel = () => {
  const { id, token } = useAtomValue(authAtom);
  const { data, error, sendMessage, changeRoom, sendNotice } = useChat(token);
  const { roomId, messages, users, notice } = data;

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
        nextRoomId = "DEFAULT";
        break;
      default:
        break;
    }

    // 이전 방과 같은 방이면 무시
    if (nextRoomId === roomId) return;

    changeRoom(nextRoomId);
  };

  const sendChat = (message: string) => {
    console.log(id, message);
    sendMessage({
      user_id: id,
      message,
    });
  };

  const onClickNotice = ({
    userId,
    message,
  }: {
    userId: string;
    message: string;
  }) => {
    sendNotice({
      user_id: userId,
      message,
    });
  };

  useEffect(() => {
    scrollToBottom(chatPanelRef);
  }, [messages]);

  if (error) {
    alert(`${error.code}: ${error.reason}`);
  }

  return (
    <section>
      <div className="p-4 h-screen">
        <div className="flex flex-col gap-4 justify-center items-center h-full rounded-lg border-2 max-w-4xl mx-auto p-4">
          <ChatTabs onChange={onChangeTabs} />
          <div
            ref={chatPanelRef}
            className="flex-1 w-full overflow-scroll flex flex-col gap-4 px-4"
          >
            <ChatBanner roomId={roomId} users={users} notice={notice} />
            <ChatList
              messages={messages}
              actions={{
                onClickNotice,
              }}
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
