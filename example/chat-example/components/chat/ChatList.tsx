"use client";

import { useChat } from "@/hooks/useChat";
import ChatBubble from "./ChatBubble";
import ChatNotification from "./ChatNotification";

const ChatList = () => {
  const {
    data: { messages },
  } = useChat();

  return (
    <ul className="flex flex-col gap-2 flex-1">
      {messages.map((message, index) => {
        if (message.type === "message") {
          return (
            <li key={message.data.message_id}>
              <ChatBubble message={message.data} />
            </li>
          );
        }

        if (message.type === "notification") {
          return (
            <li
              key={`${message.data.user.user_name}-${message.data.enter}-${index}`}
            >
              <ChatNotification
                username={message.data.user.user_name}
                enter={message.data.enter}
              />
            </li>
          );
        }
      })}
    </ul>
  );
};
ChatList.displayName = "ChatList";

export default ChatList;
