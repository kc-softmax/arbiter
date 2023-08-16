import React from "react";
import { MyChatBubble, OtherChatBubble } from "./chat-bubbles";
import ChatNotification from "./ChatNotification";

const ChatList = () => {
  return (
    <div>
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
};

export default ChatList;
