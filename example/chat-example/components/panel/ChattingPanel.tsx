"use client";

import { useChat } from "@/hooks/useChat";
import { authAtom } from "@/store/authAtom";
import { scrollToBottom } from "@/utils/dom-utils";
import { useAtomValue } from "jotai";
import { useEffect, useRef } from "react";
import ChatBanner from "../chat/ChatBanner";
import ChatInputForm from "../chat/ChatInputForm";
import ChatList from "../chat/ChatList";
import ChatLobby from "../chat/ChatLobby";

const ChattingPanel = () => {
  const { id, token } = useAtomValue(authAtom);
  const { data, error, sendMessage, changeRoom, sendNotice } = useChat(token);
  const { roomId, messages, users, notice } = data;

  const chatPanelRef = useRef<HTMLDivElement>(null);

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
      <div className="p-4 h-screen flex flex-row justify-center">
        <div className="flex flex-col gap-4 justify-center items-center h-full rounded-s-lg border-2 max-w-4xl p-4 w-[1024px]">
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
        <div className="flex flex-col gap-4 items-center h-full rounded-e-lg border-2 max-w-4xl border-l-0">
          <ChatLobby changeRoom={changeRoom} />
        </div>
      </div>
    </section>
  );
};

export default ChattingPanel;
