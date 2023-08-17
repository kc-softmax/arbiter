import { ChatInfo, ChatMessage, ChatSocketMessageBase } from "@/@types/chat";
import { ChatActions } from "@/const/actions";
import ChatBubble from "./ChatBubble";
import ChatNotification from "./ChatNotification";

interface ChatListProps {
  chatInfo: ChatInfo;
  messages: ChatMessage[];
  eventMessage?: ChatSocketMessageBase;
}

const ChatList = ({ messages, eventMessage, chatInfo }: ChatListProps) => {
  const { id } = chatInfo;

  return (
    <ul className="flex flex-col gap-2 flex-1">
      {messages.map(({ message, time, user }, index) => (
        <li key={`${user}-${index}`}>
          <ChatBubble
            username={user}
            message={message}
            time={time}
            // TODO: user.id와 비교 예정
            isMe={user === id}
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
  );
};
ChatList.displayName = "ChatList";

export default ChatList;
