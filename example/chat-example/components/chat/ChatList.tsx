import { ChatInfo, ChatMessage, ChatSocketMessageBase } from "@/@types/chat";
import { ChatActions } from "@/const/actions";
import { forwardRef } from "react";
import ChatNotification from "./ChatNotification";
import { MyChatBubble, OtherChatBubble } from "./chat-bubbles";

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
            <OtherChatBubble username="username" message="hello" time="now" />
          </li>
          <li>
            <MyChatBubble username="me" message="world" time="now" />
          </li>

          {messages.map(({ message, time, user }, index) => (
            <li key={`${user}-${index}`}>
              {user === name ? (
                <MyChatBubble username={user} message={message} time={time} />
              ) : (
                <OtherChatBubble
                  username={user}
                  message={message}
                  time={time}
                />
              )}
            </li>
          ))}

          {eventMessage?.action === ChatActions.USER_JOIN ? (
            <li>
              <ChatNotification username={eventMessage.data.user} enter />
            </li>
          ) : null}
          {eventMessage?.action === ChatActions.USER_LEAVE ? (
            <li>
              <ChatNotification
                username={eventMessage.data.user}
                enter={!(eventMessage.action === "user_leave")}
              />
            </li>
          ) : null}
        </ul>
      </div>
    );
  }
);

ChatList.displayName = "ChatList";

export default ChatList;
