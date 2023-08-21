import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";

interface ChatBubbleProps {
  username: string;
  message: string;
  time: string;
}

const ChatBubble = ({ username, message, time }: ChatBubbleProps) => {
  const { id } = useAtomValue(authAtom);

  const onClickReport = () => {
    alert(`Report ${username} at ${time}`);
  };

  const isMe = id === username;

  return (
    <div className={`chat ${isMe ? "chat-end" : "chat-start"}`}>
      <p className="chat-header">{username}</p>
      <div
        tabIndex={0}
        className={`dropdown dropdown-hover dropdown-right chat-bubble flex justify-center items-end cursor-pointer max-w-[70%] ${
          isMe ? "chat-bubble-primary" : "chat-bubble-secondary"
        }`}
      >
        <p className="hover:brightness-90 transition-all">{message}</p>
        <div
          tabIndex={0}
          className="dropdown-content z-20 p-2 shadow bg-base-100 rounded-box"
        >
          <button className="btn btn-error btn-outline" onClick={onClickReport}>
            Report
          </button>
        </div>
      </div>
      <time className="chat-footer opacity-50">{time}</time>
    </div>
  );
};

export default ChatBubble;
