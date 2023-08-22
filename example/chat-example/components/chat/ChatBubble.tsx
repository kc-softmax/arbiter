import { ChatMessage } from "@/@types/chat";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";

interface ChatBubbleProps {
  message: ChatMessage;
}

const ChatBubble = ({ message }: ChatBubbleProps) => {
  const { id } = useAtomValue(authAtom);
  const {
    message: messageText,
    message_id,
    time,
    user: { user_id: userId, user_name: userName },
  } = message;

  const onClickReport = () => {
    alert(`Report ${userName}'s ${message_id} at ${time}`);
  };

  const isMe = id === userId.toString();

  return (
    <div className={`chat ${isMe ? "chat-end" : "chat-start"}`}>
      <p className="chat-header">{userName}</p>
      <div
        tabIndex={0}
        className={`dropdown dropdown-hover dropdown-right chat-bubble flex justify-center items-end cursor-pointer max-w-[70%] ${
          isMe ? "chat-bubble-primary" : "chat-bubble-secondary"
        }`}
      >
        <p className="hover:brightness-90 transition-all">{messageText}</p>
        {isMe ? null : (
          <div
            tabIndex={0}
            className="dropdown-content z-20 p-2 shadow bg-base-100 rounded-box"
          >
            <button
              className="btn btn-error btn-outline"
              onClick={onClickReport}
            >
              Report
            </button>
          </div>
        )}
      </div>
      <time className="chat-footer opacity-50">
        {new Date(time).toLocaleString()}
      </time>
    </div>
  );
};

export default ChatBubble;
