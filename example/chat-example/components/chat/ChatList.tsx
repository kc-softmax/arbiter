import React, { forwardRef } from "react";
import { MyChatBubble, OtherChatBubble } from "./chat-bubbles";
import ChatNotification from "./ChatNotification";
import { ChatMessage } from "@/@types/chat";

interface ChatListProps {
  messages: ChatMessage[];
}

const ChatList = forwardRef<HTMLDivElement, ChatListProps>(
  ({ messages }, ref) => {
    console.log("messages :>> ", messages);

    return (
      <div ref={ref}>
        <ul className="flex flex-col gap-2">
          <li>
            <OtherChatBubble username="username" message="hello" time="now" />
          </li>
          <li>
            <MyChatBubble username="me" message="world" time="now" />
          </li>
          <li>
            <ChatNotification username="username" enter />
          </li>
          <li>
            <ChatNotification username="username2" enter={false} />
          </li>
        </ul>
      </div>
    );
  }
);

ChatList.displayName = "ChatList";

export default ChatList;
