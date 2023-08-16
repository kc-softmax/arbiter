import { ChatInfo, ChatMessage, ChatSocketMessageBase } from "@/@types/chat";
import { ChatActions } from "@/const/actions";
import { forwardRef } from "react";
import ChatNotification from "./ChatNotification";
import ChatBubble from "./ChatBubble";

interface ChatListProps {
  chatInfo: ChatInfo;
  messages: ChatMessage[];
  eventMessage?: ChatSocketMessageBase;
}

const ChatList = forwardRef<HTMLDivElement, ChatListProps>(
  ({ messages, eventMessage, chatInfo }, ref) => {
    const { name } = chatInfo;

    console.log("messages :>> ", messages);

    return (
      <div ref={ref}>
        <ul className="flex flex-col gap-2">
          <li>
            <ChatBubble username="username" message="hello" time="now" />
          </li>
          <li>
            <ChatBubble username="me" message="world" time="now" isMe />
          </li>

          {messages.map(({ message, time, user }, index) => (
            <li key={`${user}-${index}`}>
              <ChatBubble
                username={user}
                message={message}
                time={time}
                isMe={user === name}
              />
            </li>
          ))}

          <li className="sticky bottom-0">
            {eventMessage?.action === ChatActions.USER_JOIN ? (
              <ChatNotification username={eventMessage.data.user} enter />
            ) : null}
            {eventMessage?.action === ChatActions.USER_LEAVE ? (
              <ChatNotification
                username={eventMessage.data.user}
                enter={!(eventMessage.action === "user_leave")}
              />
            ) : null}
          </li>
        </ul>
      </div>
    );
  }
);

ChatList.displayName = "ChatList";

export default ChatList;
