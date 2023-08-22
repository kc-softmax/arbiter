import { ChatMessage, ChatSocketMessageBase } from "@/@types/chat";
import { ChatActions } from "@/const/actions";
import ChatBubble from "./ChatBubble";
import ChatNotification from "./ChatNotification";

interface ChatListProps {
  messages: ChatMessage[];
  eventMessage?: ChatSocketMessageBase;
}

const ChatList = ({ messages, eventMessage }: ChatListProps) => {
  return (
    <ul className="flex flex-col gap-2 flex-1">
      {messages.map(({ message, time, user }, index) => (
        <li key={`${user}-${index}`}>
          <ChatBubble user={user} message={message} time={time} />
        </li>
      ))}

      <li className="sticky bottom-0">
        {eventMessage?.action === ChatActions.USER_JOIN ||
        eventMessage?.action === ChatActions.USER_LEAVE ? (
          <ChatNotification
            username={eventMessage.data.user.name}
            enter={eventMessage.action === ChatActions.USER_JOIN}
          />
        ) : null}
      </li>
    </ul>
  );
};
ChatList.displayName = "ChatList";

export default ChatList;
