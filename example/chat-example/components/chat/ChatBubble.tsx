import { ChatMessage } from "@/@types/chat";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";

interface ChatBubbleProps {
  message: ChatMessage;
  action?: {
    onClickNotice?: ({
      userId,
      message,
    }: {
      userId: string;
      message: string;
    }) => void;
  };
}

const ChatBubble = ({ message, action }: ChatBubbleProps) => {
  const { id } = useAtomValue(authAtom);
  const {
    message: messageText,
    message_id,
    time,
    user: { user_id: userId, user_name: username },
  } = message;

  const onClickNotice = () => {
    action?.onClickNotice?.({
      userId: userId.toString(),
      message: messageText,
    });
  };

  const onClickReport = () => {
    alert(`Report ${username}'s ${message_id} at ${time}`);
  };

  const isMe = id === userId.toString();

  return (
    <div className={`chat ${isMe ? "chat-end" : "chat-start"}`}>
      <p className="chat-header">{username}</p>
      <div
        tabIndex={0}
        className={`dropdown dropdown-hover chat-bubble flex justify-center items-end cursor-pointer max-w-[70%] ${
          isMe
            ? "chat-bubble-primary dropdown-left"
            : "chat-bubble-secondary dropdown-right"
        }`}
      >
        <p>{messageText}</p>

        <div
          tabIndex={0}
          className="dropdown-content z-20 p-2 shadow bg-base-100 rounded-box space-y-2"
        >
          <button
            className="btn btn-warning btn-outline"
            onClick={onClickNotice}
          >
            Notice
          </button>
          <button className="btn btn-error btn-outline" onClick={onClickReport}>
            Report
          </button>
        </div>
      </div>
      <time className="chat-footer opacity-50">
        {new Date(time).toLocaleString()}
      </time>
    </div>
  );
};

export default ChatBubble;
